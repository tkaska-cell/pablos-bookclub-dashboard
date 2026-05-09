#!/usr/bin/env python3
"""data/readers_anon.csv → dashboard_data.json

PIIを含まないハッシュ化済みCSVから集計のみ実行。
"""
import csv
import json
import re
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "data" / "readers_anon.csv"
OUT = ROOT / "dashboard_data.json"

# シナリオ名 → (date, segment) マッピング
EVENT_PATTERNS = [
    # 2026
    (re.compile(r"本とAIで自分の価値.*4月23日"), ("2026-04-23", "一般")),
    (re.compile(r"エキスパート読書会4月23日"), ("2026-04-23", "メンバー(NFT)")),
    (re.compile(r"2026年3月18日.*著者"), ("2026-03-18", "招待")),
    (re.compile(r"2026年3月18日.*LINE"), ("2026-03-18", "LINE")),
    (re.compile(r"2026年3月18日"), ("2026-03-18", "一般")),
    (re.compile(r"2026年2月18日.*著者"), ("2026-02-18", "招待")),
    (re.compile(r"2026年2月18日.*LINE"), ("2026-02-18", "LINE")),
    (re.compile(r"2026年2月18日"), ("2026-02-18", "一般")),
    (re.compile(r"エキスパート読書会2026年1月27日（LINE）"), ("2026-01-27", "LINE")),
    (re.compile(r"エキスパート読書会2026年1月27日（一般）"), ("2026-01-27", "一般")),
    (re.compile(r"エキスパート読書会2026年1月27日$"), ("2026-01-27", "一般")),
    # 2025
    (re.compile(r"2025年12月3日.*著者"), ("2025-12-03", "招待")),
    (re.compile(r"2025年12月3日.*LINE"), ("2025-12-03", "LINE")),
    (re.compile(r"2025年12月3日"), ("2025-12-03", "一般")),
    (re.compile(r"エキスパート読書会2025年10月21日（NFT）"), ("2025-10-21", "メンバー(NFT)")),
    (re.compile(r"エキスパート読書会2025年10月21日（LINE）"), ("2025-10-21", "LINE")),
    (re.compile(r"エキスパート読書会2025年10月21日（一般）"), ("2025-10-21", "一般")),
    (re.compile(r"エキスパート読書会2025年9月19日（NFT）"), ("2025-09-19", "メンバー(NFT)")),
    (re.compile(r"エキスパート読書会2025年9月19日（LINE）"), ("2025-09-19", "LINE")),
    (re.compile(r"エキスパート読書会2025年9月19日（一般）"), ("2025-09-19", "一般")),
    (re.compile(r"エキスパート読書会2025年9月10日（NFT）"), ("2025-09-10", "メンバー(NFT)")),
    (re.compile(r"エキスパート読書会2025年9月10日（LINE）"), ("2025-09-10", "LINE")),
    (re.compile(r"エキスパート読書会2025年9月10日（一般）"), ("2025-09-10", "一般")),
    (re.compile(r"エキスパート読書会2025年9月10日（特別招待）"), ("2025-09-10", "招待")),
    (re.compile(r"エキスパート読書会2025年8月28日（NFT）"), ("2025-08-28", "メンバー(NFT)")),
    (re.compile(r"エキスパート読書会2025年8月28日（LINE）"), ("2025-08-28", "LINE")),
    (re.compile(r"エキスパート読書会2025年8月28日（一般）"), ("2025-08-28", "一般")),
    (re.compile(r"エキスパート読書会2025年7月23日（NFT）"), ("2025-07-23", "メンバー(NFT)")),
    (re.compile(r"エキスパート読書会2025年7月23日（LINE）"), ("2025-07-23", "LINE")),
    (re.compile(r"エキスパート読書会2025年7月23日（一般）"), ("2025-07-23", "一般")),
]

def classify(name: str):
    for pat, val in EVENT_PATTERNS:
        if pat.search(name):
            return val
    return None

# 集計
participants = defaultdict(set)  # date → {hashed_id}
matrix = defaultdict(lambda: defaultdict(set))  # date → segment → {hashed_id}

with open(SRC, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        c = classify(row["scenario_name"])
        if c is None:
            continue
        date, seg = c
        hid = row["hashed_id"]
        participants[date].add(hid)
        matrix[date][seg].add(hid)

dates = sorted(participants.keys())
latest = dates[-1] if dates else None
prev_dates = dates[:-1] if dates else []

# 過去参加履歴
history = defaultdict(set)  # hashed_id → {dates participated}
for d, hids in participants.items():
    for h in hids:
        history[h].add(d)

# Latest breakdown
latest_set = participants[latest]
new_set = {h for h in latest_set if history[h] == {latest}}
repeat_set = latest_set - new_set
total = len(latest_set)
new_count = len(new_set)
rep_count = len(repeat_set)

# Tier
tier_2 = {h for h in repeat_set if len(history[h]) == 2}
tier_3p = {h for h in repeat_set if len(history[h]) >= 3}

# 直近3回連続参加（直近イベント+その前2回すべて出席）
if len(dates) >= 3:
    last3 = dates[-3:]
    streak3_set = participants[last3[0]] & participants[last3[1]] & participants[last3[2]]
else:
    last3 = dates[:]
    streak3_set = set()
streak3_count = len(streak3_set)
streak3_rate = round(100 * streak3_count / total, 1) if total else 0
# 3回以上 tier を 連続 vs 飛び石 に分解
tier_3p_streak = tier_3p & streak3_set
tier_3p_skip = tier_3p - tier_3p_streak

# F2: 過去ちょうど1回参加 → 今回もリピート
past_one = {h for h, ds in history.items() if (latest in ds and len(ds) == 2) or (latest not in ds and len(ds) == 1)}
# 直前回までで1回だけ参加した人を母数に、今回参加したかを見る
prior_participants = set()
for d in prev_dates:
    prior_participants |= participants[d]
prior_once = {h for h in prior_participants if len(history[h] - {latest}) == 1}
f2_num = len(prior_once & latest_set)
f2_den = len(prior_once)
f2_rate = round(100 * f2_num / f2_den, 1) if f2_den else 0

# ロイヤル: 過去2回以上参加 → 今回も
prior_2plus = {h for h in prior_participants if len(history[h] - {latest}) >= 2}
loyal_num = len(prior_2plus & latest_set)
loyal_den = len(prior_2plus)
loyal_rate = round(100 * loyal_num / loyal_den, 1) if loyal_den else 0

# Cohort
cohort = []
for d in prev_dates:
    base = len(participants[d])
    cont = len(participants[d] & latest_set)
    cohort.append({
        "date": d,
        "base": base,
        "continued": cont,
        "rate": round(100 * cont / base, 1) if base else 0,
    })

# Matrix table
mat_rows = []
for d in dates:
    row = {"date": d, "total": len(participants[d])}
    for seg in ["メンバー(NFT)", "一般", "LINE", "招待"]:
        row[seg] = len(matrix[d].get(seg, set()))
    mat_rows.append(row)

result = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "period": f"{dates[0]} 〜 {latest}（{len(dates)}回分）",
    "note": "※ 個人情報を含まないハッシュ化済みデータ（HMAC-SHA256・プロジェクト固有salt）から集計。2025年6月26日のシナリオはMyASP上でデータ不整合のため未集計。",
    "matrix": mat_rows,
    "cohort_to_latest": cohort,
    "latest": {
        "date": latest,
        "total": total,
        "new": new_count,
        "repeat": rep_count,
        "new_pct": round(100 * new_count / total, 1) if total else 0,
        "repeat_pct": round(100 * rep_count / total, 1) if total else 0,
    },
    "tier": {
        "新規": new_count,
        "2回目": len(tier_2),
        "3回以上": len(tier_3p),
    },
    "streak3": {
        "dates": last3,
        "count": streak3_count,
        "rate_of_latest": streak3_rate,
        "tier3_consecutive": len(tier_3p_streak),
        "tier3_intermittent": len(tier_3p_skip),
    },
    "kpi": {
        "f2_rate": f2_rate,
        "f2_numerator": f2_num,
        "f2_denominator": f2_den,
        "loyal_rate": loyal_rate,
        "loyal_numerator": loyal_num,
        "loyal_denominator": loyal_den,
    },
    "totals": {
        "cumulative_unique": len(history),
    },
}

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(f"✓ {OUT.name} 更新")
print(f"   F2: {f2_rate}% ({f2_num}/{f2_den})")
print(f"   ロイヤル: {loyal_rate}% ({loyal_num}/{loyal_den})")
print(f"   直近3回連続参加: {streak3_count}名 ({streak3_rate}% / 直近回参加者ベース) [{', '.join(last3)}]")
print(f"   {latest}: {total}名（新規{new_count} / リピート{rep_count}）")
print(f"   累計ユニーク: {len(history)}名")
