#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export SCRIPT_DIR

. "$ROOT_DIR/lib/password.sh"
. "$SCRIPT_DIR/lib/common.sh"

usage() {
  echo "Uso: $0 <projeto>"
  echo ""
  echo "Cria (se não existir) usuário e database isolados para o projeto no Postgres."
  echo "Se o usuário já existir, nenhuma senha nova é gerada."
  exit 1
}

[ $# -eq 1 ] || usage
PROJECT="$1"

DB_USER="$PROJECT"
DB_NAME="$PROJECT"

if user_exists "$DB_USER"; then
  echo "ℹ️  Usuário '$DB_USER' já existe. Nenhuma senha nova gerada."
  create_db_if_needed "$DB_NAME" "$DB_USER"
  grant_db_privileges "$DB_NAME" "$DB_USER"
  exit 0
fi

DB_PASS="$(generate_password 32)"

create_user_if_needed "$DB_USER" "$DB_PASS"
create_db_if_needed "$DB_NAME" "$DB_USER"
grant_db_privileges "$DB_NAME" "$DB_USER"

echo "✅ Postgres pronto para '$PROJECT'"
echo "  user: $DB_USER"
echo "  db:   $DB_NAME"
echo "  pass: $DB_PASS"
