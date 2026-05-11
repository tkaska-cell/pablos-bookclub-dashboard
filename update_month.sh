#!/usr/bin/env bash
# 月次パイプライン: 集計を再生成 → git push → PNGスナップショット → Driveアーカイブ
# 使い方:
#   ./update_month.sh                # 今日の日付でスナップショット
#   ./update_month.sh 2026-05-31     # 任意のタグ指定
set -euo pipefail
cd "$(dirname "$0")"

DATE_TAG="${1:-$(date +%Y-%m-%d)}"
SNAPSHOT_PNG="snapshots/${DATE_TAG}_dashboard.png"
DRIVE_TEAM_ID="0APGoqxH1AJunUk9PVA"                  # AIVEST 共有ドライブ
DRIVE_DIR="読書会/読書会リピート率/月次スナップショット"
PORT=8765
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

mkdir -p snapshots

echo "▶ 1/4 集計を再生成"
python3 build_dashboard.py

echo "▶ 2/4 変更があれば git push"
git add dashboard_data.json data/spreadsheet_metrics.json dashboard.html >/dev/null 2>&1 || true
if ! git diff --cached --quiet; then
  git commit -m "data: ${DATE_TAG} 月次更新"
  git push
else
  echo "   変更なし → push スキップ"
fi

echo "▶ 3/4 ヘッドレスChromeでPNG生成"
python3 -m http.server "$PORT" >/dev/null 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT
sleep 1.5

"$CHROME" --headless=new --hide-scrollbars --disable-gpu \
  --window-size=1400,3500 \
  --virtual-time-budget=8000 \
  --screenshot="$SNAPSHOT_PNG" \
  "http://localhost:${PORT}/dashboard.html" >/dev/null 2>&1

kill $SERVER_PID 2>/dev/null || true
trap - EXIT

if [[ ! -s "$SNAPSHOT_PNG" ]]; then
  echo "✗ スクリーンショット生成失敗" >&2
  exit 1
fi

echo "▶ 4/4 Driveへアップロード"
rclone copy "$SNAPSHOT_PNG" "gdrive:${DRIVE_DIR}/" \
  --drive-team-drive="$DRIVE_TEAM_ID" \
  --create-empty-src-dirs

echo
echo "✓ 完了"
echo "   スナップショット: ${SNAPSHOT_PNG}"
echo "   Drive: ${DRIVE_DIR}/$(basename "$SNAPSHOT_PNG")"
