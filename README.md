# PABLOS エキスパート読書会 ダッシュボード

10回分（2025-07-23 〜 2026-04-23）の継続率分析と、月次NPS／参加人数サマリーを統合したダッシュボード。

## 公開ページ

`https://<owner>.github.io/<repo>/dashboard.html`

## このリポジトリで公開しているもの

| ファイル | 内容 | PII |
|---|---|---|
| `dashboard.html` | フロントエンド（Chart.js v4） | なし |
| `dashboard_data.json` | F2/ロイヤル/コホート/Tier/セグメントマトリクス（集計値のみ） | なし |
| `data/spreadsheet_metrics.json` | 月次の申込・当日参加・NPS（Google Sheets由来） | なし |
| `build_dashboard.py` | ハッシュ化済CSV → JSON集計スクリプト | — |
| `sanitize.py` | 生CSV → ハッシュ化CSV変換スクリプト（参考） | — |
| `SECURITY.md` | データ取り扱い方針 | — |

## このリポジトリに**含まれない**もの

- `data/.salt`（HMAC salt、chmod 600）
- `data/readers_anon.csv`（ハッシュ化済3列CSV、chmod 600）
- `csv/`（生PII、生成直後に削除）
- 認証情報を含むスクリプト

## メトリクスの定義

- **F2 転換率**: 過去ちょうど1回参加した人のうち、直近回もリピートした比率
- **ロイヤル継続率**: 過去2回以上参加した人のうち、直近回もリピートした比率
- **コホート継続率**: 各回の参加者のうち、直近回も参加した比率
- **NPS**: スプレッドシートのアンケート集計値（10点満点）

## ローカル確認

```bash
python3 -m http.server 8765
open http://localhost:8765/dashboard.html
```
