# Publicação multiusuário via Traefik central

## Configuração real inspecionada (rapha4lx/traefik, main, 2026-10-14)
- Traefik v3.7 executa com Docker Compose, usa Docker provider (/var/run/docker.sock:ro) e file provider com arquivo único `/etc/traefik/omnidev.yml`.
- EntryPoints: web 80, websecure 443, api 8080 (host 127.0.0.1 somente), wsproxy 8443 (público), postgres 5433, amqps 5672, redis 6380.
- HTTP ACME challenge usa web:80. Traefik encontra Docker containers na rede externa `traefik_proxy`.
- **Importante:** porta 8080 não é proxy HTTP público; 443 é HTTPS público e 80 é challenge/redirect; não reaproveitar 8080 para o painel (painel: 127.0.0.1:8083).

## Resolução técnica
O Docker provider central não descobre automaticamente múltiplos namespaces Podman rootless. **Não** expor sockets Podman dos usuários, não montar sockets no Traefik e não adicionar containers de usuários ao daemon Docker privilegiado.

Criar `route-reconciler` no plano de controle:
1. Inventariar containers Podman por usuário, com watchers + varredura periódica (agente read-only).
2. Ler labels `traefik.enable`, `traefik.http.routers.*.rule`, `entrypoints`, `tls.certresolver`, `traefik.http.services.*.loadbalancer.server.port`. Tratar todas as labels como entrada NÃO confiável.
3. Validar regras estritas: Host() literal único, domínio permitido/controlado; entrypoint websecure; resolver letsencrypt; porta de container 1..65535; nenhum service de outro usuário; identidade e propriedade do container verificadas. Rejeitar PathPrefix arbitrário, middlewares não aprovados, serviços @internal, URLs externas e sintaxe de roteador não permitida.
4. Reservar nomes gerados `u<uid>-<containerid>-<router>` e nomes DNS de forma transacional; conflito de domínio é erro. Nunca confiar na label `traefik.docker.network` em rootless: remover/ignorar após validação.
5. Atribuir endpoint de host acessível **somente pelo container Traefik** para uma porta interna do workload (mesmo que o Podman publique no host). A porta pode precisar ser publicada em endereço **não-loopback** de interface dedicada, pois 127.0.0.1 do host não é acessível diretamente a partir do container Traefik na rede bridge. Como alternativa, implementar gateway/reverse-proxy interno dedicado para alcançar workloads no namespace do usuário. **Não usar host.docker.internal sem assegurar host-gateway e ACL**.
6. Firewall (nftables) permite ingress apenas da origem Traefik para os backends; bloquear acesso público e lateral. Atenção à ordem de regras e DOCKER-USER/nftables conforme distro para que Docker não contorne isolamento. Não presumir que bind a endereço de interface Docker seja privado por si só.
7. Gerar fragmentos YAML de File Provider somente para serviços aprovados, gravar via escrita atômica em diretório montado como somente leitura no Traefik, auditar aprovações, remoções, mudanças de domínio/porta e rollback.
8. No reboot: systemd user+linger+Quadlet reiniciam os workloads, reconciliador revalida endpoints e mantém/publica apenas rotas para aplicações autorizadas.

## Adaptação futura do repositório traefik
A configuração atual usa `providers.file.filename` e volume do `omnidev.yml`. Para aceitar fragmentos do gerenciador:
- trocar para `providers.file.directory: /etc/traefik/dynamic`, mantendo `watch: true`;
- montar `./omnidev.yml:/etc/traefik/dynamic/omnidev.yml:ro` para preservar regras existentes;
- montar diretório seguro de fragmentos `/var/lib/vps-panel/traefik-routes:/etc/traefik/dynamic/vps-panel:ro` ou diretório de fragmentos dentro do diretório dynamic, testando comportamento de watch de arquivos e subdiretórios;
- manter `providers.docker.exposedbydefault=false` para serviços legados;
- validar configurações e rotas/ACME existentes antes de reiniciar; aplicar por PR separado no repositório traefik.

## Exemplo de intenção declarada pelo usuário (Podman Compose)
```yaml
services:
  api:
    image: docker.io/library/nginx:alpine
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(\`api.example.com\`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.services.api.loadbalancer.server.port=80"
```
Não especificar `ports:` por padrão. **Limitação**: sem host networking ou rede compartilhada entre runtimes, Traefik Docker não alcança diretamente a porta interna rootless. O reconciliador/gateway precisará criar conexão aprovada e isolada antes de ativar a rota. Labels por si sós não tornam o serviço alcançável.

## Critérios de aceite
- Serviço A e B de usuários rootless distintos resolvem via HTTPS 443 por Traefik com domínios diferentes e ACME válido.
- Nenhuma porta de app exposta publicamente, nenhum socket Podman entregue ao Traefik.
- Domínio duplicado, labels maliciosas e mudança de ownership bloqueados.
- Reboot sem login de usuário restaura os containers e suas rotas.
- Preservados Docker provider, dashboard protegido, omnidev.yml e wsproxy existentes.
- Cortar acesso direto à porta de backend de fontes fora do container Traefik, inclusive outros containers/usuários.
