#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rb_ai_extract.py — Extract structured facts from OCR'd RB markdown files using OpenAI.

Inputs:
  --index_csv   Master CSV (RB_Number, Building_Name, Parish, Status, Links, Features, etc.)
  --md_root     Root containing rb-<ref>/rb-<ref>.md (produced by your OCR pipeline)
  --out_csv     Output CSV for extracted fields
  --model       OpenAI model (default: gpt-4o-2024-08-06)

Env:
  OPENAI_API_KEY must be set.

Features:
  • Timestamped logs; row-by-row start/finish
  • Retries & backoff; classifies 401 vs 400/422 vs 429/5xx
  • Resume mode: skips rows already present in --out_csv
  • Debug blobs to --debug_dir on failures (raw JSON/outputs)
  • Optional JSON schema validation; coerce on mismatch
  • Status JSONL stream via --status_jsonl
  • Quick-glance preview printed on success
  • Optional full JSON print via --print_json_on_success
  • Optional cleaned-text preview length via --preview_cleaned

Install:
  pip install -U openai pandas jsonschema  # jsonschema optional but recommended
"""

import argparse, json, os, re, sys, time, random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# ---------------- Logging & helpers ----------------

def log(msg: str, level: str = "INFO", err: bool = False):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stream = sys.stderr if err or level in ("WARN","ERROR") else sys.stdout
    print(f"[{ts}] [{level}] {msg}", file=stream, flush=True)

def emit_jsonl(path: str, obj: dict):
    if not path: return
    obj = {"ts": datetime.now().isoformat(timespec="seconds"), **obj}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def save_debug_blob(debug_dir: str, rb: str, kind: str, content: str):
    if not debug_dir: return
    Path(debug_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(debug_dir) / f"{ts}-rb{rb}-{kind}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ---------------- CLI ----------------

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--index_csv", required=True)
    p.add_argument("--md_root", required=True)
    p.add_argument("--out_csv", required=True)
    p.add_argument("--model", default="gpt-4o-2024-08-06")
    p.add_argument("--max_chars", type=int, default=160000, help="Trim OCR text to this many chars.")
    p.add_argument("--delay_min", type=float, default=0.4, help="Base polite delay before each request.")
    p.add_argument("--delay_max", type=float, default=1.2, help="Additional random delay.")
    p.add_argument("--oa_retries", type=int, default=3, help="Max OpenAI retries (excluding 401 by default).")
    p.add_argument("--retry_unauthorized", action="store_true", help="Retry 401 Unauthorized (off by default).")
    p.add_argument("--backoff_min", type=float, default=1.5, help="Backoff base (seconds).")
    p.add_argument("--backoff_cap", type=float, default=30.0, help="Backoff cap (seconds).")
    p.add_argument("--status_jsonl", default="", help="Optional path to write per-row status JSONL.")
    p.add_argument("--debug_dir", default="", help="If set, save raw model outputs here for failures/violations.")
    p.add_argument("--validate_schema", action="store_true", help="Run local JSON Schema validation (warn & coerce).")
    p.add_argument("--print_json_on_success", action="store_true", help="Print full model JSON on success.")
    p.add_argument("--preview_cleaned", type=int, default=0, help="If >0, print first N chars of cleaned_text.")
    return p.parse_args()

# ---------------- CSV IO ----------------

def load_rows(csv_path: str) -> List[Dict[str, str]]:
    import pandas as pd
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    return df.to_dict(orient="records")

def save_rows(rows: List[Dict[str, Any]], out_csv: str):
    if not rows: return
    cols = [
        "RB_Number","Building_Name","Parish","Status","Date_Registered","Deregistration_Date","Links","Features",
        "architect_names","builder_names","reasons_for_registration",
        "construction_start_year","construction_end_year",
        "construction_start_date_text","construction_end_date_text",
        "registration_date_text","deregistration_date_text",
        "notes","cleaned_text_source","md_path"
    ]
    for r in rows:
        for k in r.keys():
            if k not in cols:
                cols.append(k)
    import pandas as pd, numpy as np
    df = pd.DataFrame(rows, columns=cols)
    for col in ["architect_names","builder_names","reasons_for_registration"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x,(list,dict)) else x)
    df.replace({np.nan: ""}, inplace=True)
    df.to_csv(out_csv, index=False)

def load_done_set(out_csv: str):
    try:
        import pandas as pd
        df = pd.read_csv(out_csv, dtype=str)
        return set(df["RB_Number"].astype(str).str.strip())
    except Exception:
        return set()

# ---------------- Markdown helpers ----------------

def read_md_text(md_path: Path) -> str:
    try:
        return md_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def extract_ocr_block(md_text: str) -> Tuple[str, str]:
    """
    Returns (ocr_text, source_flag).
    Prefer fenced block under '## OCR'; else return whole md.
    """
    parts = re.split(r"(?m)^##\s+OCR\s*$", md_text, maxsplit=1)
    if len(parts) == 2:
        after = parts[1]
        m = re.search(r"```(.*?)```", after, flags=re.S)
        if m:
            return m.group(1).strip(), "fenced_block"
    return md_text.strip(), "full_md"

# ---------------- Schema & prompt ----------------

def build_schema() -> Dict[str, Any]:
    return {
        "name": "rb_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "cleaned_text": { "type": "string" },
                "architect_names": { "type": "array", "items": { "type": "string" } },
                "builder_names":   { "type": "array", "items": { "type": "string" } },
                "reasons_for_registration": { "type": "array", "items": { "type": "string" } },
                "construction_start_year": { "type": ["integer","null"], "minimum": 1000, "maximum": 2100 },
                "construction_end_year":   { "type": ["integer","null"], "minimum": 1000, "maximum": 2100 },
                "construction_start_date_text": { "type": ["string","null"] },
                "construction_end_date_text":   { "type": ["string","null"] },
                "registration_date_text":       { "type": ["string","null"] },
                "deregistration_date_text":     { "type": ["string","null"] },
                "notes": { "type": "string" }
            },
            "required": [
              "cleaned_text","architect_names","builder_names","reasons_for_registration",
              "construction_start_year","construction_end_year",
              "construction_start_date_text","construction_end_date_text",
              "registration_date_text","deregistration_date_text","notes"
            ]
        }
    }

PROMPT_TEMPLATE = """You will be given OCR text from an Isle of Man Registered Building document.
Tasks:
1) CLEAN the OCR text: fix obvious OCR artifacts (l/1/I swaps, hyphenation at line ends, duplicated headers), DO NOT invent facts.
2) EXTRACT and return as JSON with these fields:
   - architect_names (list)
   - builder_names (list)
   - reasons_for_registration (list of short phrases)
   - construction_start_year (int or null)
   - construction_end_year (int or null)
   - construction_start_date_text (string or null)
   - construction_end_date_text (string or null)
   - registration_date_text (string or null)
   - deregistration_date_text (string or null)
3) Put the cleaned text in 'cleaned_text'.

Context (from CSV; may help but use OCR as source of truth):
RB number: {rb}
Building name: {name}
Parish: {parish}
Status: {status}
Links: {links}

Return ONLY JSON per the schema.

--- OCR TEXT START ---
{ocr}
--- OCR TEXT END ---
"""

# ---------------- Coercion & classification ----------------

def coerce_to_schema_like(data: dict) -> dict:
    """Fill missing keys with sensible defaults; coerce obvious types."""
    out = {
        "cleaned_text": "",
        "architect_names": [],
        "builder_names": [],
        "reasons_for_registration": [],
        "construction_start_year": None,
        "construction_end_year": None,
        "construction_start_date_text": None,
        "construction_end_date_text": None,
        "registration_date_text": None,
        "deregistration_date_text": None,
        "notes": "",
    }
    if isinstance(data, dict):
        out.update({k: v for k, v in data.items() if k in out})

    for k in ("architect_names","builder_names","reasons_for_registration"):
        v = out[k]
        if isinstance(v, str):
            out[k] = [v] if v.strip() else []
        elif not isinstance(v, list):
            out[k] = []
        else:
            out[k] = [str(x) for x in v if str(x).strip()]

    for k in ("construction_start_year","construction_end_year"):
        v = out[k]
        if isinstance(v, str):
            m = re.search(r"\b(1[0-9]{3}|20[0-9]{2}|2100)\b", v)
            out[k] = int(m.group(0)) if m else None
        elif isinstance(v, (int, float)):
            out[k] = int(v)
        elif v is not None:
            out[k] = None

    for k in ("construction_start_date_text","construction_end_date_text","registration_date_text","deregistration_date_text","notes"):
        v = out[k]
        if v is not None and not isinstance(v, str):
            out[k] = str(v)

    if not isinstance(out["cleaned_text"], str):
        out["cleaned_text"] = ""

    return out

def _status_from_exc(e: Exception) -> Optional[int]:
    code = getattr(e, "status_code", None)
    if code: return int(code)
    resp = getattr(e, "response", None)
    if resp is not None:
        code = getattr(resp, "status_code", None)
        if code: return int(code)
    m = re.search(r"status[_ ]code[=:]\s*(\d{3})", str(e), re.IGNORECASE)
    return int(m.group(1)) if m else None

# ---------------- OpenAI call with retries & logging ----------------

def call_openai_with_retries(payload_text: str, model: str, args, rb: str) -> dict:
    from openai import OpenAI
    client = OpenAI()
    schema = build_schema()

    # Polite delay before each request
    time.sleep(random.uniform(args.delay_min, args.delay_max))

    # 1) Try STRUCTURED OUTPUTS (json_schema) via Chat Completions
    for attempt in range(args.oa_retries + 1):
        try:
            t0 = time.time()
            log(f"[RB {rb}] OpenAI call (json_schema) attempt {attempt+1}/{args.oa_retries+1}")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role":"system","content":"You are a meticulous archivist. Cite only the provided OCR text."},
                    {"role":"user","content": payload_text},
                ],
                temperature=0,
                response_format={"type":"json_schema","json_schema": schema},
            )
            out = resp.choices[0].message.content
            dur = time.time() - t0
            log(f"[RB {rb}] OpenAI success (json_schema) in {dur:.2f}s", "DONE")
            data = json.loads(out)

            # Optional validation
            if args.validate_schema:
                try:
                    from jsonschema import validate
                    validate(instance=data, schema=schema["schema"])
                except Exception as ve:
                    log(f"[RB {rb}] Schema validation warning: {ve}", "WARN", err=True)
                    save_debug_blob(args.debug_dir, rb, "schema-violation", json.dumps(data, ensure_ascii=False))
                    data = coerce_to_schema_like(data)

            return data

        except TypeError as e:
            log(f"[RB {rb}] json_schema not supported by SDK: {e}", "WARN", err=True)
            break  # move to json_object
        except Exception as e:
            status = _status_from_exc(e)
            dur = time.time() - t0
            log(f"[RB {rb}] OpenAI error (json_schema) status={status} after {dur:.2f}s: {e}", "WARN", err=True)
            if status == 401 and not args.retry_unauthorized:
                log("[Hint] 401 = auth/permissions; not a schema issue.", "WARN", err=True)
                raise
            if attempt >= args.oa_retries:
                log("[RB {rb}] Exhausted json_schema attempts; falling back to json_object.", "WARN", err=True)
                break
            sleep_s = min(args.backoff_min * (2 ** attempt) + random.uniform(0, args.backoff_min), args.backoff_cap)
            log(f"[RB {rb}] Backoff {sleep_s:.2f}s before retry (json_schema).")
            time.sleep(sleep_s)

    # 2) Fallback: JSON MODE (json_object)
    for attempt in range(args.oa_retries + 1):
        try:
            t0 = time.time()
            log(f"[RB {rb}] OpenAI call (json_object) attempt {attempt+1}/{args.oa_retries+1}")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role":"system","content":"You are a meticulous archivist. Cite only the provided OCR text."},
                    {"role":"user","content": payload_text},
                ],
                temperature=0,
                response_format={"type":"json_object"},
            )
            out = resp.choices[0].message.content
            dur = time.time() - t0
            log(f"[RB {rb}] OpenAI success (json_object) in {dur:.2f}s", "DONE")
            try:
                data = json.loads(out)
            except Exception as je:
                log(f"[RB {rb}] JSON decode error: {je}; first 200 chars: {out[:200]!r}", "WARN", err=True)
                save_debug_blob(args.debug_dir, rb, "json-decode", out)
                raise

            if args.validate_schema:
                try:
                    from jsonschema import validate
                    validate(instance=data, schema=schema["schema"])
                except Exception as ve:
                    log(f"[RB {rb}] Schema validation warning: {ve}", "WARN", err=True)
                    save_debug_blob(args.debug_dir, rb, "schema-violation", json.dumps(data, ensure_ascii=False))
                    data = coerce_to_schema_like(data)

            return data

        except Exception as e:
            status = _status_from_exc(e)
            dur = time.time() - t0
            log(f"[RB {rb}] OpenAI error (json_object) status={status} after {dur:.2f}s: {e}", "WARN", err=True)
            if status == 401 and not args.retry_unauthorized:
                log("[Hint] 401 = auth/permissions; not a schema issue.", "WARN", err=True)
                raise
            if attempt >= args.oa_retries:
                raise
            sleep_s = min(args.backoff_min * (2 ** attempt) + random.uniform(0, args.backoff_min), args.backoff_cap)
            log(f"[RB {rb}] Backoff {sleep_s:.2f}s before retry (json_object).")
            time.sleep(sleep_s)

# ---------------- Main ----------------

def main():
    args = parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        log("OPENAI_API_KEY is not set", "ERROR", err=True)
        sys.exit(2)

    rows = load_rows(args.index_csv)
    done = load_done_set(args.out_csv)
    if done:
        log(f"Resume mode: {len(done)} RBs already in {args.out_csv}; will skip those.")

    out_records: List[Dict[str, Any]] = []
    total = len(rows)
    processed = 0
    succeeded = 0
    failed = 0
    skipped = 0

    log(f"Starting extraction for {total} rows…")

    for row in rows:
        rb = str(row.get("RB_Number","")).strip()
        if not rb:
            skipped += 1
            log("Skipping row with empty RB_Number", "WARN", err=True)
            emit_jsonl(args.status_jsonl, {"rb": None, "event": "skip", "reason": "no_rb"})
            continue

        if rb in done:
            skipped += 1
            log(f"[RB {rb}] Already in out_csv; skipping.")
            emit_jsonl(args.status_jsonl, {"rb": rb, "event": "skip", "reason": "already_done"})
            continue

        md_path = Path(args.md_root) / f"rb-{rb}" / f"rb-{rb}.md"
        if not md_path.exists():
            skipped += 1
            log(f"[RB {rb}] No markdown found at {md_path}; skipping.", "WARN", err=True)
            emit_jsonl(args.status_jsonl, {"rb": rb, "event": "skip", "reason": "no_md"})
            continue

        md_text = read_md_text(md_path)
        ocr_text, source = extract_ocr_block(md_text)
        if not ocr_text.strip():
            skipped += 1
            log(f"[RB {rb}] OCR text empty; skipping.", "WARN", err=True)
            emit_jsonl(args.status_jsonl, {"rb": rb, "event": "skip", "reason": "no_ocr"})
            continue

        if len(ocr_text) > args.max_chars:
            log(f"[RB {rb}] OCR text trimmed from {len(ocr_text)} → {args.max_chars} chars.")
            ocr_text = ocr_text[:args.max_chars]

        payload = PROMPT_TEMPLATE.format(
            rb=rb,
            name=row.get("Building_Name",""),
            parish=row.get("Parish",""),
            status=row.get("Status",""),
            links=row.get("Links",""),
            ocr=ocr_text
        )

        log(f"[RB {rb}] Extraction start.")
        emit_jsonl(args.status_jsonl, {"rb": rb, "event": "start"})

        try:
            parsed = call_openai_with_retries(payload, args.model, args, rb)

            # Coerce just in case (harmless if already fine)
            parsed = coerce_to_schema_like(parsed)

            # Quick-glance preview
            yrs = ""
            if parsed.get("construction_start_year") or parsed.get("construction_end_year"):
                yrs = f"{parsed.get('construction_start_year') or ''}–{parsed.get('construction_end_year') or ''}"
            arch = ", ".join(parsed.get("architect_names", [])[:3])
            bld  = ", ".join(parsed.get("builder_names", [])[:3])
            reasons = parsed.get("reasons_for_registration", [])
            regtxt = parsed.get("registration_date_text")
            dereg  = parsed.get("deregistration_date_text")
            clen  = len(parsed.get("cleaned_text",""))
            log(f"[RB {rb}] Preview: arch=[{arch}] builders=[{bld}] years={yrs} reg='{regtxt}' dereg='{dereg}' reasons({len(reasons)}) cleaned_len={clen}")

            if args.preview_cleaned and parsed.get("cleaned_text"):
                snippet = parsed["cleaned_text"][:args.preview_cleaned].replace("\n"," ")
                log(f"[RB {rb}] cleaned_text[0:{args.preview_cleaned}]: {snippet}")

            if args.print_json_on_success:
                log(f"[RB {rb}] JSON:\n{json.dumps(parsed, ensure_ascii=False, indent=2)}")

            rec = {
                "RB_Number": rb,
                "Building_Name": row.get("Building_Name",""),
                "Parish": row.get("Parish",""),
                "Status": row.get("Status",""),
                "Date_Registered": row.get("Date_Registered",""),
                "Deregistration_Date": row.get("Deregistration_Date",""),
                "Links": row.get("Links",""),
                "Features": row.get("Features",""),
                "architect_names": parsed.get("architect_names", []),
                "builder_names": parsed.get("builder_names", []),
                "reasons_for_registration": parsed.get("reasons_for_registration", []),
                "construction_start_year": parsed.get("construction_start_year"),
                "construction_end_year": parsed.get("construction_end_year"),
                "construction_start_date_text": parsed.get("construction_start_date_text"),
                "construction_end_date_text": parsed.get("construction_end_date_text"),
                "registration_date_text": parsed.get("registration_date_text"),
                "deregistration_date_text": parsed.get("deregistration_date_text"),
                "notes": parsed.get("notes",""),
                "cleaned_text_source": source,
                "md_path": str(md_path),
            }
            out_records.append(rec)
            succeeded += 1
            emit_jsonl(args.status_jsonl, {"rb": rb, "event": "success"})
            log(f"[RB {rb}] Extraction DONE.", "DONE")

        except Exception as e:
            failed += 1
            status = _status_from_exc(e)
            if status == 401:
                log("[Hint] 401 = authentication/permissions (key/project); not a schema issue.", "WARN", err=True)
            elif status in (400, 422):
                log("[Hint] 400/422 often indicate invalid parameters or a schema/format mismatch.", "WARN", err=True)
            emit_jsonl(args.status_jsonl, {"rb": rb, "event": "failure", "status": status, "error": str(e)[:500]})
            log(f"[RB {rb}] Extraction FAILED (status={status}): {e}", "ERROR", err=True)

        processed += 1

    if out_records:
        save_rows(out_records, args.out_csv)
        log(f"Wrote {len(out_records)} rows → {args.out_csv}")

    log(f"Finished. processed={processed} succeeded={succeeded} failed={failed} skipped={skipped}")

if __name__ == "__main__":
    main()
