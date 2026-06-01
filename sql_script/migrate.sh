#!/bin/sh
set -eu

# ============================================
# Script de migrations multi-projeto
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTS_DIR="$SCRIPT_DIR/projects"
export SCRIPT_DIR

. "$SCRIPT_DIR/lib/common.sh"

usage() {
  echo "Uso: $0 [projeto | all | list]"
  echo ""
  echo "Comandos:"
  echo "  list        Lista projetos disponíveis"
  echo "  <projeto>   Executa migrations de um projeto específico"
  echo "  all         Executa migrations de todos os projetos"
  echo ""
  echo "Exemplos:"
  echo "  $0 list"
  echo "  $0 service_flow"
  echo "  $0 all"
  exit 1
}

list_projects() {
  if [ ! -d "$PROJECTS_DIR" ]; then
    echo "Nenhum projeto encontrado em $PROJECTS_DIR"
    exit 0
  fi

  echo "Projetos disponíveis:"
  for d in "$PROJECTS_DIR"/*; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    if [ -f "$d/config.env" ]; then
      echo "  - $name"
    else
      echo "  - $name (⚠️  sem config.env)"
    fi
  done
}

run_project() {
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

  # Carrega config.env (ignora comentários e linhas vazias)
  while IFS='=' read -r key value; do
    case "$key" in
      \#*|""|*\#*) continue ;;
    esac
    # Remove aspas opcionais
    value=$(printf '%s' "$value" | sed -e 's/^"//' -e 's/"$//')
    export "$key=$value"
  done < "$_project_dir/config.env"

  : "${DB_NAME:?DB_NAME não definido em config.env}"
  : "${DB_USER:?DB_USER não definido em config.env}"
  : "${DB_PASS:?DB_PASS não definido em config.env}"

  echo "🚀 Executando migrations para '$_project'..."
  echo "   Banco: $DB_NAME"
  echo "   Usuário: $DB_USER"

  create_user_if_needed "$DB_USER" "$DB_PASS"
  create_db_if_needed "$DB_NAME" "$DB_USER"
  grant_db_privileges "$DB_NAME" "$DB_USER"

  run_sql_files "$DB_NAME" "$_project_dir" "$DB_USER"

  echo "✅ Migrations de '$_project' concluídas!"
}

# ===== MAIN =====

if [ $# -eq 0 ]; then
  usage
fi

CMD="$1"

case "$CMD" in
  list)
    list_projects
    ;;
  all)
    for d in "$PROJECTS_DIR"/*; do
      [ -d "$d" ] || continue
      name=$(basename "$d")
      run_project "$name"
    done
    ;;
  *)
    run_project "$CMD"
    ;;
esac
