# Design Specification: Importação com Opção "Todos" Baseada em Cache Multi-Domínio

- **Data:** 2026-10-23
- **Status:** Aprovado
- **Autor:** Thiago Oliveira / Antigravity

---

## 1. Visão Geral
Adicionar ao módulo de importação de obras do **Manhua Manager** a opção **"Todos"** no seletor de domínios. Quando essa opção for selecionada, as buscas e listagens serão executadas exclusivamente em cima dos arquivos locais de cache (`.cache/import_cache_*.json`) pertencentes a todos os domínios que atualmente possuem cache em disco. Cada obra exibida incluirá a indicação visual explícita do seu domínio de origem.

---

## 2. Requisitos e Critérios de Sucesso
1. **Opção no Catálogo:** O seletor de domínios deve disponibilizar a opção `"all"` (`name: "Todos"`, `supported: True`), posicionada no topo da listagem de domínios.
2. **Varredura Dinâmica de Caches:**
   - Buscar em todos os arquivos que correspondam ao padrão `.cache/import_cache_*.json`.
   - Ignorar graciosamente domínios que não possuem arquivo de cache criado em disco.
   - Extrair itens de todas as chaves de busca (`catalog[query][page]`) armazenadas no cache de cada domínio.
3. **Desduplicação e Identificação de Origem:**
   - Desduplicar itens com base no `urlTemplate` para evitar que a mesma obra apareça repetida se estiver presente em mais de uma query no cache do mesmo domínio.
   - Atribuir a cada item os atributos `domain` (ex: `"mangafire.to"`) e `domainName` (ex: `"MangaFire"`).
4. **Filtragem e Paginação:**
   - Se `q` for fornecido: filtrar os itens cujo título contenha o texto pesquisado (`query.lower() in item["title"].lower()`).
   - Se `q` estiver vazio: listar todos os itens cacheados.
   - Ordenar os itens alfabeticamente pelo título.
   - Paginar em memória com limite de 40 itens por página.
5. **Exibição nas Interfaces (Mobile e Web):**
   - **Mobile (Flutter):** Subtítulo do `ListTile` deve exibir `"<domainName> • Cap. <lastChapter>"` (ou `"<domainName> • Sem capítulos"`).
   - **Web (`index.html`):** Na listagem, exibir `"[<domainName>] Último: Cap. <lastChapter>"`.
   - Manter a marcação `"Já cadastrada"` para itens presentes em `database.json`.
6. **Integridade de Testes:**
   - 100% dos testes do Pytest e do Flutter devem passar.

---

## 3. Arquitetura e Componentes

### 3.1 Backend (`importers/all_cache.py` e `importers/registry.py`)
- Criar a classe `AllCacheImporter(BaseDomainImporter)` em `importers/all_cache.py`:
  - `domain = "all"`
  - `name = "Todos"`
  - `__init__(self, cache_dir: Optional[str] = None)`
  - `_get_domain_info_from_filename(filename: str) -> tuple[str, str]`: mapeia sufixos (ex: `import_cache_mangafire_to.json` $\rightarrow$ `("mangafire.to", "MangaFire")`) com base em `DOMAINS_CATALOG`.
  - `search_or_browse(query: Optional[str] = None, page: int = 1, force_refresh: bool = False) -> dict`:
    - Varre o diretório `.cache/` por `import_cache_*.json`.
    - Carrega cada JSON, itera pelas entradas de `catalog`, coleta os itens e vincula `domain` e `domainName`.
    - Desduplica por `urlTemplate`.
    - Filtra por `query` se fornecido.
    - Ordena alfabeticamente pelo título.
    - Pagina em fatias de 40 itens e retorna `{"items": page_items, "page": page, "totalPages": total_pages, "domain": "all"}`.
- Registrar em `importers/registry.py`:
  - Inserir `{"domain": "all", "name": "Todos", "supported": True}` no topo de `DOMAINS_CATALOG`.
  - Mapear `"all": AllCacheImporter()` em `_IMPORTERS`.

### 3.2 Endpoint da API (`server.py`)
- Na rota `/api/import/browse`:
  - Já resolve `importer = get_importer(domain)`.
  - Para cada item retornado, inclui `domain` e `domainName` no payload JSON de resposta, além do campo existente `alreadyExists`.

### 3.3 Modelo e Tela Mobile (`mobile_app/`)
- Em `mobile_app/lib/models/import_work_item.dart`:
  - Adicionar campos opcionais: `final String? domain;` e `final String? domainName;`.
  - Atualizar construtor e `fromJson` / `toJson`.
- Em `mobile_app/lib/screens/import_manhua_screen.dart`:
  - Na renderização do `ListTile`:
    - Se `item.domainName` estiver preenchido, formatar subtítulo como `"${item.domainName} • ${chText}"`.
    - Caso contrário, manter apenas `${chText}`.

### 3.4 Interface Web (`index.html`)
- Em `renderImportWorkList()`:
  - Se `item.domainName` estiver presente: exibir `[${item.domainName}] ` antes do número do capítulo.

---

## 4. Testes e Validação
1. **Testes Unitários de `AllCacheImporter` (`tests/test_importers.py`):**
   - Agregação de múltiplos arquivos de cache em diretório temporário (`tmp_path`).
   - Verificação de filtragem case-insensitive por título.
   - Verificação de desduplicação por `urlTemplate`.
   - Verificação de paginação e cálculo de `totalPages`.
   - Verificação de presença dos campos `domain` e `domainName`.
2. **Testes da API (`tests/test_import_api.py`):**
   - Chamada `GET /api/import/browse?domain=all&q=...`.
   - Validação da resposta e verificação do status `200 OK`.
3. **Testes do Aplicativo Flutter (`mobile_app/test/`):**
   - Teste de decodificação do modelo `ImportWorkItem` com `domain` e `domainName`.
   - Teste de widget de `ImportManhuaScreen` validando que a identificação do domínio é exibida na tela.
4. **Verificação Operacional:**
   - Execução de `pytest tests/`.
   - Execução de `flutter test`.
   - Reinício de `manhua-manager.service` via `systemctl --user`.
