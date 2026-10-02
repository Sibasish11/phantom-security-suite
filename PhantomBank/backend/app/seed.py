"""Create two disjoint, wholly synthetic banking datasets."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from .auth import hash_password
from .config import HONEYPOT_CUSTOMER_ID, REAL_CUSTOMER_ID, settings
from .db import Database


PASSWORDS = {
    "real": "DemoMaya!2025",
    "honeypot": "ProbeJohn!2025",
}


def seed_database(database: Database, target: str) -> None:
    database.init_schema()
    if target == "real":
        customer_id = REAL_CUSTOMER_ID
        name = "Maya Bennett"
        email = "maya.bennett@northstar.test"
        phone = "+44 20 5550 0182"
        address = "14 Rowan Quay, Bristol, BS1 4NX"
        marker = "REAL-MAYA-7Q4N"
        account_one = ("real-account-everyday-001", "Everyday", "RB-2048-7712", 428650, 410000)
        account_two = ("real-account-savings-001", "Savings", "RB-2048-8834", 1250000, 1250000)
        beneficiaries = [
            ("real-beneficiary-alex-001", "Alex Morgan", "•• 7714", "Cedar & Co Bank"),
            ("real-beneficiary-river-001", "River & Stone Studio", "•• 1059", "Brightline Bank"),
        ]
        cards = [
            ("real-card-visa-001", "Everyday card", "•••• 1842", "Visa debit", "Active", "09/28", 250000),
            ("real-card-virtual-001", "Travel virtual card", "•••• 6027", "Virtual", "Active", "02/27", 150000),
        ]
        transactions = [
            ("Coffee & Kin", "Morning coffee", "Food & drink", "out", 480),
            ("Northstar Payroll", "Salary · February", "Income", "in", 324000),
            ("Harbour Market", "Weekly groceries", "Shopping", "out", 6840),
            ("Brightline Energy", "Direct debit", "Bills", "out", 9200),
            ("Lumen Rail", "Bristol to London", "Travel", "out", 4350),
            ("Northstar Payroll", "Salary · January", "Income", "in", 324000),
            ("Pine & Paper", "Home supplies", "Shopping", "out", 3820),
        ]
    else:
        customer_id = HONEYPOT_CUSTOMER_ID
        name = "John Carter"
        email = "john.carter@vaultline.test"
        phone = "+44 20 5550 0731"
        address = "88 Meridian Yard, Leeds, LS1 2DE"
        marker = "DECOY-JOHN-3M8Z"
        account_one = ("decoy-account-ops-991", "Current", "HD-7719-4402", 9173400, 9173400)
        account_two = ("decoy-account-reserve-991", "Reserve", "HD-7719-5520", 28000000, 28000000)
        beneficiaries = [
            ("decoy-beneficiary-north-991", "Northbridge Logistics", "•• 4402", "Crown Meridian Bank"),
            ("decoy-beneficiary-lattice-991", "Lattice Research Ltd", "•• 1008", "Harbour National"),
            ("decoy-beneficiary-elm-991", "Elmworks Services", "•• 9211", "Crown Meridian Bank"),
        ]
        cards = [
            ("decoy-card-ops-991", "Operations card", "•••• 4402", "Visa debit", "Active", "11/29", 1200000),
            ("decoy-card-vault-991", "Reserve virtual", "•••• 1190", "Virtual", "Active", "06/28", 600000),
        ]
        transactions = [
            ("Carter & Vale Holdings", "Settlement batch", "Income", "in", 1800000),
            ("Meridian Freight", "Invoice 4471", "Operations", "out", 228000),
            ("Lattice Research Ltd", "Research retainer", "Services", "out", 97500),
            ("Crown Meridian Bank", "Treasury sweep", "Transfer", "in", 500000),
            ("Northbridge Logistics", "Contractor payout", "Operations", "out", 144000),
        ]

    now = datetime.now(timezone.utc)
    with database.transaction(immediate=True) as cursor:
        # Additive bootstrap only: a restart must never erase transfers or
        # destination audit evidence. Resetting a demo is an operator action.
        cursor.execute("SELECT COUNT(*) FROM bank_customers")
        count_row = cursor.fetchone()
        count = next(iter(count_row.values())) if isinstance(count_row, dict) else count_row[0]
        if count:
            print(f"{target}: existing synthetic dataset preserved")
            return
        cursor.execute(
            database.adapt("INSERT INTO bank_customers (id, full_name, email, password_hash, phone, address, customer_marker, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"),
            (customer_id, name, email, hash_password(PASSWORDS[target]), phone, address, marker, now.isoformat()),
        )
        for account in (account_one, account_two):
            cursor.execute(
                database.adapt("INSERT INTO accounts (id, customer_id, account_type, account_number, balance_cents, available_cents, currency, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'GBP', 'active', ?)"),
                (
                    account[0], customer_id, account[1], account[2], account[3], account[4], now.isoformat()
                ),
            )
        for beneficiary_id, beneficiary_name, hint, bank_name in beneficiaries:
            cursor.execute(
                database.adapt("INSERT INTO beneficiaries (id, customer_id, name, account_hint, bank_name, created_at) VALUES (?, ?, ?, ?, ?, ?)"),
                (beneficiary_id, customer_id, beneficiary_name, hint, bank_name, now.isoformat()),
            )
        for card in cards:
            cursor.execute(
                database.adapt("INSERT INTO cards (id, customer_id, card_name, card_number_masked, card_type, status, expires_on, spending_limit_cents) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"),
                (card[0], customer_id, card[1], card[2], card[3], card[4], card[5], card[6]),
            )
        account_id = account_one[0]
        for index, (merchant, description, category, direction, amount) in enumerate(transactions):
            occurred = now - timedelta(days=index * 3 + 1)
            cursor.execute(
                database.adapt("INSERT INTO transactions (id, customer_id, account_id, direction, amount_cents, merchant, description, category, occurred_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')"),
                (f"{target}-transaction-{index + 1:03d}", customer_id, account_id, direction, amount, merchant, description, category, occurred.isoformat()),
            )
    print(f"seeded {target}: {name} ({email})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("real", "honeypot", "all"), default="all")
    args = parser.parse_args()
    if args.target in ("real", "all"):
        seed_database(Database(settings.real_database_url, "real"), "real")
    if args.target in ("honeypot", "all"):
        seed_database(Database(settings.honeypot_database_url, "honeypot"), "honeypot")


if __name__ == "__main__":
    main()
