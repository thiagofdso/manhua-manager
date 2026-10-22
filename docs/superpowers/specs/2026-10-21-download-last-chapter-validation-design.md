# Design Spec: Validação do Último Episódio na Função de Download

**Data:** 2026-10-21  
**Autor:** Thiago Oliveira / Assistant  
**Status:** Aprovado  

## 1. Visão Geral e Motivação
Atualmente, as obras no Manhua Manager podem conter o campo opcional `lastChapter` (último episódio lançado). Quando preenchido, esse campo impede o usuário de avançar a leitura para além do último capítulo existente. No entanto, o fluxo de download em lote (tanto na interface Web quanto no aplicativo móvel Flutter e na rota de extração da API) permitia solicitar intervalos arbitrários sem validação contra o `lastChapter`.

Esta especificação define a validação ponta a ponta do `lastChapter` durante a configuração e disparo de downloads em lote, impedindo solicitações de capítulos além do último disponível e sugerindo valores coerentes nos formulários.

## 2. Requisitos do Sistema

### 2.1 Requisitos Funcionais (RF)
- **RF01 - Sugestão Inteligente de Intervalo (Web & Mobile):**
  - Ao abrir o diálogo de download, o campo de capítulo final não deve ultrapassar `lastChapter`, caso este esteja definido.
- **RF02 - Bloqueio de Download no Cliente Web:**
  - Se o usuário tentar iniciar download com `start > lastChapter` ou `end > lastChapter`, o sistema bloqueia a execução e exibe alerta informativo.
- **RF03 - Bloqueio de Download no App Mobile (Flutter):**
  - Se o usuário tentar iniciar download com `start > lastChapter` ou `end > lastChapter`, o aplicativo bloqueia o início e exibe um `SnackBar` explicativo.
- **RF04 - Validação no Backend (API):**
  - A rota `GET /api/manhuas/<id>/batch-chapter-images` deve retornar HTTP 400 caso `lastChapter` esteja definido e `start > lastChapter` ou `end > lastChapter`.
- **RF05 - Preservação de Comportamento sem `lastChapter`:**
  - Quando a obra não tiver `lastChapter` definido (`null`), o comportamento pré-existente de download permanece inalterado (sem restrição além do limite de 50 capítulos por lote).

## 3. Arquitetura e Detalhes de Implementação

### 3.1 Backend (`server.py`)
No endpoint `/api/manhuas/<int:item_id>/batch-chapter-images`:
- Verificar se `manhua.get("lastChapter") is not None`.
- Se verdadeiro, validar:
  ```python
  last_chap = manhua.get("lastChapter")
  if last_chap is not None and (start > last_chap or end > last_chap):
      return jsonify({"error": f"Capítulo excede o último episódio disponível ({last_chap})"}), 400
  ```

### 3.2 Frontend Web (`index.html`)
- Em `openDownloadModal(id)`:
  - Se `m.lastChapter != null`, configurar o valor padrão do capítulo final respeitando o teto:
    ```javascript
    const maxChap = m.lastChapter;
    const defaultEnd = maxChap != null ? Math.min((m.currentChapter || 1) + 4, maxChap) : (m.currentChapter || 1) + 4;
    document.getElementById('downloadEndChapter').value = Math.max(defaultEnd, m.currentChapter || 1);
    if (maxChap != null) {
      document.getElementById('downloadStartChapter').max = maxChap;
      document.getElementById('downloadEndChapter').max = maxChap;
    } else {
      document.getElementById('downloadStartChapter').removeAttribute('max');
      document.getElementById('downloadEndChapter').removeAttribute('max');
    }
    ```
- Em `startBatchDownload()`:
  - Validar contra `m.lastChapter`:
    ```javascript
    if (m.lastChapter != null && (start > m.lastChapter || end > m.lastChapter)) {
      alert(`O intervalo não pode ultrapassar o último episódio disponível (${m.lastChapter}).`);
      return;
    }
    ```

### 3.3 Mobile App Flutter (`mobile_app`)
- No widget `DownloadManhuaDialog`:
  - No `initState`:
    ```dart
    final last = widget.manhua.lastChapter;
    final endChap = (last != null)
        ? ((startChap + 4 > last) ? (startChap > last ? startChap : last) : startChap + 4)
        : startChap + 4;
    _endController = TextEditingController(text: endChap.toString());
    ```
  - Em `_startDownload`:
    ```dart
    if (widget.manhua.lastChapter != null) {
      final last = widget.manhua.lastChapter!;
      if (start > last || end > last) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('O intervalo não pode ultrapassar o último episódio disponível ($last).')),
        );
        return;
      }
    }
    ```
- No serviço `DownloadManager`:
  - Validação defensiva em `startDownload` para assegurar integridade caso chamado programaticamente.

## 4. Testes e Critérios de Aceite
- **Backend Tests:**
  - Teste na rota `/api/manhuas/<id>/batch-chapter-images` com parâmetros `end > lastChapter` retornando código 400.
  - Teste com parâmetros válidos `end <= lastChapter` funcionando normalmente.
- **Flutter Tests:**
  - Teste em `test/screens/download_manhua_dialog_test.dart` verificando que ao preencher um capítulo final superior a `lastChapter`, o SnackBar é exibido e nenhum download é iniciado.
- **Compilação Mobile:**
  - Geração dos pacotes APK (debug e release) atualizados.
