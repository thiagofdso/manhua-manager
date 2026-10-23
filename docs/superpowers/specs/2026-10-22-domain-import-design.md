# Especificação de Design: Importação de Obras por Domínio (Asura Scans)

- **Data:** 2026-10-22
- **Status:** Aprovado para Planejamento
- **Domínio Inicial:** `asurascans.com`

---

## 1. Visão Geral e Objetivos

O objetivo deste recurso é permitir que o usuário importe obras em lote a partir dos sites parceiros/fontes suportadas, iniciando por `https://asurascans.com/browse/comics`. A funcionalidade possibilita navegar ou pesquisar o catálogo do domínio, selecionar as obras desejadas via checkboxes, e cadastrá-las automaticamente no sistema com configurações padrão estabelecidas, garantindo que obras já adicionadas manualmente não sejam sobrescritas.

Para otimizar o uso de rede e evitar scraping repetitivo, as extrações de catálogo são armazenadas em cache local no backend com validade de 1 semana (7 dias) por domínio.

---

## 2. Requisitos

### 2.1 Requisitos Funcionais
1. **Seletor de Domínios:**
   - Interface com dropdown listando os domínios do ecossistema do aplicativo.
   - Domínios sem implementação de importação exibem a etiqueta informativa `"Sem suporte"`.
   - Domínios suportados (inicialmente `asurascans.com`) habilitam as ações de pesquisa e importação.
2. **Pesquisa e Catálogo:**
   - Campo de texto para filtro por nome (opcional) e botão `"Pesquisar"`.
   - Ao pesquisar, carrega o catálogo correspondente do domínio (com suporte a paginação).
   - A listagem exibe **apenas**:
     - Checkbox de seleção.
     - Nome da obra (`title`).
     - Quantidade de episódios / último capítulo (`lastChapter`).
     - Badge/status `"Já cadastrada"` quando a obra já existir no banco.
3. **Seleção e Ações em Lote:**
   - Checkbox `"Selecionar todos"` para marcar ou desmarcar todas as obras elegíveis da listagem atual.
   - Obras que já constam no banco de dados (`alreadyExists: true`) têm seus checkboxes desabilitados e não são marcadas pelo `"Selecionar todos"`.
   - Botão `"Importar"` que aciona o cadastro das obras selecionadas.
4. **Regras de Cadastro na Importação:**
   - `currentChapter`: inicializado em `1`.
   - `updateDay`: inicializado em `6` (Domingo).
   - `lastChapter`: preenchido com o número do último capítulo extraído (quando disponível).
   - `urlTemplate`: URL da obra preservando o placeholder `{chapter}` (ex: `https://asurascans.com/comics/{slug}/chapter/{chapter}`).
   - `updatedAt`: timestamp unix atual.
   - `customOrder`: ordem ajustada para o final da fila de leitura não-favorita.
   - `isHiatus`: `false`.
   - **Prevenção de sobrescrita:** se a obra já existir no banco (por `urlTemplate` ou título idêntico), o backend ignora a inserção sem alterar a obra cadastrada previamente.
5. **Cache em Arquivo por Domínio:**
   - Salvo em `.cache/import_cache_<domain>.json`.
   - TTL de 7 dias (604.800 segundos).
   - Se o cache for válido, responde as pesquisas e paginações a partir do cache para evitar requisições desnecessárias ao site externo.

### 2.2 Requisitos de Interface
- **Aplicação Web (`index.html`):**
  - Botão `"📥 Importar Obras"` no cabeçalho.
  - Modal responsivo e integrado ao design existente.
- **Aplicativo Mobile (`mobile_app`):**
  - Item `"Importar Obras"` no menu lateral (`AppDrawer`).
  - Tela/diálogo dedicada de importação com dropdown, busca, seleção e importação.

---

## 3. Arquitetura e Componentes

### 3.1 Backend (`server.py` e `importers/`)

```
importers/
├── __init__.py
├── base.py            # BaseDomainImporter (classe base abstrata)
├── registry.py        # Registro centralizado de domínios e suporte
└── asurascans.py      # Implementação para asurascans.com com cache
```

#### BaseDomainImporter (`importers/base.py`)
```python
class BaseDomainImporter:
    domain: str
    name: str

    def is_supported(self) -> bool:
        return False

    def search_or_browse(self, query: str = None, page: int = 1) -> dict:
        raise NotImplementedError
```

#### AsurascansImporter (`importers/asurascans.py`)
- URL base: `https://asurascans.com/browse/comics`
- Extrai:
  - `title`: decodificado via `html.unescape`.
  - `slug`: extraído de `/comics/{slug}`.
  - `urlTemplate`: `https://asurascans.com/comics/{slug}/chapter/{chapter}`.
  - `lastChapter`: extraído do bloco de contagem de capítulos (`<span ...>N Chs.</span>`).
- Gerencia o arquivo de cache `.cache/import_cache_asurascans_com.json`:
  - Estrutura contendo `timestamp` de criação e dicionário indexado por chave de busca/página.
  - TTL de 7 dias.

#### Registro de Domínios (`importers/registry.py`)
Lista padronizada dos domínios do sistema:
- `asurascans.com`: Suportado (`true`)
- `mangafire.to`: Não suportado (`false`)
- `comix.to`: Não suportado (`false`)
- `manhuaus.com`: Não suportado (`false`)
- `manhuatop.org`: Não suportado (`false`)
- `ravenscans.org`: Não suportado (`false`)
- `arenascan.com`: Não suportado (`false`)
- `mgeko.cc`: Não suportado (`false`)
- `levelingwithgods.com`: Não suportado (`false`)
- `pickmeupgacha.com`: Não suportado (`false`)
- `magicemperor.online`: Não suportado (`false`)

### 3.2 Endpoints da API REST

#### `GET /api/import/domains`
Retorna a lista de domínios disponíveis e seu status de suporte:
```json
[
  { "domain": "asurascans.com", "name": "Asura Scans", "supported": true },
  { "domain": "mangafire.to", "name": "MangaFire", "supported": false },
  ...
]
```

#### `GET /api/import/browse?domain=asurascans.com&q=solo&page=1`
Retorna a listagem de obras com identificação de duplicatas já cadastradas:
```json
{
  "status": "ok",
  "domain": "asurascans.com",
  "page": 1,
  "totalPages": 5,
  "items": [
    {
      "title": "Solo Swordmaster",
      "urlTemplate": "https://asurascans.com/comics/solo-swordmaster-11fe7da3/chapter/{chapter}",
      "lastChapter": 23,
      "alreadyExists": false
    },
    {
      "title": "The Extra’s Academy Survival Guide",
      "urlTemplate": "https://asurascans.com/comics/the-extras-academy-survival-guide-11fe7da3/chapter/{chapter}",
      "lastChapter": 130,
      "alreadyExists": true
    }
  ]
}
```

#### `POST /api/import`
Recebe as obras a serem inseridas e executa o cadastro:
- **Payload:**
  ```json
  {
    "items": [
      {
        "title": "Solo Swordmaster",
        "urlTemplate": "https://asurascans.com/comics/solo-swordmaster-11fe7da3/chapter/{chapter}",
        "lastChapter": 23
      }
    ]
  }
  ```
- **Processamento:**
  - Carrega `database.json`.
  - Para cada item, valida se `urlTemplate` ou `title` já existem. Se já existirem, incrementa contador `skipped`.
  - Se novo: cria registro com `currentChapter: 1`, `updateDay: 6`, `lastChapter`, `urlTemplate`, `isHiatus: false`, `updatedAt: now`.
  - Salva `database.json`.
- **Resposta:**
  ```json
  {
    "status": "ok",
    "imported": 1,
    "skipped": 0
  }
  ```

---

## 4. Interfaces de Usuário

### 4.1 Interface Web (`index.html`)
- **Gatilho:** Botão no `<header>`: `<button class="btn btn-secondary btn-sm" onclick="openImportModal()">📥 Importar Obras</button>`.
- **Modal (`#importModal`):**
  - Dropdown com domínios e badge visual ("✓ Suportado" / "⚠️ Sem suporte").
  - Linha com `<input id="importSearchInput">` e `<button onclick="searchImportWorks()">Pesquisar</button>`.
  - Linha de controle com checkbox `<input type="checkbox" id="selectAllImport"> Selecionar todos` e contador `(X selecionadas)`.
  - Tabela/lista compacta com altura fixa e scroll:
    - Coluna 1: Checkbox (habilitado apenas para `!alreadyExists`).
    - Coluna 2: Título da obra.
    - Coluna 3: Último episódio (`Cap. N` ou `-`).
    - Coluna 4: Badge `"Já cadastrada"` quando aplicável.
  - Paginação: botões `< Anterior` e `Próxima >`.
  - Botão inferior: `<button id="btnConfirmImport" class="btn w-full">Importar (N)</button>`.

### 4.2 Aplicativo Mobile (`mobile_app`)
- **Gatilho:** Item no `AppDrawer`: ListTile com ícone `Icons.cloud_download_outlined`, título `"Importar Obras"`.
- **Tela `ImportManhuaScreen`:**
  - `DropdownButtonFormField` para seleção de domínio com indicador visual de suporte.
  - `TextField` de busca com ação no teclado e botão de pesquisa.
  - `CheckboxListTile` para "Selecionar todos" (apenas obras não existentes).
  - `ListView.builder` exibindo:
    - `Checkbox` (desabilitado se já cadastrada).
    - Título (`Text(..., maxLines: 1, overflow: TextOverflow.ellipsis)`).
    - Subtítulo com `Cap. ${item.lastChapter ?? '-'}`.
    - Trailing chip `"Já cadastrada"` em cinza/âmbar.
  - Paginação inferior com botões de navegação de páginas.
  - `ElevatedButton` fixo na base para confirmar importação e disparar atualização no `ManhuaController`.

---

## 5. Estratégia de Testes

1. **Testes Unitários Backend (`tests/test_import.py`):**
   - Teste de listagem de domínios (`/api/import/domains`).
   - Teste do extrator `AsurascansImporter` com mock e com resposta HTML real.
   - Teste de expiração e hit de cache de 1 semana.
   - Teste de importação (`/api/import`) com verificação de valores padrão (`currentChapter = 1`, `updateDay = 6`, `lastChapter`, `urlTemplate`).
   - Teste de prevenção de sobrescrita (duplicatas existentes são ignoradas).
2. **Testes Unitários Mobile (`mobile_app/test/`):**
   - Teste do modelo e serviço de importação na `ApiService`.
   - Teste de renderização da tela de importação e seleção de checkboxes.
3. **Verificação Operacional:**
   - `./.venv/bin/pytest tests/`
   - `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
   - `systemctl --user restart manhua-manager.service`
