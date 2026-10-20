# Especificação de Design: Título Dinâmico da Página (Nome do Manhua e Capítulo)

**Data:** 19/10/2026  
**Status:** Aprovado  
**Branch Alvo:** `feature/dynamic-page-title`  

## 1. Visão Geral

Permitir que a aba do navegador exiba dinamicamente o nome da obra e o número do capítulo atual durante a leitura e visualização de detalhes, retornando ao título padrão do aplicativo quando o usuário estiver na lista principal de manhuas.

Formato solicitado pelo usuário:
- Durante a leitura / detalhes: `<Título da Obra> <Capítulo>` (exemplo: `Overgeared 199`).
- Na lista principal / fechamento do leitor: `Manhua Tracker`.

---

## 2. Arquitetura e Alterações em `index.html`

No frontend (`index.html`):

1. **Leitor Nativo Contínuo:**
   - Na função `updateReaderHeader()` (chamada em `loadChapterPages()`):
     ```javascript
     document.title = `${readerManhua.title} ${readerManhua.currentChapter}`;
     ```
   - Ao fechar o leitor (`closeReader()`):
     - Se `previousView` for `detailView` e `selectedManhua` existir: restaura o título da obra selecionada.
     - Se retornar à lista (`listView`):
       ```javascript
       document.title = 'Manhua Tracker';
       ```

2. **Tela de Detalhes:**
   - Na função `renderDetails()`:
     ```javascript
     document.title = `${selectedManhua.title} ${selectedManhua.currentChapter}`;
     ```
   - Na função `showListView()`:
     ```javascript
     document.title = 'Manhua Tracker';
     ```

---

## 3. Estratégia de Testes

- Atualizar e expandir a suíte de testes do frontend em `tests/test_pwa_assets.py`:
  - Verificar se `index.html` inclui a lógica de atribuição de `document.title` tanto em `updateReaderHeader`, `renderDetails`, `closeReader` e `showListView`.
  - Garantir que o formato literal `${readerManhua.title} ${readerManhua.currentChapter}` e `'Manhua Tracker'` estejam presentes.
