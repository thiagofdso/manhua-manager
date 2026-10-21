# Design: Download Local de Episódios e Leitura Offline (Web & Mobile)

**Data:** 21/10/2026  
**Status:** Aprovado  
**Escopo:** Backend Flask (`server.py`), Interface Web (`index.html`), Aplicativo Móvel Flutter (`mobile_app/`).

---

## 1. Contexto e Objetivos

Atualmente, tanto a interface Web quanto o aplicativo Flutter do **Manhua Manager** dependem de chamadas em tempo real à API para buscar as URLs das imagens de cada capítulo (`/api/chapter-images`) e renderizá-las através do proxy de imagens (`/api/proxy-image`).

Este design especifica a funcionalidade completa de **download local de capítulos** e **leitura offline**, com os seguintes requisitos fundamentais:
1. **Download por Faixa (Range):** O usuário pode escolher um intervalo de capítulos (ex: do capítulo 10 ao 25) para baixar localmente.
2. **Endpoint em Lote no Backend:** O backend resolve as URLs das imagens de todos os capítulos do intervalo e retorna uma resposta estruturada em JSON.
3. **Armazenamento Local nos Clientes:**
   - **Web:** Utiliza **IndexedDB** para armazenar as imagens binárias (`Blob`) e os metadados dos capítulos.
   - **Mobile:** Salva os arquivos de imagens diretamente no sistema de arquivos local (`path_provider`) e mantém um catálogo estruturado.
4. **Verificação Offline Obrigatória no Leitor:** Ao abrir um capítulo no leitor, o frontend (Web e Mobile) deve **sempre verificar se o capítulo existe localmente** antes de tentar qualquer requisição ao backend. Se existir, o capítulo é carregado instantaneamente do armazenamento local, funcionando 100% offline.
5. **Cópia Local da Lista de Obras no Mobile:** O aplicativo móvel deve salvar uma cópia local atualizada do catálogo de obras. Se o backend estiver inacessível, o app exibe essa lista local para que o usuário possa acessar suas obras e ler capítulos baixados offline.
6. **Permissão de Acesso ao Disco no Mobile:** Na primeira abertura do aplicativo, o app deve solicitar a permissão de armazenamento necessária para gravação e leitura dos downloads.
7. **Gerenciamento e Limpeza Manual (Sem Limpeza Automática):** O usuário pode remover capítulos baixados individualmente, remover todos os capítulos de uma obra ou limpar todos os downloads locais. **É estritamente proibida qualquer limpeza automática, expiração por tempo ou remoção por LRU.**

---

## 2. Backend (`server.py`)

### 2.1 Novo Endpoint: `GET /api/manhuas/<int:item_id>/batch-chapter-images`

- **Rota:** `/api/manhuas/<int:item_id>/batch-chapter-images`
- **Método:** `GET`
- **Query Parameters:**
  - `start` (*int*, obrigatório): Número do capítulo inicial (>= 1).
  - `end` (*int*, obrigatório): Número do capítulo final (>= start).

#### Validações
- Se `item_id` não existir em `database.json`: Retorna HTTP 404 (`{"error": "Obra não encontrada"}`).
- Se `start < 1` ou `end < start`: Retorna HTTP 400 (`{"error": "Intervalo de capítulos inválido"}`).
- Se `(end - start + 1) > 50`: Retorna HTTP 400 (`{"error": "Limite máximo de 50 capítulos por lote excedido"}`).

#### Extração Concorrente
- Para cada capítulo $c \in [\text{start}, \text{end}]$, constrói a URL alvo correspondente.
- Executa a extração em paralelo utilizando `concurrent.futures.ThreadPoolExecutor(max_workers=5)`.
- Se um capítulo individual falhar ou não for encontrado no provedor externo, registra `"images": []` e `"error": "..."` para aquele capítulo sem interromper o processamento dos demais capítulos do lote.

#### Estrutura do JSON de Resposta
```json
{
  "manhuaId": 1,
  "title": "Overgeared",
  "range": { "start": 10, "end": 12 },
  "totalChapters": 3,
  "chapters": [
    {
      "chapter": 10,
      "targetUrl": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/10",
      "images": [
        "https://asurascans.com/media/overgeared/ch10/01.jpg",
        "https://asurascans.com/media/overgeared/ch10/02.jpg"
      ]
    },
    {
      "chapter": 11,
      "targetUrl": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/11",
      "images": [
        "https://asurascans.com/media/overgeared/ch11/01.jpg"
      ]
    },
    {
      "chapter": 12,
      "targetUrl": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/12",
      "images": [],
      "error": "Capítulo não disponível na fonte"
    }
  ]
}
```

---

## 3. Frontend Web (`index.html`)

### 3.1 Armazenamento com IndexedDB (`ManhuaOfflineDB`)
- **Banco de Dados:** `ManhuaOfflineDB` (versão 1)
- **Object Store `chapters`:**
  - Chave primária: `"${manhuaId}_${chapter}"`
  - Valor:
    ```javascript
    {
      manhuaId: 1,
      chapter: 10,
      title: "Overgeared",
      pageCount: 15,
      downloadedAt: 1792600000
    }
    ```
- **Object Store `pages`:**
  - Chave primária: `"${manhuaId}_${chapter}_${pageIndex}"`
  - Valor: `Blob` (conteúdo binário da imagem)

### 3.2 Modal de Downloads no Card da Obra
- Cada card de obra recebe um botão com ícone de download (`💾` ou ícone SVG de download).
- Ao clicar, abre o modal **"Downloads Offline - {Título}"**:
  - **Formulário de Download:**
    - Campo *Do Capítulo* e *Até o Capítulo* (sugestão inicial: capítulo atual da obra).
    - Botão *Baixar Capítulos*.
  - **Barra de Progresso:**
    - Exibe barra percentual e status em texto: *"Baixando capítulo 11 (imagem 3 de 15)..."*.
    - Para cada URL retornada pelo backend, a imagem é baixada via `/api/proxy-image?url=...` como `res.blob()` e armazenada no IndexedDB.
  - **Lista de Capítulos Baixados:**
    - Tabela/lista dos capítulos baixados desta obra com a contagem de páginas e data de download.
    - Botão de lixeira individual para excluir um capítulo específico do IndexedDB.
    - Botão *Excluir Todos os Capítulos Desta Obra*.

### 3.3 Limpeza Global de Armazenamento
- No modal de configurações / topo da página:
  - Exibe resumo de capítulos armazenados no navegador.
  - Botão *Limpar Todos os Downloads Locais* (com diálogo de confirmação).
  - Nenhuma expiração ou limpeza automática.

### 3.4 Leitor Web Offline (`loadChapterPages`)
- Ao abrir o leitor ou trocar de capítulo:
  1. Consulta a store `chapters` no IndexedDB para a chave `"${readerManhua.id}_${readerManhua.currentChapter}"`.
  2. **Se existir no IndexedDB:**
     - Carrega todas as páginas associadas da store `pages`.
     - Gera URLs locais temporárias com `URL.createObjectURL(blob)`.
     - Renderiza imediatamente os elementos `<img>` no container do leitor.
     - Exibe indicador no cabeçalho: `💾 Offline (Baixado)`.
     - **Não faz nenhuma requisição HTTP de imagens ou API.**
  3. **Se não existir:**
     - Executa o fluxo padrão chamando `/api/chapter-images?url=...` e `/api/proxy-image`.

---

## 4. Aplicativo Móvel Flutter (`mobile_app/`)

### 4.1 Permissões no Android (`AndroidManifest.xml` e `permission_handler`)
- Declarar permissões no `mobile_app/android/app/src/main/AndroidManifest.xml`:
  - `READ_EXTERNAL_STORAGE`
  - `WRITE_EXTERNAL_STORAGE`
- Adicionar dependência `permission_handler` e `path_provider` no `pubspec.yaml`.
- Na inicialização da aplicação (`HomeScreen.initState`):
  - Verifica e solicita permissão de armazenamento de forma transparente logo na primeira abertura do app.

### 4.2 Cópia Local da Lista de Obras (Fallback Offline)
- No `StorageService`:
  - `saveCachedManhuas(List<Manhua> manhuas)`: Serializa a lista de obras em JSON e salva no `SharedPreferences` sempre que `apiService.fetchManhuas()` obtiver sucesso.
  - `getCachedManhuas()`: Carrega e desserializa a lista salva localmente.
- No `ManhuaController.loadManhuas()`:
  - Se a requisição de rede falhar (falta de internet ou servidor desligado), busca a cópia de `getCachedManhuas()`.
  - Se houver obras em cache, popula a lista e define `isOfflineMode = true`.
  - Exibe um banner visual discreto no topo da `HomeScreen`: *"Modo Offline: exibindo lista salva localmente"*.
  - O usuário pode navegar e abrir qualquer obra que tenha capítulos baixados, sem tela bloqueante de erro.

### 4.3 Armazenamento Local no Sistema de Arquivos (`DownloadService`)
- Criação do serviço `DownloadService`:
  - Diretório base de downloads: `<getApplicationDocumentsDirectory()>/downloads/`
  - Estrutura de pastas:
    `downloads/<manhuaId>/chapter_<chapter>/<pageIndex>.jpg`
  - Registro de capítulos baixados: Salvo em arquivo manifesto `downloads/downloads_manifest.json` ou `SharedPreferences`.
  - Métodos do serviço:
    - `Future<bool> hasChapter(int manhuaId, int chapter)`
    - `Future<List<String>> getChapterImagePaths(int manhuaId, int chapter)`
    - `Future<void> saveChapterImages(int manhuaId, int chapter, List<List<int>> imageBytesList)`
    - `Future<void> deleteChapter(int manhuaId, int chapter)`
    - `Future<void> deleteAllForManhua(int manhuaId)`
    - `Future<void> clearAllDownloads()`
    - `Future<List<int>> getDownloadedChapters(int manhuaId)`
    - `Future<int> getTotalDownloadedChaptersCount()`

### 4.4 Modal de Downloads no Card da Obra (`DownloadManhuaDialog`)
- No card da obra, no menu `...` ou botão de download:
  - Abre o diálogo `DownloadManhuaDialog`:
    - Campos numéricos *Capítulo Inicial* e *Capítulo Final*.
    - Botão *Baixar*.
    - Chama `apiService.fetchBatchChapterImages(manhuaId, start, end)`.
    - Realiza o download de cada imagem através de `apiService.getProxyImageUrl(url)` e salva os bytes via `DownloadService`.
    - Barra de progresso visual com contagem de capítulos e páginas em andamento.
    - Seção inferior com a lista dos capítulos salvos localmente, botão de lixeira individual e botão *Excluir todos desta obra*.

### 4.5 Leitor Offline (`ReaderScreen`)
- Em `_loadPages()`:
  1. Executa `await downloadService.hasChapter(_currentManhua.id, _currentChapter)`.
  2. **Se estiver baixado localmente:**
     - Recupera os caminhos dos arquivos locais via `getChapterImagePaths`.
     - Define `_imageUrls` com os paths locais.
     - No `build()`, renderiza utilizando `Image.file(File(path))` com fallback seguro.
     - Exibe badge na AppBar: `💾 Salvo Localmente`.
     - **Não faz chamada ao backend.**
  3. **Se não estiver baixado localmente:**
     - Tenta carregar normalmente da API através de `apiService.fetchChapterImages`.
     - Caso o backend esteja inacessível, informa: *"Este capítulo não está baixado localmente e o servidor está indisponível"*.

### 4.6 Limpeza nas Configurações (`SettingsDialog`)
- Seção **"Downloads Locais"**:
  - Exibe o número total de capítulos salvos no dispositivo.
  - Botão *Limpar Todos os Downloads Locais*.
  - Nenhuma rotina de limpeza automática ou expiração de arquivos.

---

## 5. Casos de Borda e Tratamento de Erros

1. **Capítulo sem imagens na fonte:** O backend retorna `"images": []` e o frontend avisa o usuário sem abortar os demais capítulos do range.
2. **Queda de conexão no meio do download:** O frontend grava com sucesso os capítulos que foram concluídos antes da interrupção. O usuário pode reiniciar o download do capítulo restante.
3. **Servidor backend offline:** O app mobile abre em modo offline utilizando a lista de obras cacheada e abre imediatamente os capítulos baixados no leitor.
4. **Armazenamento de disco cheio:** Captura de exceção de escrita no disco com alerta amigável ao usuário.

---

## 6. Estratégia de Testes

### 6.1 Backend (`tests/test_server.py`)
- Teste de validação de parâmetros de `batch-chapter-images` (ausência de params, start > end, limite > 50, manhua inexistente).
- Teste de retorno com mock de capítulos múltiplos com resposta 200 e payload JSON contendo o array `chapters`.

### 6.2 Mobile (`mobile_app/test/`)
- Testes unitários do `DownloadService` (salvar, verificar existência, listar capítulos e excluir).
- Teste do `StorageService` para `saveCachedManhuas` e `getCachedManhuas`.
- Teste do leitor `ReaderScreen` verificando que prioriza o armazenamento local antes de chamar `apiService`.
- Execução com `./.venv/bin/pytest tests/` e `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`.
