CREATE TABLE IF NOT EXISTS bank_customers (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    customer_marker TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES bank_customers(id),
    account_type TEXT NOT NULL,
    account_number TEXT NOT NULL UNIQUE,
    balance_cents INTEGER NOT NULL DEFAULT 0,
    available_cents INTEGER NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'GBP',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id);

CREATE TABLE IF NOT EXISTS beneficiaries (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES bank_customers(id),
    name TEXT NOT NULL,
    account_hint TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_customer ON beneficiaries(customer_id);

CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES bank_customers(id),
    card_name TEXT NOT NULL,
    card_number_masked TEXT NOT NULL,
    card_type TEXT NOT NULL,
    status TEXT NOT NULL,
    expires_on TEXT NOT NULL,
    spending_limit_cents INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cards_customer ON cards(customer_id);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES bank_customers(id),
    account_id TEXT NOT NULL REFERENCES accounts(id),
    direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
    merchant TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    transfer_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_transactions_customer_date ON transactions(customer_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS transfers (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES bank_customers(id),
    source_account_id TEXT NOT NULL REFERENCES accounts(id),
    beneficiary_id TEXT NOT NULL REFERENCES beneficiaries(id),
    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
    reference TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(customer_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS gateway_audit (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    destination TEXT NOT NULL CHECK(destination IN ('real', 'honeypot')),
    success INTEGER NOT NULL,
    response_count INTEGER NOT NULL DEFAULT 0,
    entity_type TEXT,
    entity_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gateway_audit_created ON gateway_audit(created_at DESC);
