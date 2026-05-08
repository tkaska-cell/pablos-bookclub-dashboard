#!/usr/bin/env python3
"""raw CSV → 個人情報除去版（hashed_id + シナリオ + 日付のみ）

入力: csv/all_readers_clean.csv（生データ・PII含む）
出力: data/readers_anon.csv（hashed_id, scenario_name, registration_date）
出力後、生データは削除推奨。
"""
import csv
import hashlib
import hmac
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "csv" / "all_readers_clean.csv"
OUT_DIR = ROOT / "data"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "readers_anon.csv"
SALT_FILE = OUT_DIR / ".salt"

# 永続salt（同じメアドは同じhashになるが、別プロジェクトとは突合不能）
if SALT_FILE.exists():
    salt = SALT_FILE.read_bytes()
else:
    salt = secrets.token_bytes(32)
    SALT_FILE.write_bytes(salt)
    os.chmod(SALT_FILE, 0o600)

def hash_email(email: str) -> str:
    return hmac.new(salt, email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()[:16]

count = 0
seen = set()
with open(RAW, encoding="utf-8", errors="replace") as fin, \
     open(OUT, "w", encoding="utf-8", newline="") as fout:
    r = csv.DictReader(fin)
    w = csv.writer(fout)
    w.writerow(["hashed_id", "scenario_name", "registration_date"])
    for row in r:
        email = row.get("メールアドレス", "")
        scen = row.get("シナリオ名（購入商品）", "")
        date = row.get("登録日", "")
        if "@" not in email or not scen:
            continue
        hid = hash_email(email)
        key = (hid, scen)
        if key in seen:
            continue
        seen.add(key)
        w.writerow([hid, scen, date])
        count += 1

os.chmod(OUT, 0o600)
print(f"✓ {OUT.relative_to(ROOT)} 出力: {count}件")
print(f"   ユニーク参加者: {len(set(k[0] for k in seen))}名")
print(f"   salt: {SALT_FILE.relative_to(ROOT)} (chmod 600)")
