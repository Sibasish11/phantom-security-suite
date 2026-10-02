#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Tests use throwaway DATABASES, never the running demo databases. No live
# volumes or schemas are deleted. Test DB names are deliberately explicit.
QA_SUFFIX="$(date +%s)_$$"
for pair in "postgres-real phantomlayer_qa_real_${QA_SUFFIX}" "postgres-honeypot phantomlayer_qa_honeypot_${QA_SUFFIX}" "postgres-control phantomlayer_qa_control_${QA_SUFFIX}"; do
  read -r service database <<< "$pair"
  docker compose exec -T "$service" sh -eu -c '
    if ! psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '\''$1'\''" | grep -q 1; then
      createdb -U "$POSTGRES_USER" "$1"
    fi
  ' sh "$database"
done

# Bind the current source tree into a short-lived test runner, leaving the
# running application and database volumes untouched.
docker compose run --rm --no-deps \
  -v "$PWD/backend:/app" \
  -e PHANTOMLAYER_TEST_DATABASES=1 \
  -e PHANTOMLAYER_QA_DATABASE_SUFFIX="${QA_SUFFIX}" \
  -e DEBUG=false \
  -e DEMO_MODE=true \
  backend python -m tests.qa_runner "$@"
