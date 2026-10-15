# VPS Control Plane — arquitetura proposta

## Contexto
A stack existente usa Docker Compose, Nginx, PostgreSQL e RabbitMQ. Manter a stack atual funcional durante a migração.

## Objetivo
Painel na porta 8083 para administração de usuários Linux, grupos, sessões, ambientes Podman rootless, instalações via catálogo e roteamento Traefik.

## Limites de confiança
- Backend nativo no host via systemd, usando conta de serviço dedicada sem privilégios gerais de root.
- Autenticação Linux via PAM; negar root e contas de sistema, rate limiting, cookies HttpOnly/Secure/SameSite, CSRF, timeout de sessão.
- Autorização por papéis: administrator, operator, viewer; o login válido não concede automaticamente administração.
- Helper privilegiado isolado, com operações tipadas de allowlist, validação estrita e registro de auditoria; sem executar comandos arbitrários recebidos da API.
- Terminal PTY opcional exige autorização explícita por identidade, nunca abre um shell root, limites de sessão e trilha de auditoria. Conexão via WebSocket autenticado e Origin validado.
- Nunca compartilhar /var/run/docker.sock, sockets Podman de outros usuários ou /etc/shadow com a aplicação web.
- Instalação de ferramentas apenas por catálogo versionado, com ações declarativas e aprovações administrativas.

## Rede
- Listener do aplicativo em 127.0.0.1:8083, acessível por SSH local port forwarding.
- Para acesso web remoto: Traefik com HTTPS, autenticação reforçada e ACL de origem; sem expor HTTP puro na porta 8083.
- Firewall: SSH 22/tcp e HTTPS 443/tcp, HTTP 80/tcp somente se necessário para ACME. Bloquear 5433/6380 externamente por padrão; manter endpoints internos para banco e filas.
- Traefik central recebe apenas endpoints de serviços publicados e aprovados, via file provider gerenciado por reconciliador; não conecta aos sockets de runtime de cada usuário.
- Para Podman rootless, expor aplicações autorizadas somente no endereço interno do host em portas atribuídas pelo gerenciador; configurar serviços systemd user/Quadlet e linger com política.

## Segurança SSH
- Antes de modificar sshd: testar chave SSH de administrador e garantir acesso alternativo pelo console do provedor.
- Usar /etc/ssh/sshd_config.d/60-vps-hardening.conf:
  PermitRootLogin no
  PasswordAuthentication no
  KbdInteractiveAuthentication no
  PubkeyAuthentication yes
- Validar sshd -t antes de reload e preservar rollback.
- Senhas Linux continuam possíveis no painel pelo PAM sobre HTTPS/túnel SSH, embora o acesso SSH por senha fique desligado.

## Entregas
1. API de leitura e RBAC: inventário de contas, grupos e sessões; auditoria e testes.
2. Operações administrativas: criação de contas e grupos, memberships, gerenciamento de sessões com helper allowlist.
3. Ambientes: Podman rootless, subuid/subgid, cgroups v2, Quadlet e limites de recursos por usuário.
4. Catálogo de ferramentas e instalador transacional: pacotes globais e por usuário.
5. Terminal web PTY com escopo, limites e auditoria.
6. Traefik central com rotas dinâmicas aprovadas, TLS, checagens e reconciliação.
7. Migração segura dos serviços Docker Compose legados.

## Critérios mínimos de aceite
- Login PAM apenas para contas autorizadas; conta root e contas de serviço rejeitadas.
- Usuário sem papel administrativo não pode criar usuários, alterar grupos, instalar ferramentas globais ou iniciar sessões de outros usuários.
- Sessões expiram e são revogáveis; proteção contra CSRF e ataques de tentativa de senha.
- Serviço web não consegue ler hashes em /etc/shadow nem acessar sockets de containers de terceiros.
- Isolamento de processos, volumes, rede e recursos demonstrado em testes para usuários distintos.
- Nenhuma alteração em SSH/firewall pode bloquear o acesso remoto administrativo existente.
- CI com testes de autorização, integração, segurança e rollback antes do deploy.
