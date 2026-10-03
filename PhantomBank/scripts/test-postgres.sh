#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Only create new QA databases. No existing databases or volumes are deleted.
suffix="$(date +%s)_$$"
created=()
cleanup() {
  for target in "${created[@]}"; do
    docker compose exec -T "bank-postgres-$target" sh -eu -c '
      for candidate in "${BANK_QA_ADMIN_USER:-$POSTGRES_USER}" phantomlayer postgres; do
        if [ "$(psql -U "$candidate" -d postgres -Atqc "SELECT rolcreatedb FROM pg_roles WHERE rolname = current_user" 2>/dev/null || true)" = "t" ]; then
          dropdb --if-exists -U "$candidate" "$1"
          exit
        fi
      done
      exit 1
    ' sh "phantombank_qa_${target}_${suffix}"
  done
}
trap cleanup EXIT
echo "Disposable PhantomBank QA database suffix: $suffix (removed on exit)"
for target in real honeypot; do
  docker compose exec -T "bank-postgres-$target" sh -eu -s -- "phantombank_qa_${target}_${suffix}" <<'SCRIPT'
database="$1"

# The bank login is deliberately not a cluster administrator. Fresh local
# clusters initialize POSTGRES_USER as an administrator, while the preserved
# presentation clusters retain their original phantomlayer administrator.
admin_user="${BANK_QA_ADMIN_USER:-}"
if [ -z "$admin_user" ]; then
  for candidate in "$POSTGRES_USER" phantomlayer postgres; do
    if [ "$(psql -U "$candidate" -d postgres -Atqc "SELECT rolcreatedb FROM pg_roles WHERE rolname = current_user" 2>/dev/null || true)" = "t" ]; then
      admin_user="$candidate"
      break
    fi
  done
fi
[ -n "$admin_user" ] || { echo "No local PostgreSQL administration role available for QA database creation" >&2; exit 1; }

createdb -U "$admin_user" "$database"
psql -v ON_ERROR_STOP=1 -U "$admin_user" -d postgres -c "GRANT CONNECT ON DATABASE \"$database\" TO \"$POSTGRES_USER\";"
psql -v ON_ERROR_STOP=1 -U "$admin_user" -d "$database" -c "GRANT USAGE, CREATE ON SCHEMA public TO \"$POSTGRES_USER\";"
SCRIPT
  created+=("$target")
done
docker compose run --rm --no-deps -v "$PWD/backend:/app" -e BANK_QA_SUFFIX="$suffix" bank-api python -c '
import os, pytest
suffix=os.environ["BANK_QA_SUFFIX"]
for target in ("REAL", "HONEYPOT"):
    original=os.environ[target+"_DATABASE_URL"]
    os.environ["BANK_"+target+"_POSTGRES_TEST_URL"]=original.rsplit("/",1)[0]+"/phantombank_qa_"+target.lower()+"_"+suffix
raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider"]))
'
