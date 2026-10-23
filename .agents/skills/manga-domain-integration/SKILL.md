---
name: manga-domain-integration
description: >-
  Use esta habilidade quando o usuário solicitar a adição, análise ou suporte
  a um novo domínio ou fonte de leitura de mangá/manhua no manhua-manager.
---

# Manga Domain Integration Runbook

Procedimento padrão para engenharia reversa e integração de novos domínios no `manhua-manager`.

## Etapa 1: Triagem de Proteção e Acesso HTTP
1. Teste a URL do capítulo com curl simples:
   ```bash
   curl -sI -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "<URL>"
   ```
2. **Se 200 OK:**
   - O domínio não utiliza desafio interativo Cloudflare Turnstile. Siga para a **Etapa 2 (Inspeção SSR/DOM)**.
3. **Se 403 Forbidden / `cf-mitigated: challenge`:**
   - O site utiliza Cloudflare Turnstile. Siga para a **Etapa 3 (Headless Browser com Brave/Xvfb)**.

## Etapa 2: Extração em Domínios HTTP Diretos
1. Baixe o HTML e verifique fontes estruturadas de dados antes de fazer parsing complexo:
   - **Next.js:** Inspecione `<script id="__NEXT_DATA__" type="application/json">` (ex: `mangak.io`).
   - **WordPress + Lazy Load:** Inspecione atributos `data-src` vs `lazy_placeholder.gif` (ex: `levelingwithgods.com`, `pickmeupgacha.com`).
   - **Contêineres de Leitor:** Identifique divs específicas como `#chapter-reader`, `.entry-content`, `.reading-content`.
2. Teste o download de 1 imagem via curl com e sem `Referer`:
   - Se retornar 403 sem `Referer`, adicione o domínio em `/api/proxy-image` no `server.py` com o referer obrigatório.
3. Extraia os links de navegação (`nextChapter` / `prevChapter`) via HTML ou JSON.

## Etapa 3: Extração em Domínios Protegidos por Cloudflare Turnstile
1. Utilize o pipeline headless com Brave + Puppeteer executado sob Xvfb:
   - Caminho do binário: `/usr/bin/brave-browser`
   - Perfil persistente: `.cache/brave_profile` (para reuso de tokens `cf_clearance`).
   - Argumentos obrigatórios: `--no-sandbox`, `--disable-setuid-sandbox`, `--disable-blink-features=AutomationControlled`.
2. Detecção e clique no Turnstile:
   - Monitore frames de desafio (`cloudflare` / `challenges`) e efetue o clique na caixa de seleção.
   - Aguarde a transição de título para sair de "Just a moment..." / "Um momento…".
3. Salve o cookie `cf_clearance` em cache para repassar nas requisições do `/api/proxy-image`.
4. Crie o par `<dominio>_extractor.mjs` e `<dominio>_provider.py` seguindo o modelo de `manhuaus_provider.py` ou `comix_provider.py`.

## Etapa 4: Integração no Backend e Testes
1. Conecte o extrator em `extract_chapter_images_by_domain` em `server.py`.
2. Adicione navegação em `extract_html_navigation` ou no provider correspondente.
3. Adicione testes unitários em `tests/test_server.py`.
4. Execute os testes:
   ```bash
   ./.venv/bin/pytest tests/
   cd mobile_app && flutter test
   ```
5. Reinicie o serviço:
   ```bash
   systemctl --user restart manhua-manager.service
   ```
