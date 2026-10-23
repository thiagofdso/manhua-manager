# Manhua Manager - Diretrizes e Padrões de Projeto

## 1. Comandos Operacionais e Ambiente
- **Ambiente Python:** Utilize sempre o ambiente virtual local em `./.venv/bin/python` e `./.venv/bin/pytest`. Não utilize o python global do sistema para testes.
- **Testes Backend:** `./.venv/bin/pytest tests/`
- **Testes Mobile (Flutter):** `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
- **Serviço do Sistema:** Gerenciado via systemd de usuário (não use `sudo`):
  `systemctl --user restart manhua-manager.service`
  `systemctl --user status manhua-manager.service --no-pager`

## 2. Padrões de URLs e Capítulos
- Todo template de obra no banco (`database.json`) e na API deve preservar o placeholder `{chapter}`.
- Ao converter URLs contendo números de capítulo (ex: `chapter-170`, `chapter/224`), a substituição deve manter o prefixo intacto (ex: `chapter-{chapter}` ou `/chapter/{chapter}`).
- Ao adicionar novas plataformas, mantenha compatibilidade com os provedores existentes (`asurascans`, `manhuatop`, `ravenscans`, `mangafire`, `comix`, `manhuaus`).

## 3. Proxy de Imagens
- Imagens que exigem cabeçalhos de origem ou cookies de proteção devem ser tratadas em `/api/proxy-image`:
  - `mangak.io` / `qvzr*.org`: Injetar `Referer: https://mangak.io/`.
  - `manhuaus.com` / `img.manhuaus.com`: Injetar `Referer: https://manhuaus.com/`, `Cookie: cf_clearance=...` e User-Agent compatível.
  - `asurascans.com` / `ravenscans.org` / `mangafire.to`: Injetar seus respectivos `Referer`.
