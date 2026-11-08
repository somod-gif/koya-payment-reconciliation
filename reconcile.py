#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py
"""
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation


def parse_ts(value):
    """Return a sortable key for an ISO-8601 timestamp."""
    if not isinstance(value, str) or not value.strip():
        return (0.0, "")
    raw = value.strip()
    try:
        return (datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp(), raw)
    except ValueError:
        return (0.0, raw)


def parse_amount(value):
    """Parse numbers as well as strings like "4,804.15"."""
    if isinstance(value, (int, float)):
        raw = str(value)
    elif isinstance(value, str):
        raw = value.replace(",", "").replace("₦", "").replace("NGN", "").strip()
    else:
        return None

    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


# A payment may have several attempts; only the latest attempt per txn_id
# counts. Timestamps decide order, with line order breaking exact ties.
latest = {}
with open("payments.jsonl", encoding="utf-8") as f:
    for index, line in enumerate(f):
        if not line.strip():
            continue

        try:
            event = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            # Production export contains truncated lines; ignore them.
            continue
        if not isinstance(event, dict):
            continue

        txn_id = event.get("txn_id")
        if txn_id is None or str(txn_id).strip() == "":
            continue

        amount = parse_amount(event.get("amount"))
        if amount is None:
            continue

        key = str(txn_id).strip()
        candidate = (parse_ts(event.get("ts")), index, event.get("status"), amount)
        current = latest.get(key)
        if current is None or candidate[:2] >= current[:2]:
            latest[key] = candidate

count = 0
total = Decimal("0")
for _, _, status, amount in latest.values():
    if status == "success":
        count += 1
        total += amount

with open("expected.txt", encoding="utf-8") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")
