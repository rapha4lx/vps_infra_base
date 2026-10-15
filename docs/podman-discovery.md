# Descoberta e reconciliação de containers externos

## Objetivo
Detectar containers Podman rootless criados tanto pelo painel como por SSH/terminal, identificar os que não têm boot automático e permitir integração segura ao gerenciamento central.

## Fontes de detecção
- Event watcher por usuário: `podman events --format json` (create, start, stop, remove, rename), executado como o próprio usuário; não compartilhar sockets de runtimes entre contas.
- Reconciliador executado no boot do daemon, em intervalos configuráveis e após perda/reconexão do watcher: `podman ps -a --format json` por usuário; consultar `podman inspect` somente para containers descobertos/relevantes.
- Descobrir Quadlets existentes de usuários sem sobrescrever os criados manualmente.
- Persistir cursor de eventos quando possível, fazer reconciliação completa ao reiniciar o observador e tolerar eventos duplicados.
- O Podman utiliza journald como mecanismo padrão de eventos; validar retenção e configuração em cada distribuição.

## Estados no painel
- `managed`: container criado pelo painel/Quadlet gerenciado;
- `external`: container externo detectado, sem política gerenciada;
- `boot_enabled`: Quadlet com instalação válida, serviço gerado e linger habilitado;
- `needs_attention`: configuração inconsistente, conflito, migração necessária;
- `ignored`: exclusão explícita por política do proprietário.

## Política de adoção
- O painel registra novos containers externos sem alterar sua execução.
- Containers novos criados no painel recebem Quadlet com boot automático por padrão.
- Para containers externos: oferecer `Adotar e habilitar boot`, com inspeção prévia de mounts, secrets, redes, labels, portas, comando, healthchecks, dependências, volumes e auto-restart.
- Adoção pode exigir substituição do container existente por um gerido via Quadlet, portanto exigir confirmação, plano de rollback e preservação dos dados. Não fazer conversão silenciosa/destrutiva.
- Não alterar containers de outros usuários, não oferecer adoção de containers privilegiados ou que dependam de configurações desconhecidas e não conflitar com systemd/Quadlets já gerenciados.
- Não confundir `--restart=always` isoladamente com garantia de inicialização no boot do host. O requisito de boot é atendido via systemd user + linger + Quadlet.

## Testes obrigatórios
- Detectar `podman run -d` por SSH sem uso do painel.
- Reconhecer dois usuários rootless isolados.
- Recuperar eventos perdidos com reconciliação após reinício.
- Não duplicar registros ao consumir novamente o mesmo evento.
- Mostrar containers existentes e não gerenciados, sem reiniciá-los automaticamente.
- Confirmar adoção de um workload compatível e reboot sem login.
- Recusar adoção de workload incompatível sem causar indisponibilidade.
