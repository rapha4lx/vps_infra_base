#!/bin/sh
set -eu

# ============================================
# Biblioteca comum para operações PostgreSQL
# ============================================

CONTAINER_NAME="${POSTGRES_CONTAINER:-nginx_postgres}"

if [ -z "${SCRIPT_DIR:-}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
ENV_FILE="$(cd "$SCRIPT_DIR/.." && pwd)/.env"
SUPERUSER="${POSTGRES_SUPERUSER:-$(grep '^POSTGRES_USER=' "$ENV_FILE" | head -n1 | cut -d'=' -f2- | sed -e 's/^"//' -e 's/"$//')}"

postgres_exec() {
  docker exec -i "$CONTAINER_NAME" psql -U "$SUPERUSER" -d postgres "$@"
}

db_exists() {
  docker exec -i "$CONTAINER_NAME" psql -U "$SUPERUSER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$1'" | grep -q "1"
}

user_exists() {
  docker exec -i "$CONTAINER_NAME" psql -U "$SUPERUSER" -d postgres -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='$1'" | grep -q "1"
}

create_user_if_needed() {
  _db_user="$1"
  _db_pass="$2"
  if ! user_exists "$_db_user"; then
    echo "🔑 Criando usuário $_db_user..."
    docker exec -i "$CONTAINER_NAME" psql -U "$SUPERUSER" -d postgres \
      -c "CREATE USER \"$_db_user\" WITH PASSWORD '$_db_pass';"
  else
    echo "ℹ️  Usuário $_db_user já existe."
  fi
}

create_db_if_needed() {
  _db_name="$1"
  _db_owner="$2"
  if ! db_exists "$_db_name"; then
    echo "📦 Criando database $_db_name..."
    docker exec -i "$CONTAINER_NAME" psql -U "$SUPERUSER" -d postgres \
      -c "CREATE DATABASE \"$_db_name\" OWNER \"$_db_owner\";"
  else
    echo "ℹ️  Database $_db_name já existe."
  fi
}

grant_db_privileges() {
  _db_name="$1"
  _db_user="$2"
  docker exec -i "$CONTAINER_NAME" psql -U "$SUPERUSER" -d postgres \
    -c "GRANT ALL PRIVILEGES ON DATABASE \"$_db_name\" TO \"$_db_user\";"
}

run_sql_files() {
  _db_name="$1"
  _project_dir="$2"
  _db_user="$3"

  if [ ! -d "$_project_dir" ]; then
    echo "❌ Diretório do projeto não encontrado: $_project_dir"
    return 1
  fi

  find "$_project_dir" -maxdepth 1 -name '*.sql' | sort | while IFS= read -r f; do
    echo "🗃️  Aplicando $(basename "$f")..."
    docker exec -i "$CONTAINER_NAME" psql -U "$_db_user" -d "$_db_name" <"$f"
    echo "✅ $(basename "$f") aplicado."
  done
}
