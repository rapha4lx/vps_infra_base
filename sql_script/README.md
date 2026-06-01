# SQL Scripts & Migrations

Estrutura organizada para inicialização e migrations de bancos PostgreSQL por projeto.

## Estrutura

```
sql_script/
  migrate.sh              # Script principal
  lib/
    common.sh             # Funções utilitárias
  projects/
    service_flow/         # Cada projeto tem sua pasta
      config.env          # Credenciais e nome do banco
      001_schema.sql      # Schema (executado em ordem alfabética)
      002_seed.sql        # Dados iniciais (opcional)
```

## Uso

```bash
# Listar projetos disponíveis
./migrate.sh list

# Rodar migrations de um projeto específico
./migrate.sh service_flow

# Rodar migrations de todos os projetos
./migrate.sh all
```

## Adicionar um novo projeto

1. Crie uma pasta em `projects/<nome_do_projeto>/`
2. Adicione `config.env` com:
   - `DB_NAME`: nome do banco
   - `DB_USER`: usuário da aplicação
   - `DB_PASS`: senha do usuário
3. Adicione arquivos `.sql` numerados (ex: `001_schema.sql`, `002_seed.sql`)
4. Execute: `./migrate.sh <nome_do_projeto>`

## Requisitos

- Docker Compose rodando com o serviço `postgres` (`nginx_postgres`)
- Variável de ambiente `POSTGRES_CONTAINER` pode ser usada para apontar outro container
- Variável de ambiente `POSTGRES_SUPERUSER` pode ser usada para trocar o superuser (padrão: `postgres`)

## Script legado

O arquivo `create_user_db.sh` continua disponível para uso interativo manual.
