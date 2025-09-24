#!/usr/bin/env python3
"""
RB PDFs → cache, OCR, text & image extraction (timestamped logs + structured Markdown).

Output rules:
- If RB ref has a slash (e.g. '241/REGBLD1'):
    out_dir = output_base / 'rb-241' / 'REGBLD1'
    readable = 'REGBLD1-readable.pdf'
    md       = 'REGBLD1.md'
- Otherwise (e.g. '247'):
    out_dir = output_base / 'rb-247'
    readable = 'rb-247-readable.pdf'
    md       = 'rb-247.md'

Images always go in: out_dir / 'images' / <n>.jpg

Source PDFs are cached in --pdf_directory as rb-<ref>.pdf (subdirs created if ref contains '/').
"""

import argparse, re, sys, time, random, subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# ---------- logging ----------

def log(msg: str, level: str = "INFO", err: bool = False):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stream = sys.stderr if err or level in ("WARN", "ERROR") else sys.stdout
    print(f"[{ts}] [{level}] {msg}", file=stream)

# ---------- CLI / CSV ----------

def parse_args():
    p = argparse.ArgumentParser(description="Fetch, OCR, and extract text/images from RB PDFs.")
    p.add_argument("--index_csv", required=True, help="CSV with at least RB_Number and Links.")
    p.add_argument("--pdf_directory", required=True, help="Directory for source PDFs (rb-<ref>.pdf).")
    p.add_argument("--output_directory", required=True, help="Base directory for per-ref outputs.")
    p.add_argument("--user_agent", default="Mozilla/5.0 (compatible; RB-PDF-Collector/1.5)")
    p.add_argument("--delay_min", type=float, default=1.0)
    p.add_argument("--delay_max", type=float, default=3.0)
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--pdf_url_base", default=None, help="Base URL for relative links (e.g. https://pabc.gov.im)")
    return p.parse_args()

def read_rows(csv_path: str):
    import pandas as pd
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    need = {"RB_Number", "Links"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    return df.to_dict(orient="records"), set(df.columns)

# ---------- helpers ----------

def ref_from_row(row: dict) -> str:
    # keep slashes, dashes, underscores, dots; sanitize others
    ref = str(row.get("RB_Number", "")).strip()
    return re.sub(r"[^\w\-./]", "_", ref)

def split_ref(ref: str):
    """
    Returns (base, leaf, has_slash):
      - base = first segment (before first '/')
      - leaf = last segment (after last '/')
    """
    parts = [p for p in ref.strip("/").split("/") if p]
    if not parts:
        return ref, ref, False
    return parts[0], parts[-1], (len(parts) > 1)

def md_escape(text: str) -> str:
    return re.sub(r"([#*_`])", r"\\\1", text)

def pick_pdf_url(links: str, base: Optional[str]) -> Optional[str]:
    if not links:
        return None
    parts = re.split(r"[,\s]+", links.strip())
    for part in parts:
        if not part:
            continue
        url = part
        if base and url.startswith("/"):
            url = base.rstrip("/") + url
        if ".pdf" in url.lower():
            return url
    return None

def split_links(links: str, base: Optional[str]):
    urls = []
    if not links:
        return urls
    for part in re.split(r"[,\s]+", links.strip()):
        if not part:
            continue
        url = part
        if base and url.startswith("/"):
            url = base.rstrip("/") + url
        urls.append(url)
    return urls

def polite_sleep(a: float, b: float):
    if b <= 0: return
    time.sleep(random.uniform(max(0, a), b))

def download_pdf(url: str, dest: Path, ua: str, timeout: int, retries: int) -> bool:
    import requests
    headers = {"User-Agent": ua, "Accept": "application/pdf, */*"}
    for attempt in range(retries + 1):
        try:
            with requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True) as r:
                ctype = (r.headers.get("Content-Type") or "").lower()
                if r.status_code == 200 and ("pdf" in ctype or url.lower().endswith(".pdf")):
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(8192):
                            if chunk:
                                f.write(chunk)
                    return True
                else:
                    log(f"HTTP {r.status_code} for {url} (Content-Type: {ctype})", "WARN", err=True)
        except Exception as e:
            log(f"Download error: {e}", "WARN", err=True)
        time.sleep(1.5 * (attempt + 1))
    return False

def have_ocrmypdf() -> bool:
    try:
        subprocess.run(["ocrmypdf", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def run_ocr(input_pdf: Path, output_pdf: Path):
    if not have_ocrmypdf():
        return False, "ocrmypdf not found; skipping OCR."
    try:
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ocrmypdf", "--deskew", "--clean", "--optimize", "3", "--skip-text",
             str(input_pdf), str(output_pdf)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True, None
    except subprocess.CalledProcessError as e:
        return False, f"OCR failed (exit {e.returncode})."
    except Exception as e:
        return False, f"OCR error: {e}"

def extract_text(pdf: Path) -> str:
    text = ""
    try:
        import fitz
        with fitz.open(pdf) as doc:
            text = "\n".join(page.get_text("text") for page in doc)
    except Exception:
        pass
    if text.strip():
        return text.strip()
    try:
        from pdfminer_high_level import extract_text as pdfminer_extract_text  # type: ignore
    except Exception:
        # pdfminer.six import path (compat)
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore
        except Exception:
            pdfminer_extract_text = None
    if pdfminer_extract_text:
        try:
            return (pdfminer_extract_text(str(pdf)) or "").strip()
        except Exception:
            return ""
    return ""

def extract_images(pdf: Path, out_dir: Path) -> int:
    saved = 0
    try:
        import fitz
    except Exception:
        return 0
    try:
        from PIL import Image
        pil_ok = True
    except Exception:
        pil_ok = False

    try:
        with fitz.open(pdf) as doc:
            out_dir.mkdir(parents=True, exist_ok=True)
            idx = 1
            for page in doc:
                for img in page.get_images(full=True):
                    xref = img[0]
                    try:
                        base = doc.extract_image(xref)
                        data = base["image"]
                        ext = base.get("ext", "bin").lower()
                        if pil_ok:
                            from io import BytesIO
                            im = Image.open(BytesIO(data))
                            if im.mode in ("RGBA", "P"): im = im.convert("RGB")
                            (out_dir / f"{idx:04d}.jpg").parent.mkdir(parents=True, exist_ok=True)
                            im.save(out_dir / f"{idx:04d}.jpg", "JPEG", quality=90)
                        else:
                            with open(out_dir / f"{idx:04d}.{ext}", "wb") as f:
                                f.write(data)
                        idx += 1; saved += 1
                    except Exception:
                        continue
    except Exception:
        return saved
    return saved

def build_markdown(ref: str, row: dict, ocr_text: str, links_resolved: list, csv_cols: set) -> str:
    """Compose rb-*.md with # RB <ref>, name paragraph, Parish, dates, optional Features, Links, OCR."""
    building_name = str(row.get("Building_Name", "")).strip() or "(Unknown building)"
    date_reg = str(row.get("Date_Registered", "")).strip()
    parish = str(row.get("Parish", "")).strip() if "Parish" in csv_cols else ""
    status = str(row.get("Status", "")).strip() if "Status" in csv_cols else ""
    dereg_date = str(row.get("Deregistration_Date", "")).strip() if "Deregistration_Date" in csv_cols else ""
    features_raw = str(row.get("Features", "")).strip() if "Features" in csv_cols else ""

    lines = [f"# RB {ref}", "", md_escape(building_name), ""]

    if parish:
        lines += ["## Parish", parish, ""]

    lines += ["## Registration date", (date_reg if date_reg else "(not provided)"), ""]

    if dereg_date or status.lower() == "de-registered":
        lines += ["## De-registration date", (dereg_date if dereg_date else "(not provided)"), ""]

    if features_raw:
        lines.append("## Features")
        for p in [p.strip() for p in re.split(r"[;|,]+", features_raw) if p.strip()]:
            lines.append(f"- {p}")
        lines.append("")

    lines.append("## Links")
    if links_resolved:
        for url in links_resolved:
            lines.append(f"- {url}")
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("## OCR")
    if ocr_text.strip():
        lines.append("```")
        lines.append(ocr_text)
        lines.append("```")
    else:
        lines.append("(no extractable text)")
    lines.append("")

    return "\n".join(lines)

# ---------- core ----------

def process_row(row: dict, pdf_dir: Path, out_base: Path, ua: str,
                delay_min: float, delay_max: float, timeout: int,
                retries: int, base_url: Optional[str], csv_cols: set) -> None:
    ref = ref_from_row(row)
    if not ref:
        log("Missing RB_Number; skipping.", "WARN", err=True)
        return

    base, leaf, has_slash = split_ref(ref)

    # Paths (source PDF cache — may create subdirs if has_slash)
    src_pdf = pdf_dir / f"rb-{ref}.pdf"

    # Output directory according to the new rules
    out_dir = (out_base / f"rb-{base}" / leaf) if has_slash else (out_base / f"rb-{ref}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # File names depend on slash-ness
    if has_slash:
        readable_pdf = out_dir / f"{leaf}-readable.pdf"
        md_path = out_dir / f"{leaf}.md"
    else:
        readable_pdf = out_dir / f"rb-{ref}-readable.pdf"
        md_path = out_dir / f"rb-{ref}.md"

    imgs_dir = out_dir / "images"

    # Ensure we have a source PDF
    if not src_pdf.exists():
        url = pick_pdf_url(row.get("Links", ""), base_url)
        if url:
            log(f"Downloading {url} → {src_pdf}")
            ok = download_pdf(url, src_pdf, ua, timeout, retries)
            if not ok:
                log(f"Failed to download {url} (ref={ref})", "WARN", err=True)
            polite_sleep(delay_min, delay_max)
        else:
            log(f"No PDF URL in Links for ref={ref}", "WARN", err=True)

    if not src_pdf.exists():
        log(f"Missing source PDF for ref={ref}; skipping.", "WARN", err=True)
        return

    # OCR → save permanent readable PDF in out_dir
    used_pdf = readable_pdf if readable_pdf.exists() else src_pdf
    if used_pdf is src_pdf:
        ok, note = run_ocr(src_pdf, readable_pdf)
        if ok and readable_pdf.exists():
            used_pdf = readable_pdf
        else:
            if note:
                log(f"{note} (ref={ref})")

    # Extract text & images
    text = extract_text(used_pdf)
    img_count = extract_images(used_pdf, imgs_dir)

    # Build markdown (features included only if present)
    links_resolved = split_links(row.get("Links", ""), base_url)
    md = build_markdown(ref, row, text, links_resolved, csv_cols)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    log(f"ref={ref} → {md_path.name}, images:{img_count}, readable:{readable_pdf.exists()}", "DONE")

def main():
    args = parse_args()
    pdf_dir = Path(args.pdf_directory); pdf_dir.mkdir(parents=True, exist_ok=True)
    out_base = Path(args.output_directory); out_base.mkdir(parents=True, exist_ok=True)

    try:
        rows, csv_cols = read_rows(args.index_csv)
    except Exception as e:
        log(f"CSV read failed: {e}", "ERROR", err=True)
        sys.exit(2)

    log(f"Processing {len(rows)} rows…")
    for row in rows:
        try:
            process_row(row, pdf_dir, out_base, args.user_agent,
                        args.delay_min, args.delay_max, args.timeout,
                        args.retries, args.pdf_url_base, csv_cols)
        except KeyboardInterrupt:
            log("Interrupted by user.", "INFO")
            break
        except Exception as e:
            ref = str(row.get("RB_Number","")).strip()
            log(f"Unexpected error on ref={ref}: {type(e).__name__}: {e}", "WARN", err=True)

    log("Finished.")

if __name__ == "__main__":
    main()
