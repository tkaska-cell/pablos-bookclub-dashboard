#!/usr/bin/env bash
# 月次パイプライン: 集計を再生成 → PNGスナップショット（全高） → Driveアーカイブ → 「過去のレポート」へリンク挿入 → git push
# 使い方:
#   ./update_month.sh                       # 今日の日付でスナップショット
#   ./update_month.sh 2026-09-18 "9月読書会反映後"   # タグとリンク表示ラベル（省略時は「YYYY-MM-DD」のみ）
set -euo pipefail
cd "$(dirname "$0")"

DATE_TAG="${1:-$(date +%Y-%m-%d)}"
LABEL="${2:-}"
SNAPSHOT_PNG="snapshots/${DATE_TAG}_dashboard.png"
DRIVE_DIR="05_エキスパート読書会/読書会リピート率/snapshots"   # PABLOSドライブ（tkaska@へ共有済み）
PORT=8765
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

mkdir -p snapshots

echo "▶ 1/5 集計を再生成"
python3 build_dashboard.py

echo "▶ 2/5 ヘッドレスChromeでPNG生成（全高→余白トリム）"
python3 -m http.server "$PORT" >/dev/null 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT
sleep 1.5

"$CHROME" --headless=new --hide-scrollbars --disable-gpu \
  --window-size=1400,8000 \
  --virtual-time-budget=8000 \
  --screenshot="$SNAPSHOT_PNG" \
  "http://localhost:${PORT}/dashboard.html" >/dev/null 2>&1

kill $SERVER_PID 2>/dev/null || true
trap - EXIT

if [[ ! -s "$SNAPSHOT_PNG" ]]; then
  echo "✗ スクリーンショット生成失敗" >&2
  exit 1
fi
# 3500px固定だと下部（流入セグメント表・用語解説）が切れていたため、描画内容の最下端＋余白でトリムする
python3 - "$SNAPSHOT_PNG" <<'PY'
import sys, numpy as np
from PIL import Image
p = sys.argv[1]; im = Image.open(p); a = np.array(im.convert("L")).astype(int)
bg = a[-1, 0]
rows = np.where((np.abs(a - bg) > 8).any(axis=1))[0]
bottom = min(int(rows.max()) + 60, im.height) if len(rows) else im.height
if bottom >= im.height - 60:
    sys.exit("✗ 描画が8000pxを超えています。--window-size を上げてください")
im.crop((0, 0, im.width, bottom)).save(p); print(f"   トリム後 {im.width}x{bottom}")
PY

echo "▶ 3/5 Driveへアップロード"
rclone copy "$SNAPSHOT_PNG" "gdrive:${DRIVE_DIR}/" \
  --drive-shared-with-me \
  --create-empty-src-dirs

echo "▶ 4/5 「過去のレポート」プルダウンへリンク挿入"
FILE_ID=$(rclone lsjson "gdrive:${DRIVE_DIR}" --drive-shared-with-me --no-modtime \
  | python3 -c "import json,sys; n=sys.argv[1]; print(next((f['ID'] for f in json.load(sys.stdin) if f['Name']==n), ''))" "$(basename "$SNAPSHOT_PNG")")
if [[ -z "$FILE_ID" ]]; then
  echo "✗ DriveのファイルIDを取得できません（アップロード失敗？）" >&2
  exit 1
fi
python3 - "$FILE_ID" "$DATE_TAG" "$LABEL" <<'PY'
import sys
from pathlib import Path
fid, tag, label = sys.argv[1], sys.argv[2], sys.argv[3]
p = Path("dashboard.html"); s = p.read_text()
marker = "<!-- ARCHIVE_LIST_TOP:"
i = s.find(marker)
if i < 0:
    sys.exit("✗ dashboard.html に ARCHIVE_LIST_TOP マーカーがありません")
if fid in s:
    print("   同じファイルIDのリンクが既にある → 挿入スキップ"); sys.exit(0)
text = f"{tag}（{label}）" if label else tag
li = f'\n          <li><a href="https://drive.google.com/file/d/{fid}/view" target="_blank" rel="noopener">{text}</a></li>'
eol = s.find("\n", i)
p.write_text(s[:eol] + li + s[eol:]); print(f"   挿入: {text}")
PY

echo "▶ 5/5 変更があれば git push（公開GitHub Pages）"
git add dashboard_data.json data/spreadsheet_metrics.json dashboard.html build_dashboard.py update_month.sh .gitignore >/dev/null 2>&1 || true
if ! git diff --cached --quiet; then
  git commit -m "data: ${DATE_TAG} 月次更新"
  git push
else
  echo "   変更なし → push スキップ"
fi

echo
echo "✓ 完了"
echo "   スナップショット: ${SNAPSHOT_PNG}"
echo "   Drive: ${DRIVE_DIR}/$(basename "$SNAPSHOT_PNG")  (id=${FILE_ID})"
