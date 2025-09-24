#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge AI-extracted fields into your index CSV and optionally update rb-<ref>.md files.

Inputs:
  --index_csv            Your current master CSV (e.g., registered_and_deregistered_with_parish_features_normalised.csv)
  --extracted_csv        The model output CSV (from rb_ai_extract.py)
  --out_csv              Where to write the merged CSV
  --md_root              Root containing rb-<ref>/rb-<ref>.md (from the OCR pipeline)

Options:
  --update_md            Actually rewrite md files (otherwise dry-run only logs what it WOULD change)
  --backup_md            Save .bak alongside md before writing
  --add_cleaned_section  Add a "## Cleaned OCR" section with cleaned_text from extraction
  --fill_missing_dates_from_extraction  Only if existing md sections are missing/empty
  --limit N              Process at most N records (for testing)
  --verbose              Print more per-record detail

What it writes into each rb-<ref>.md (idempotent):
  - (optional) fills empty "## Registration date" / "## De-registration date" from extracted *_date_text
  - Adds/updates a "## Extracted details" section:
      * Architects: ...
      * Builders: ...
      * Construction: 1892–1895 (or verbatim start/end date text if present)
      * Reasons for registration: (bullets)
  - (optional) Adds a "## Cleaned OCR" fenced block with the model’s cleaned_text (keeps original OCR block intact)

Safe to re-run: sections are replaced in-place on subsequent runs.
"""

import argparse, json, os, re, sys, time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# ---------- logging ----------
def log(msg, level="INFO", err=False):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stream = sys.stderr if err or level in ("WARN","ERROR") else sys.stdout
    print(f"[{ts}] [{level}] {msg}", file=stream, flush=True)

# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--index_csv", required=True)
    p.add_argument("--extracted_csv", required=True)
    p.add_argument("--out_csv", required=True)
    p.add_argument("--md_root", required=True)
    p.add_argument("--update_md", action="store_true")
    p.add_argument("--backup_md", action="store_true")
    p.add_argument("--add_cleaned_section", action="store_true")
    p.add_argument("--fill_missing_dates_from_extraction", action="store_true")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()

# ---------- IO ----------
def load_csv(path: str) -> List[Dict[str,str]]:
    import pandas as pd
    df = pd.read_csv(path, dtype=str).fillna("")
    return df.to_dict(orient="records")

def save_csv(rows: List[Dict[str,Any]], path: str):
    import pandas as pd, numpy as np
    if not rows:
        log("No rows to write.", "WARN")
        return
    # Stable columns: take union of keys in order of first appearance
    cols = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k); cols.append(k)
    df = pd.DataFrame(rows, columns=cols)
    df.replace({np.nan: ""}, inplace=True)
    df.to_csv(path, index=False)

# ---------- Markdown helpers ----------
H_RE = lambda title: re.compile(rf"(?m)^##\s+{re.escape(title)}\s*$")

def find_section(text: str, title: str) -> Tuple[int,int]:
    """
    Return (start_idx, end_idx) of the section (title line inclusive up to just before next '## ' or end).
    If missing, (-1,-1).
    """
    head = H_RE(title).search(text)
    if not head:
        return -1, -1
    start = head.start()
    # find next heading after this
    nxt = re.search(r"(?m)^##\s+.+$", text[head.end():])
    if nxt:
        end = head.end() + nxt.start()
    else:
        end = len(text)
    return start, end

def set_section(text: str, title: str, body: str) -> str:
    """
    Insert or replace a '## {title}' section with body (no trailing newline required).
    """
    new_block = f"## {title}\n{body.rstrip()}\n\n"
    s, e = find_section(text, title)
    if s == -1:
        # insert before Links if present, else append
        sL, eL = find_section(text, "Links")
        if sL != -1:
            return text[:sL] + new_block + text[sL:]
        else:
            if not text.endswith("\n"):
                text += "\n"
            return text + "\n" + new_block
    else:
        return text[:s] + new_block + text[e:]

def get_section_body(text: str, title: str) -> str:
    s, e = find_section(text, title)
    return "" if s == -1 else text[s:e]

def replace_or_fill_date_section(text: str, title: str, new_value: str, only_if_missing=True) -> str:
    """
    If the section exists and is non-empty (beyond header), keep it unless only_if_missing=False.
    If missing or empty, set it to new_value or '(not provided)' if blank.
    """
    s, e = find_section(text, title)
    new_value = new_value.strip()
    body = new_value if new_value else "(not provided)"
    if s == -1:
        return set_section(text, title, body)
    # section exists: check content after the header line
    sec = text[s:e]
    lines = sec.splitlines()
    content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    if content and only_if_missing:
        return text  # leave as-is
    return set_section(text, title, body)

def add_or_replace_cleaned_ocr(text: str, cleaned: str) -> str:
    body = "```\n" + cleaned.rstrip() + "\n```" if cleaned.strip() else "(no cleaned text)"
    return set_section(text, "Cleaned OCR", body)

def add_or_replace_extracted_details(text: str, arch: List[str], bld: List[str],
                                     start_year, end_year, start_txt, end_txt,
                                     reasons: List[str]) -> str:
    lines = []
    if arch:
        lines.append(f"* Architects: {', '.join(arch)}")
    if bld:
        lines.append(f"* Builders: {', '.join(bld)}")
    # Construction line preference: text labels if present, else years span
    cons = None
    if start_txt or end_txt:
        st = start_txt or ""
        en = end_txt or ""
        if st and en:
            cons = f"{st} – {en}"
        else:
            cons = st or en
    elif start_year or end_year:
        cons = f"{start_year or ''}–{end_year or ''}"
    if cons:
        lines.append(f"* Construction: {cons}")

    if reasons:
        lines.append("* Reasons for registration:")
        for r in reasons:
            r = str(r).strip()
            if r:
                lines.append(f"  - {r}")

    body = "\n".join(lines) if lines else "(no extracted details)"
    return set_section(text, "Extracted details", body)

# ---------- Merge + MD update ----------
def as_list(x):
    if isinstance(x, list): return x
    if isinstance(x, str):
        x = x.strip()
        if not x: return []
        try:
            # some rows may be JSON strings
            j = json.loads(x)
            if isinstance(j, list): return [str(v) for v in j]
        except Exception:
            pass
        # split on semicolons/commas
        parts = [p.strip() for p in re.split(r"[;,]+", x) if p.strip()]
        return parts
    return []

def main():
    args = parse_args()
    idx_rows = load_csv(args.index_csv)
    ext_rows = load_csv(args.extracted_csv)

    # Build map from RB_Number -> extraction row (the last one wins if dup)
    ext_by_rb: Dict[str, Dict[str,str]] = {}
    for r in ext_rows:
        rb = str(r.get("RB_Number","")).strip()
        if rb:
            ext_by_rb[rb] = r

    merged: List[Dict[str,Any]] = []
    md_root = Path(args.md_root)
    touched = 0
    skipped = 0

    log(f"Merging {len(ext_rows)} extracted rows into {len(idx_rows)} index rows…")

    for i, row in enumerate(idx_rows, 1):
        rb = str(row.get("RB_Number","")).strip()
        merged_row = dict(row)
        ext = ext_by_rb.get(rb)
        if ext:
            # Flatten lists (architect_names, builder_names, reasons_for_registration may be JSON)
            merged_row["architect_names"] = json.dumps(as_list(ext.get("architect_names","")), ensure_ascii=False)
            merged_row["builder_names"] = json.dumps(as_list(ext.get("builder_names","")), ensure_ascii=False)
            merged_row["reasons_for_registration"] = json.dumps(as_list(ext.get("reasons_for_registration","")), ensure_ascii=False)
            merged_row["construction_start_year"] = ext.get("construction_start_year","")
            merged_row["construction_end_year"]   = ext.get("construction_end_year","")
            merged_row["construction_start_date_text"] = ext.get("construction_start_date_text","")
            merged_row["construction_end_date_text"]   = ext.get("construction_end_date_text","")
            merged_row["registration_date_text"]       = ext.get("registration_date_text","")
            merged_row["deregistration_date_text"]     = ext.get("deregistration_date_text","")
            merged_row["notes_extraction"]             = ext.get("notes","")
            merged_row["cleaned_text_source"]          = ext.get("cleaned_text_source","")
            merged_row["md_path"]                      = ext.get("md_path","")

            # Heuristic Needs_Review
            needs = []
            if not as_list(ext.get("architect_names","")) and not as_list(ext.get("builder_names","")):
                needs.append("no_names")
            if not as_list(ext.get("reasons_for_registration","")):
                needs.append("no_reasons")
            if not (ext.get("construction_start_year") or ext.get("construction_end_year")
                    or ext.get("construction_start_date_text") or ext.get("construction_end_date_text")):
                needs.append("no_dates")
            if ext.get("cleaned_text_source","") != "fenced_block":
                needs.append("ocr_not_fenced")
            merged_row["Needs_Review"] = "; ".join(needs)

            # ---- Markdown update (optional) ----
            if args.update_md:
                mdp = Path(ext.get("md_path") or (md_root / f"rb-{rb}" / f"rb-{rb}.md"))
                if mdp.exists():
                    text = mdp.read_text(encoding="utf-8", errors="ignore")

                    # (optional) fill missing dates from extraction
                    if args.fill_missing_dates_from_extraction:
                        text = replace_or_fill_date_section(
                            text, "Registration date", ext.get("registration_date_text",""), only_if_missing=True
                        )
                        # Only add De-registration section when appropriate (status or extracted text)
                        status = str(row.get("Status","")).strip().lower()
                        if status == "de-registered" or ext.get("deregistration_date_text",""):
                            text = replace_or_fill_date_section(
                                text, "De-registration date", ext.get("deregistration_date_text",""), only_if_missing=True
                            )

                    # Extracted details section (always added/updated when we have any extracted content)
                    text = add_or_replace_extracted_details(
                        text,
                        arch=as_list(ext.get("architect_names","")),
                        bld=as_list(ext.get("builder_names","")),
                        start_year=ext.get("construction_start_year"),
                        end_year=ext.get("construction_end_year"),
                        start_txt=ext.get("construction_start_date_text"),
                        end_txt=ext.get("construction_end_date_text"),
                        reasons=as_list(ext.get("reasons_for_registration","")),
                    )

                    # (optional) cleaned OCR section
                    if args.add_cleaned_section:
                        cleaned = ext.get("cleaned_text","") or ""
                        text = add_or_replace_cleaned_ocr(text, cleaned)

                    if args.backup_md:
                        bak = mdp.with_suffix(mdp.suffix + ".bak")
                        if not bak.exists():
                            bak.write_text(mdp.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")

                    if args.verbose:
                        log(f"[RB {rb}] Updating MD: {mdp}")

                    mdp.write_text(text, encoding="utf-8")
                    touched += 1
                else:
                    if args.verbose:
                        log(f"[RB {rb}] MD missing at {mdp}", "WARN", err=True)
                    skipped += 1

        merged.append(merged_row)

        if args.limit and i >= args.limit:
            log(f"Hit --limit={args.limit}, stopping early.")
            break

    # Save merged CSV
    save_csv(merged, args.out_csv)
    log(f"Merged CSV written → {args.out_csv}")
    if args.update_md:
        log(f"Markdown updated: touched={touched} missing_md={skipped}")

if __name__ == "__main__":
    main()
