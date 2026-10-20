# Design Specification: Native Webtoon Continuous Image Reader & Image Proxy

## 1. Overview
Esta especificação define a substituição do leitor baseado em iframe por um **Leitor Nativo Contínuo de Webtoon/Manhua**. O backend Python extrai automaticamente as URLs de todas as páginas do capítulo a partir do HTML da fonte e disponibiliza um proxy de imagens para contornar proteções de *Hotlink* (`Referer`). O frontend exibe as imagens em cascata vertical sem anúncios, sem menus poluídos e sem restrições de `X-Frame-Options`.

## 2. Architecture & Endpoints

### 2.1 Backend Endpoints (`server.py`)
1. **`GET /api/chapter-images?url=<target_chapter_url>`:**
   - Realiza requisição GET com `User-Agent` de navegador para o URL do capítulo.
   - Extrai as URLs das imagens que possuem classe `wp-manga-chapter-img` (ignorando logos ou banners promocionais como `about_manhuatop`).
   - Retorna payload JSON:
     ```json
     {
       "status": "ok",
       "count": 10,
       "images": [
         "https://s2.manhuatop.org/.../ch_197_1.jpg",
         "https://s2.manhuatop.org/.../ch_197_2.jpg"
       ]
     }
     ```
2. **`GET /api/proxy-image?url=<encoded_image_url>`:**
   - Faz a requisição da imagem enviando os cabeçalhos:
     - `User-Agent: Mozilla/5.0`
     - `Referer: https://manhuatop.org/`
   - Retorna os bytes binários com `Content-Type: image/jpeg` (ou tipo correspondente) e cabeçalhos de cache HTTP (`Cache-Control: public, max-age=86400`).

### 2.2 Frontend Native Reader (`index.html`)
1. **Estrutura do Leitor:**
   - Substituição do `<iframe>` por uma área de rolagem vertical contínua `#readerImagesContainer`.
   - As imagens são renderizadas com `src="/api/proxy-image?url=" + encodeURIComponent(img)` e `loading="lazy"`.
   - Layout responsivo adaptado para celular e desktop: largura máxima de `800px`, centralizado, sem margens ou espaços indesejados entre as páginas.
2. **Estados da Interface:**
   - Estado de carregamento com feedback visual enquanto as imagens são requisitadas.
   - Tratamento de erro com mensagem legível e botão alternativo de abertura no navegador.
3. **Barra de Ferramentas:**
   - Botão `← Voltar`.
   - Título da obra e capítulo atual.
   - Botões `◀` e `▶` para trocar de capítulo (persiste novo capítulo no backend, busca as novas páginas e rola para o topo).
   - Botão `↗` para abrir o site original externamente.

## 3. Verification Plan
- **Testes de Backend:** Testar endpoints `/api/chapter-images` e `/api/proxy-image` com `pytest` (mockando requisições externas para garantir testes rápidos e determinísticos).
- **Testes de Frontend:** Validar presença de `#readerImagesContainer` e ausência de bloqueios por iframe.
- **Teste de Integração Real:** Consultar `http://localhost:5000/api/chapter-images?url=https://manhuatop.org/manhua/overgeared-org/chapter-197/` e validar retorno com 10 páginas.
