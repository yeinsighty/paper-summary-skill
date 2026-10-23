"""PDF를 쪽별 텍스트로 뽑는다. 글자가 없는 쪽은 Tesseract로 OCR한다.

사용: python -X utf8 -I extract_pages.py "<PDF>" "<출력 폴더>"
출력:
  <출력 폴더>/<PDF 이름>.json  쪽별 텍스트 (verify_quotes.py가 읽음)
  <출력 폴더>/<PDF 이름>.txt   쪽 구분선이 들어간 읽기용 텍스트
"""
import json
import os
import re
import shutil
import sys
from collections import Counter

import pymupdf

TESSDATA = r"C:\Program Files\Tesseract-OCR\tessdata"
MIN_CHARS = 50  # 이보다 글자가 적은 쪽은 스캔본으로 보고 OCR


def ocr(page):
    tp = page.get_textpage_ocr(language="kor+eng", dpi=300, full=True, tessdata=TESSDATA)
    return page.get_text(textpage=tp)


def page_number_candidates(text):
    """머리말·꼬리말(앞뒤 4줄)에 있는 모든 숫자. 쪽 번호만 쪽마다 같은 보정값을 낸다."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    nums = set()
    for l in lines[:4] + lines[-4:]:
        nums.update(int(n) for n in re.findall(r"(?<![\d.,:/(-])\d{1,4}(?![\d.,:/)-])", l))
    return nums


def main(pdf, out_dir):
    if not os.path.isdir(TESSDATA) and not shutil.which("tesseract"):
        print("경고: Tesseract를 찾지 못해 스캔본 OCR을 할 수 없습니다.", file=sys.stderr)
    doc = pymupdf.open(pdf)
    pages = []
    for i, page in enumerate(doc, start=1):
        text, used_ocr = page.get_text(), False
        if len(re.sub(r"\s", "", text)) < MIN_CHARS:
            try:
                text, used_ocr = ocr(page), True
            except Exception as e:
                print(f"PDF p.{i} OCR 실패: {e}", file=sys.stderr)
        pages.append({"pdf_page": i, "ocr": used_ocr, "text": text})

    # 인쇄 쪽 번호 = PDF 쪽 + 보정값. 3쪽 이상, 그리고 전체의 1/4 이상에서 같은 보정값이 나와야 채택
    offsets = Counter(n - p["pdf_page"] for p in pages for n in page_number_candidates(p["text"]))
    offset = None
    if offsets:
        best, count = offsets.most_common(1)[0]
        if count >= max(3, len(pages) // 4):
            offset = best

    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, os.path.splitext(os.path.basename(pdf))[0])
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"pdf": pdf, "offset": offset, "pages": pages}, f, ensure_ascii=False)
    with open(base + ".txt", "w", encoding="utf-8") as f:
        for p in pages:
            printed = p["pdf_page"] + offset if offset is not None else "?"
            mark = " | OCR" if p["ocr"] else ""
            f.write(f"\n===== PDF p.{p['pdf_page']} | 인쇄 p.{printed}{mark} =====\n{p['text']}")

    n_ocr = sum(p["ocr"] for p in pages)
    print(json.dumps({"쪽수": len(pages), "OCR한 쪽": n_ocr,
                      "인쇄쪽보정": offset if offset is not None else "[확인 필요]",
                      "텍스트": base + ".txt", "JSON": base + ".json"}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
