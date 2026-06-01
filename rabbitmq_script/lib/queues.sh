#!/bin/sh
set -eu

CONTAINER_NAME="${RABBITMQ_CONTAINER:-nginx_rabbitmq}"

# Verifica se rabbitmqadmin está disponível
rabbitmqadmin_exec() {
  if ! docker exec -i "$CONTAINER_NAME" which rabbitmqadmin > /dev/null 2>&1; then
    echo "❌ rabbitmqadmin não encontrado no container."
    echo "   Certifique-se de usar a imagem rabbitmq:3-management-alpine"
    exit 1
  fi
  docker exec -i "$CONTAINER_NAME" rabbitmqadmin "$@"
}

declare_queue() {
  _vhost="$1"
  _user="$2"
  _pass="$3"
  _name="$4"
  _durable="${5:-true}"
  _auto_delete="${6:-false}"
  
  echo "📦 Declarando fila $_name (vhost: $_vhost)..."
  rabbitmqadmin_exec declare queue name="$_name" vhost="$_vhost" durable="$_durable" auto_delete="$_auto_delete" \
    --username="$_user" --password="$_pass" 2>/dev/null || {
    echo "⚠️  Fila $_name já existe ou erro ao declarar."
  }
}

declare_exchange() {
  _vhost="$1"
  _user="$2"
  _pass="$3"
  _name="$4"
  _type="${5:-direct}"
  _durable="${6:-true}"
  
  echo "📡 Declarando exchange $_name (tipo: $_type, vhost: $_vhost)..."
  rabbitmqadmin_exec declare exchange name="$_name" vhost="$_vhost" type="$_type" durable="$_durable" \
    --username="$_user" --password="$_pass" 2>/dev/null || {
    echo "⚠️  Exchange $_name já existe ou erro ao declarar."
  }
}

bind_queue() {
  _vhost="$1"
  _user="$2"
  _pass="$3"
  _queue="$4"
  _exchange="$5"
  _routing_key="${6:-}"
  
  echo "🔗 Bindando fila $_queue -> exchange $_exchange (routing_key: $_routing_key)..."
  rabbitmqadmin_exec declare binding vhost="$_vhost" source="$_exchange" destination="$_queue" routing_key="$_routing_key" \
    --username="$_user" --password="$_pass" 2>/dev/null || {
    echo "⚠️  Binding já existe ou erro ao criar."
  }
}
