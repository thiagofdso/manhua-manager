# Especificação de Design: Suporte Multi-Domínio (Asura Scans e ManhuaTop)

**Data:** 19/10/2026  
**Status:** Aprovado  
**Branch Alvo:** `feature/asurascans-support`  

## 1. Visão Geral e Objetivos

O leitor contínuo do Manhua Manager anteriormente possuía suporte fixo de scraping apenas para o portal `manhuatop.org`. O objetivo deste incremento é:
1. Adicionar suporte à extração de páginas do site `asurascans.com` (especificamente páginas no formato Astro / CDN `asurascans.com`).
2. Implementar uma arquitetura de extração extensível baseada no domínio da URL informada (`Domain Dispatcher`).
3. Manter 100% de compatibilidade com o formato existente de extração para `manhuatop.org`.
4. Atualizar o cadastro padrão de "Overgeared" em `database.json` para utilizar a URL do Asura Scans com o template `{chapter}` e capítulo inicial `197`.
5. Ajustar o proxy `/api/proxy-image` para utilizar o cabeçalho `Referer` apropriado e evitar bloqueio por hotlinking.

---

## 2. Arquitetura e Componentes

### 2.1 Despachante de Domínios (`Domain Dispatcher`)

No backend Python (`server.py`):
- Ao receber a chamada GET em `/api/chapter-images?url=<target_url>`, o backend faz o download do HTML com headers simulando navegador comum.
- O domínio é extraído usando:
  ```python
  parsed = urllib.parse.urlparse(target_url)
  domain = parsed.netloc.lower()
  if domain.startswith("www."):
      domain = domain[4:]
  ```
- O domínio é roteado para a função especializada correspondente através de um dicionário:
  ```python
  DOMAIN_EXTRACTORS = {
      "asurascans.com": extract_asurascans_images,
      "manhuatop.org": extract_manhuatop_images,
  }
  ```
- Se o domínio não estiver registrado, um fallback genérico tenta os extratores disponíveis.

### 2.2 Extrator para `manhuatop.org` (`extract_manhuatop_images`)

- Mantém a lógica existente:
  - Regex para `<img ... class="...wp-manga-chapter-img..." ... src="..." ...>`.
  - Filtra URLs que contenham `about_manhuatop`.
  - Remove duplicatas mantendo a ordem de leitura.

### 2.3 Extrator para `asurascans.com` (`extract_asurascans_images`)

- Asura Scans utiliza Astro SSR com hidratação via `<astro-island>`.
- As URLs das páginas dos capítulos residem sob o padrão CDN:
  `https://cdn.asurascans.com/asura-images/chapters-merged/<series>/<chapter_id>/<page>.webp?v=...`
- Estratégia de extração:
  1. Busca por tags `<img>` e referências de imagem que correspondam ao padrão `https://cdn\.asurascans\.com/asura-images/chapters-merged/[^\s"\'<>&]+(?:\?[^\s"\'<>&]*)?`.
  2. Filtro estrito para excluir capas (`/covers/`), logotipos e avatares.
  3. Deduplicação preservando a ordem natural do leitor (`dict.fromkeys(...)`).

### 2.4 Proxy de Imagem (`/api/proxy-image`)

- Extrai o domínio da imagem requisitada.
- Se a imagem for do CDN do Asura Scans (`cdn.asurascans.com`), define o cabeçalho `Referer: https://asurascans.com/`.
- Se for de outro domínio, utiliza a origem do domínio como Referer.

---

## 3. Modelo de Dados (`database.json`)

Atualização do registro com `id: 1` ("Overgeared"):
```json
{
  "id": 1,
  "title": "Overgeared",
  "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
  "currentChapter": 197,
  "updatedAt": 1792461210
}
```

---

## 4. Estratégia de Testes

- **Testes Unitários:**
  - `test_extract_manhuatop_images`: garante que o parser antigo não quebre.
  - `test_extract_asurascans_images`: validação com mock do HTML real do Asura Scans extraindo exatamente 19 páginas de capítulo ordenadas de `001.webp` a `019.webp`.
  - `test_chapter_images_endpoint_asurascans`: integração com endpoint `/api/chapter-images` retornando `count: 19` e status 200.
  - `test_proxy_image_asurascans_referer`: validação de cabeçalhos de requisição do proxy.
- **Testes Automatizados:** Suíte completa executada via `make test`.
