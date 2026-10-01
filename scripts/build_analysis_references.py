"""Offline PDF reference renderer. Never modifies questions, answers or user data.

Requires development-only PyMuPDF. The runtime serves bundled PNGs, not PDFs.
Each crop is located from the original PDF image rectangle and caption, so the
different page-9 arrangement in 001-009 / 010-018 is preserved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
CAPTIONS = {
    "mc": "[전자접촉기]", "eocr": "[EOCR]", "timer": "[타이머]",
    "relay": "[8P 릴레이]", "fr": "[플리커릴레이]",
    "fls": "[플로트레스 스위치]", "ss": "[셀렉터 스위치]",
    "socket8": "[8P 소켓(베이스) 구성도]", "socket12": "[12P 소켓(베이스) 구성도]",
}


def render_references(source: Path, output: Path):
    inventory = {}
    for number in range(1, 19):
        pdf, = source.glob(f"*-{number:03d}-*.pdf")
        problem_id = f"qnet_electrician_practical_{number:03d}"
        target = output / problem_id / "study-references"
        target.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(pdf) as document:
            assert "동작 사항" in document[7].get_text(), pdf
            assert "내부 결선도" in document[8].get_text(), pdf
            records = {}
            def render(name, page, clip=None):
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), clip=clip, alpha=False)
                path = target / f"{name}.png"
                pix.save(path)
                records[name] = {"page": page.number + 1, "width": pix.width, "height": pix.height,
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                if clip:
                    records[name]["crop"] = list(clip)
            render("operation", document[7])
            page = document[8]
            render("internal", page)
            images = [pymupdf.Rect(item["bbox"]) for item in page.get_image_info()
                      if item["bbox"][1] > 130 and item["bbox"][3] < 740]
            for name, caption in CAPTIONS.items():
                matches = page.search_for(caption)
                if not matches:
                    continue  # No FR/FLS/SS illustration in 010-018: never invent one.
                assert len(matches) == 1, (pdf, caption)
                label = matches[0]
                cx = (label.x0 + label.x1) / 2
                candidates = [rect for rect in images if rect.x0 < cx < rect.x1 and -2 <= label.y0 - rect.y1 < 25]
                assert candidates, (pdf, caption)
                rect = min(candidates, key=lambda r: label.y0 - r.y1)
                crop = pymupdf.Rect(min(rect.x0, label.x0) - 3, rect.y0 - 3,
                                       max(rect.x1, label.x1) + 3, label.y1 + 3)
                render(name, page, crop)
            inventory[problem_id] = {"source": pdf.name, "source_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                                     "references": records}
        print(problem_id, len(records))
    return inventory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    inventory = render_references(args.source, ROOT / "problems")
    (ROOT / "catalog/qnet_analysis_references.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
