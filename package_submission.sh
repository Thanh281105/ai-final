#!/usr/bin/env bash
# Dong goi do an theo dung cau truc de bai yeu cau (ban cho macOS / Linux):
#
#   AI_final_<Project Group ID>_<Student ID>/
#     source/  task1/ task2/ task3/ README.md REAME.md requirement.txt requirements.txt
#     report.pdf
#     demo.txt
#
# Cach dung:  ./package_submission.sh <GroupId> <StudentId>      vi du: ./package_submission.sh G01 523H0178
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Cach dung: $0 <GroupId> <StudentId>" >&2
    exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
NAME="AI_final_$1_$2"
OUT="$ROOT/$NAME"
ZIP="$ROOT/$NAME.zip"

rm -rf "$OUT" "$ZIP"
mkdir -p "$OUT/source"

# 1. Ma nguon cua ba task (bo qua moi truong ao va file tam)
for t in task1 task2 task3; do
    rsync -a --exclude ".venv" --exclude ".venv-windows-old" --exclude "__pycache__" \
          --exclude "*.pyc" --exclude ".DS_Store" "$ROOT/$t/" "$OUT/source/$t/"
done

# 2. README va requirement (de bai ghi "REAME.md" va "requirement.txt": tao ca hai cach viet)
cp "$ROOT/README.md" "$OUT/source/README.md"
cp "$ROOT/README.md" "$OUT/source/REAME.md"
printf "python-sat>=0.1.8.dev1\npygame>=2.1\nmatplotlib>=3.3\n" > "$OUT/source/requirement.txt"
cp "$OUT/source/requirement.txt" "$OUT/source/requirements.txt"

# 3. Bao cao va link video
if [ -f "$ROOT/report.pdf" ]; then
    cp "$ROOT/report.pdf" "$OUT/report.pdf"
    if [ "$ROOT/report/report.tex" -nt "$ROOT/report.pdf" ]; then
        echo "CANH BAO: report/report.tex moi hon report.pdf - hay bien dich lai bao cao truoc khi nop." >&2
    fi
else
    echo "CANH BAO: khong tim thay report.pdf o thu muc goc." >&2
fi
cp "$ROOT/demo.txt" "$OUT/demo.txt"
if ! grep -Eq "^https?://[^[:space:]]+\.[^[:space:]]+" "$OUT/demo.txt"; then
    echo "CANH BAO: demo.txt chua co link video (dang la placeholder)." >&2
fi

# 4. Nen ZIP va don dep
(cd "$ROOT" && zip -qr "$ZIP" "$NAME" -x "*.DS_Store")
rm -rf "$OUT"
echo "Da tao: $ZIP"
