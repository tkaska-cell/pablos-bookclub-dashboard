# データ取扱方針

## 原則

このプロジェクトは PABLOS 読書会の継続率分析が目的。
個人情報（氏名・メアド・電話・住所）は分析に**不要**なため、ローカル保管しない。

## パイプライン

```
MyASP CSV (PII含む)  ──[一時取得]──>  sanitize.py  ──>  data/readers_anon.csv (HMAC-SHA256ハッシュ済)
                                          │
                                          └─> 元CSVは即削除
```

`data/readers_anon.csv` は以下3列のみ：
- `hashed_id`: メアドをHMAC-SHA256でハッシュ化（先頭16文字）
- `scenario_name`: シナリオ名（公開情報）
- `registration_date`: 登録日時

ソルト (`data/.salt`) はランダム32バイト、`chmod 600`。
他プロジェクトとの突合は不可能（プロジェクト固有salt）。

## 運用ルール

- ❌ 生CSVを `csv/` に置きっぱなしにしない（取得 → 即sanitize → 即削除）
- ❌ `/tmp/` にPII残骸を残さない（セッション終了時にクリーンアップ）
- ❌ Cookieファイル・認証情報をコミットしない
- ❌ `data/.salt` を共有・コミットしない
- ✅ 共有OK: `dashboard.html`, `dashboard_data.json`, `build_dashboard.py`, `sanitize.py`
- ✅ 集計結果（人数・率）のみ外部共有可

## 2025年データの再取得が必要な場合

1. MyASP管理画面に手動ログイン → 必要シナリオの「ユーザー一覧」CSVをダウンロード
2. `csv/` に配置 → `python3 sanitize.py` 実行
3. 即 `rm -rf csv/`
4. `python3 build_dashboard.py` で集計再生成

または、各シナリオ取得→hash化→生データ削除を1ステップで行うパイプ版を後日整備。

## 削除確認

```bash
ls csv/                    # → No such file（あればNG）
ls /tmp/*cookie* 2>/dev/null  # → 何も出ない（あればNG）
ls /tmp/*.csv     2>/dev/null  # → 何も出ない（あればNG）
```
