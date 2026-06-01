# RabbitMQ Scripts

Gerenciamento de usuários, vhosts e permissões do RabbitMQ por projeto.

## Estrutura

```
rabbitmq_script/
  setup.sh              # Script principal
  lib/
    common.sh             # Funções utilitárias
  projects/
    service_flow/         # Cada projeto tem sua pasta
      config.env          # Credenciais e configurações do RabbitMQ
```

## Uso

### Gerenciar usuários e vhosts

```bash
# Listar projetos disponíveis
./setup.sh list

# Configurar um projeto específico (cria usuário, vhost e permissões)
./setup.sh service_flow

# Configurar todos os projetos
./setup.sh all

# Remover configuração de um projeto (deleta usuário e vhost)
./setup.sh delete service_flow
```

### Declarar filas, exchanges e bindings

```bash
# Declarar recursos (filas, exchanges, bindings) de um projeto
./declare.sh service_flow
```

## Configuração por projeto (config.env)

```env
RABBITMQ_USER=service_flow_user
RABBITMQ_PASS=senha_segura
RABBITMQ_TAGS=management
RABBITMQ_VHOST=/service_flow
RABBITMQ_PERM_CONFIGURE=.*
RABBITMQ_PERM_READ=.*
RABBITMQ_PERM_WRITE=.*
```

| Variável | Descrição | Padrão |
|---|---|---|
| `RABBITMQ_USER` | Nome do usuário da aplicação | obrigatório |
| `RABBITMQ_PASS` | Senha do usuário | obrigatório |
| `RABBITMQ_TAGS` | Tags do usuário | `management` |
| `RABBITMQ_VHOST` | Virtual host dedicado | obrigatório |
| `RABBITMQ_PERM_CONFIGURE` | Permissão de configuração | `.*` |
| `RABBITMQ_PERM_READ` | Permissão de leitura | `.*` |
| `RABBITMQ_PERM_WRITE` | Permissão de escrita | `.*` |

## Tags de usuário

- `administrator` - Acesso total
- `management` - Acesso ao Management UI e API
- `monitoring` - Apenas leitura de estatísticas
- `none` - Sem acesso administrativo

## Configuração de filas (queues.conf)

Crie um arquivo `queues.conf` no diretório do projeto para declarar filas, exchanges e bindings:

```conf
# Filas
queue|tickets.created|true|false
queue|notifications.email|true|false

# Exchanges
exchange|tickets.topic|topic|true
exchange|notifications.direct|direct|true

# Bindings
bind|tickets.created|tickets.topic|ticket.created
bind|notifications.email|notifications.direct|email
```

Formato: `ACTION|arg1|arg2|...`

| Ação | Argumentos | Descrição |
|---|---|---|
| `queue` | `nome\|durable\|auto_delete` | Declara uma fila |
| `exchange` | `nome\|tipo\|durable` | Declara um exchange (tipos: direct, topic, fanout, headers) |
| `bind` | `fila\|exchange\|routing_key` | Cria binding entre fila e exchange |

## Permissões

As permissões são regexes que definem quais recursos o usuário pode acessar no vhost:
- `.*` - Acesso a tudo
- `^queue_name$` - Acesso apenas a uma fila específica
- `^(queue1\|queue2)$` - Acesso a filas específicas

## Requisitos

- Docker Compose rodando com o serviço `rabbitmq` (`nginx_rabbitmq`)
- O container deve estar com o plugin `rabbitmq_management` ativo (padrão na imagem `management`)

## Script legado

O arquivo `create_user_db.sh` na pasta `sql_script/` continua disponível para uso manual do PostgreSQL.

## Fluxo completo

```bash
# 1. Subir o RabbitMQ
cd /path/to/datashaper_infra
docker compose up -d rabbitmq

# 2. Criar usuário, vhost e permissões
./rabbitmq_script/setup.sh service_flow

# 3. Declarar filas, exchanges e bindings
./rabbitmq_script/declare.sh service_flow
```

## Dicas

### Criar uma fila via CLI
```bash
docker exec nginx_rabbitmq rabbitmqadmin declare queue name=my_queue durable=true -V /service_flow -u service_flow_user -p senha
```

### Listar filas de um vhost
```bash
docker exec nginx_rabbitmq rabbitmqctl list_queues -p /service_flow
```

### Enviar uma mensagem de teste
```bash
docker exec nginx_rabbitmq rabbitmqadmin publish exchange=amq.default routing_key=my_queue payload='{"test":true}' -V /service_flow -u service_flow_user -p senha
```
