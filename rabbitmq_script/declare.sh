#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTS_DIR="$SCRIPT_DIR/projects"

. "$SCRIPT_DIR/lib/common.sh"
. "$SCRIPT_DIR/lib/queues.sh"

usage() {
  echo "Uso: $0 <projeto>"
  echo ""
  echo "Declara filas, exchanges e bindings definidos em queues.conf"
  echo ""
  echo "Exemplo:"
  echo "  $0 service_flow"
  exit 1
}

if [ $# -eq 0 ]; then
  usage
fi

_project="$1"
_project_dir="$PROJECTS_DIR/$_project"

if [ ! -d "$_project_dir" ]; then
  echo "❌ Projeto '$_project' não encontrado em $_project_dir"
  exit 1
fi

if [ ! -f "$_project_dir/config.env" ]; then
  echo "❌ Configuração não encontrada: $_project_dir/config.env"
  exit 1
fi

# Carrega config.env
while IFS='=' read -r key value; do
  case "$key" in
    \#*|""|*\#*) continue ;;
  esac
  value=$(printf '%s' "$value" | sed -e 's/^"//' -e 's/"$//')
  export "$key=$value"
done < "$_project_dir/config.env"

: "${RABBITMQ_USER:?RABBITMQ_USER não definido em config.env}"
: "${RABBITMQ_PASS:?RABBITMQ_PASS não definido em config.env}"
: "${RABBITMQ_VHOST:?RABBITMQ_VHOST não definido em config.env}"

QUEUES_CONF="$_project_dir/queues.conf"

if [ ! -f "$QUEUES_CONF" ]; then
  echo "ℹ️  Arquivo $QUEUES_CONF não encontrado. Nenhuma fila para declarar."
  exit 0
fi

echo "🚀 Declarando recursos do RabbitMQ para '$_project'..."

# Lê o arquivo de configuração de filas
while IFS= read -r line || [ -n "$line" ]; do
  # Remove comentários e espaços
  line=$(echo "$line" | sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  [ -z "$line" ] && continue

  # Formato: ACTION|ARGS
  # Exemplos:
  #   queue|nome|durable|auto_delete
  #   exchange|nome|tipo|durable
  #   bind|fila|exchange|routing_key
  
  _action=$(echo "$line" | cut -d'|' -f1)
  
  case "$_action" in
    queue)
      _name=$(echo "$line" | cut -d'|' -f2)
      _durable=$(echo "$line" | cut -d'|' -f3)
      _auto_delete=$(echo "$line" | cut -d'|' -f4)
      declare_queue "$RABBITMQ_VHOST" "$RABBITMQ_USER" "$RABBITMQ_PASS" \
        "$_name" "${_durable:-true}" "${_auto_delete:-false}"
      ;;
    exchange)
      _name=$(echo "$line" | cut -d'|' -f2)
      _type=$(echo "$line" | cut -d'|' -f3)
      _durable=$(echo "$line" | cut -d'|' -f4)
      declare_exchange "$RABBITMQ_VHOST" "$RABBITMQ_USER" "$RABBITMQ_PASS" \
        "$_name" "${_type:-direct}" "${_durable:-true}"
      ;;
    bind)
      _queue=$(echo "$line" | cut -d'|' -f2)
      _exchange=$(echo "$line" | cut -d'|' -f3)
      _routing_key=$(echo "$line" | cut -d'|' -f4)
      bind_queue "$RABBITMQ_VHOST" "$RABBITMQ_USER" "$RABBITMQ_PASS" \
        "$_queue" "$_exchange" "$_routing_key"
      ;;
    *)
      echo "⚠️  Ação desconhecida: $_action"
      ;;
  esac
done < "$QUEUES_CONF"

echo "✅ Recursos declarados para '$_project'!"
