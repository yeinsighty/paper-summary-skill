"""요약본의 인용 문장이 표시한 쪽에 실제로 있는지 확인한다.

사용: python -X utf8 -I verify_quotes.py "<요약본.md>" "<extract_pages.py가 만든 .json>"
검사 대상: '> "원문" (p. 12)', '(pp. 12-13)', '(PDF p. 5)' 형식의 줄.
띄어쓰기·줄바꿈·따옴표 차이는 무시하고, '…' 또는 '...'로 줄인 부분은 앞뒤 조각을 각각 찾는다.
하나라도 못 찾으면 종료 코드 1.
"""
import json
import re
import sys
import unicodedata

QUOTE = re.compile(r'^>\s*["“](.+)["”]\s*\((PDF\s*)?pp?\.\s*(\d+)(?:\s*[-–~]\s*(\d+))?\)')


def norm(s):
    # NFKC: 'ﬁ' 같은 합자와 전각 문자를 일반 글자로 맞춘다
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\s\"'“”‘’「」『』\-­]", "", s).lower()


def main(md_path, json_path):
    data = json.load(open(json_path, encoding="utf-8"))
    pages = {p["pdf_page"]: norm(p["text"]) for p in data["pages"]}
    md = open(md_path, encoding="utf-8").read()
    m = re.search(r"^인쇄쪽보정:\s*(-?\d+)", md, re.M)
    offset = int(m.group(1)) if m else data["offset"]

    ok, fails = 0, []
    for line in md.splitlines():
        q = QUOTE.match(line.strip())
        if not q:
            continue
        quote, is_pdf, start, end = q.group(1), q.group(2), int(q.group(3)), q.group(4)
        end = int(end) if end else start
        if not is_pdf:
            if offset is None:
                fails.append((line, "인쇄쪽보정을 몰라 쪽을 확인할 수 없음"))
                continue
            start, end = start - offset, end - offset
        # 문장이 쪽을 넘어갈 수 있어 앞뒤 1쪽까지 이어 붙여 찾는다
        window = "".join(pages.get(i, "") for i in range(start - 1, end + 2))
        pos, found = 0, True
        for frag in re.split(r"…|\.\.\.", quote):
            frag = norm(frag)
            if not frag:
                continue
            pos = window.find(frag, pos)
            if pos < 0:
                found = False
                break
        if found:
            ok += 1
        else:
            fails.append((line, "표시한 쪽 근처에서 찾지 못함"))

    print(f"확인 {ok}개 / 실패 {len(fails)}개")
    for line, why in fails:
        print(f"- {why}: {line[:120]}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
