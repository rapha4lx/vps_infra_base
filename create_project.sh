#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
  echo "Uso: $0 <projeto>"
  echo ""
  echo "Cria usuários isolados para o projeto no RabbitMQ, Postgres e Redis."
  echo "Gera uma senha nova (32+ caracteres) para cada serviço em que o"
  echo "usuário ainda não existir e imprime as credenciais no terminal."
  exit 1
}

[ $# -eq 1 ] || usage
PROJECT="$1"

echo "=== Provisionando projeto '$PROJECT' ==="

echo ""
echo "--- RabbitMQ ---"
"$SCRIPT_DIR/rabbitmq_script/create_user.sh" "$PROJECT"

echo ""
echo "--- PostgreSQL ---"
"$SCRIPT_DIR/sql_script/create_user.sh" "$PROJECT"

echo ""
echo "--- Redis ---"
"$SCRIPT_DIR/redis_script/create_user.sh" "$PROJECT"

echo ""
echo "=== Concluído: '$PROJECT' ==="
