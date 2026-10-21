# Design: Gerenciador Global de Downloads em Segundo Plano, Cancelamento e Fila Ativa (Mobile & Web)

**Data:** 21/10/2026  
**Status:** Aprovado  
**Escopo:** Frontend Web (`index.html`), Aplicativo Móvel Flutter (`mobile_app/`).

---

## 1. Contexto e Objetivos

Com a introdução do download local de capítulos por intervalo, os usuários precisam ter controle total sobre as transferências em andamento:
1. **Download Contínuo e Não-Bloqueante:** O download de capítulos deve continuar rodando em segundo plano se o usuário fechar o diálogo/modal ou navegar pelo app.
2. **Reconexão de Progresso:** Ao reabrir o diálogo de download de uma obra que já está sendo baixada, o usuário deve ver a barra de progresso no ponto exato em que a transferência está.
3. **Cancelamento Sob Demanda:** O usuário deve ter um botão "Cancelar Download" tanto no diálogo da obra quanto na listagem global de downloads ativos, interrompendo imediatamente o loop de requisições e preservando os capítulos já 100% concluídos.
4. **Fila Global de Downloads Ativos:** A tela principal (Web e Mobile) deve ter um atalho visual com contador de tarefas ativas, abrindo um painel com todas as obras em transferência e seus respectivos controles.

---

## 2. Aplicativo Móvel Flutter (`mobile_app/`)

### 2.1 Modelo `DownloadTask`
Arquivo: `mobile_app/lib/models/download_task.dart`
- Propriedades:
  - `int manhuaId`
  - `String title`
  - `int startChapter`
  - `int endChapter`
  - `int currentChapter`
  - `int currentImageIndex`
  - `int totalImagesInChapter`
  - `int totalImagesOverall`
  - `int downloadedImagesOverall`
  - `double progress` (0.0 a 1.0)
  - `String progressMessage` (ex: `"Capítulo 12: imagem 4 de 20..."`)
  - `DownloadStatus status` (`queued`, `downloading`, `completed`, `cancelled`, `error`)
  - `String? errorMessage`
  - `bool isCancelled`

### 2.2 Serviço Reativo `DownloadManager`
Arquivo: `mobile_app/lib/services/download_manager.dart`
- Herda de `ChangeNotifier` para que telas e diálogos reajam em tempo real.
- Mantém `Map<int, DownloadTask> _tasks`.
- Métodos principais:
  - `List<DownloadTask> get activeTasks`: Retorna tarefas com status `downloading` ou `queued`.
  - `DownloadTask? getTask(int manhuaId)`: Retorna a tarefa atual daquela obra.
  - `Future<void> startDownload(...)`:
    - Verifica se já existe download rodando para o `manhuaId`.
    - Itera sobre os capítulos e imagens.
    - Antes de cada capítulo e de cada imagem, checa `if (task.isCancelled) return;`.
    - Atualiza os campos de progresso e executa `notifyListeners()`.
    - Ao concluir um capítulo, grava no disco via `DownloadService`.
  - `void cancelDownload(int manhuaId)`:
    - Marca `task.isCancelled = true`, define status como `cancelled` e emite `notifyListeners()`.

### 2.3 Diálogo da Obra (`DownloadManhuaDialog`)
- Consome o `DownloadManager` via `context.watch<DownloadManager>()` ou listener:
  - Se `task != null && task.status == DownloadStatus.downloading`:
    - Desabilita os campos de texto.
    - Exibe barra de progresso e texto da tarefa ativa.
    - Substitui o botão "Iniciar Download" por um botão vermelho: `"Cancelar Download"`.
  - O botão "Fechar" pode ser clicado livremente sem interromper a tarefa.

### 2.4 Fila Global de Downloads na `HomeScreen` e `ActiveDownloadsDialog`
- Na `HomeScreen`:
  - Na AppBar, adiciona ícone `Icons.downloading` com badge numérico contendo `downloadManager.activeTasks.length`.
  - Ao clicar, abre o diálogo `ActiveDownloadsDialog`.
- Em `ActiveDownloadsDialog`:
  - Lista todas as obras em andamento com título, intervalo, barra de progresso, percentual e botão `"Cancelar"`.

---

## 3. Frontend Web (`index.html`)

### 3.1 Gerenciador Global `activeDownloads`
- Objeto global em memória rastreando tarefas:
  ```javascript
  activeDownloads[manhuaId] = {
    manhuaId,
    title,
    startChapter,
    endChapter,
    currentChapter,
    progressPercent,
    progressText,
    status: 'downloading',
    isCancelled: false,
    abortController: new AbortController()
  };
  ```

### 3.2 Execução e Cancelamento
- `startBatchDownload()`:
  - Cria a entrada em `activeDownloads[manhuaId]`.
  - Usa `signal: task.abortController.signal` nos `fetch()` de `/api/proxy-image`.
  - Antes de cada imagem/capítulo, valida `if (task.isCancelled) return;`.
  - Grava capítulos concluídos no `IndexedDB`.
  - Atualiza o badge do cabeçalho e os modais abertos.
- `cancelActiveDownload(manhuaId)`:
  - Seta `task.isCancelled = true`.
  - Invoca `task.abortController.abort()`.
  - Remove da lista ativa e atualiza a interface.

### 3.3 Modal da Obra (`#downloadModal`)
- Ao abrir para um `manhuaId`:
  - Se estiver em `activeDownloads`, restaura o progresso e mostra botão vermelho `"Cancelar Download"`.
  - Fechar o modal oculta apenas a janela visual; a tarefa permanece rodando no navegador.

### 3.4 Modal de Fila Global (`#activeDownloadsModal`)
- No cabeçalho da lista principal:
  - Botão dinâmico `📥 Downloads Ativos (N)`.
  - Clicar abre `#activeDownloadsModal`, exibindo todos os downloads correntes com progresso e botão individual de cancelamento.

---

## 4. Estratégia de Testes

1. **Testes Unitários no Mobile (`mobile_app/test/services/download_manager_test.dart`):**
   - Início de download atualiza tarefas ativas.
   - Cancelamento seta `isCancelled` e encerra a tarefa.
   - Progresso é emitido via `notifyListeners`.
2. **Testes de Widgets no Mobile:**
   - Diálogo `DownloadManhuaDialog` exibe botão de cancelar quando tarefa está ativa.
   - `ActiveDownloadsDialog` lista tarefas em andamento.
3. **Testes Backend/Web (`tests/test_server.py`):**
   - Verificar presença dos novos elementos de interface da fila de downloads na Web.
