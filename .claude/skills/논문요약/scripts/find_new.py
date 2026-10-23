"""01_원본에서 아직 요약하지 않은 PDF를 찾는다.

사용: python -X utf8 -I find_new.py "<논문요약 폴더>"
01_원본 바로 아래의 PDF만 본다(주제 폴더를 쓰지 않음).
이미 요약한 (원본) 파일과 내용이 똑같은 사본은 "사본"으로 표시한다(md5 비교).
한 줄에 하나씩 JSON으로 출력한다. 처리할 논문이 없으면 아무것도 출력하지 않는다.
"""
import hashlib
import json
import os
import sys

root = sys.argv[1]
src = os.path.join(root, "01_원본")
dst = os.path.join(root, "02_요약본")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


files = sorted(fn for fn in os.listdir(src)
               if os.path.isfile(os.path.join(src, fn)) and fn.lower().endswith(".pdf"))
originals = [fn for fn in files if fn.startswith("(원본) ")]
original_hashes = None  # 새 논문이 있을 때만 계산

for fn in files:
    path = os.path.join(src, fn)
    out = {"파일": fn, "경로": path}
    if fn.startswith("(원본) "):
        stem = fn[len("(원본) "):-4]
        if os.path.exists(os.path.join(dst, f"(요약본) {stem}.md")):
            continue  # 이미 요약함
        out["상태"] = "이름은 바뀌었지만 요약본 없음"
    else:
        if original_hashes is None:
            original_hashes = {}
            for o in originals:
                original_hashes.setdefault(md5(os.path.join(src, o)), o)
        same = original_hashes.get(md5(path))
        if same:
            out["상태"] = "이미 요약한 논문의 사본"
            out["같은 원본"] = same
        else:
            out["상태"] = "새 논문"
    print(json.dumps(out, ensure_ascii=False))

# 하위 폴더에 넣은 PDF는 처리하지 않으므로 알려 준다
for dp, _, fns in os.walk(src):
    if dp == src:
        continue
    for fn in fns:
        if fn.lower().endswith(".pdf"):
            print(json.dumps({"파일": fn, "경로": os.path.join(dp, fn),
                              "상태": "하위 폴더에 있어 처리하지 않음 (01_원본 바로 아래로 옮겨야 함)"},
                             ensure_ascii=False))
