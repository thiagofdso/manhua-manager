# Design Specification: Direct Reading, Eye View Button & Edit Modal

## 1. Overview
Esta especificação define o refinamento de experiência de uso do Manhua Manager:
1. **Leitura Imediata ao Clicar:** Clicar no título/card do manhua na lista principal abre diretamente a URL do capítulo atual em uma nova aba do navegador (`target="_blank"`).
2. **Botão Visualizar (👁️):** Um botão de ação dedicado no card que leva à visualização de detalhes e controles incrementais da obra.
3. **Modal de Edição (✏️):** Um botão de edição no card (e na tela de detalhes) que abre um modal permitindo alterar Nome, URL/Template e Capítulo da obra.
4. **Backend Patch Flexível:** Suporte no endpoint `PATCH /api/manhuas/<id>` para alterar simultaneamente título, `urlTemplate` e capítulo atual.

## 2. Requirements & Changes

### 2.1 Backend Changes (`server.py`)
- Rota `PATCH /api/manhuas/<int:item_id>` deve aceitar:
  - `title`: string não vazia (opcional)
  - `urlTemplate`: string não vazia (opcional)
  - `chapter`: inteiro >= 1 (opcional)
  - `delta`: inteiro (+1, -1, etc.) (opcional)
- Atualizar `updatedAt` para o timestamp atual a cada alteração.
- Salvar persistência em `database.json`.

### 2.2 Frontend SPA Changes (`index.html`)
- **Card do Manhua na Lista:**
  - Área principal como link clicável `<a>` ou `div` com cursor pointer que dispara `window.open(url, '_blank')`.
  - Botão Visualizar (`class="action-btn"`) com ícone `👁️` chamando `selectManhua(id, event)`.
  - Botão Editar (`class="action-btn"`) com ícone `✏️` chamando `openEditModal(id, event)`.
- **Modal de Edição (`#editModal`):**
  - Backdrop escuro translúcido com painel centralizado.
  - Campos: Nome da Obra, URL / Template e Capítulo Atual.
  - Validação inteligente: se o usuário digitar uma URL contendo o capítulo, substitui automaticamente por `{chapter}`. Se já contiver `{chapter}`, aceita diretamente.
  - Botão Salvar (executa `PATCH` e recarrega dados) e Botão Cancelar.
- **Tela de Detalhes (`#detailView`):**
  - Adicionar botão de edição rápido também no cabeçalho ou nas ações da obra.

## 3. Verification Plan
- **Backend Test:** Teste com `pytest` cobrindo o `PATCH` com `title`, `urlTemplate` e `chapter`.
- **Frontend Test:** Teste validando a presença dos botões `👁️`, `✏️` e da estrutura do modal `#editModal`.
- **Systemd Restart:** Reiniciar o serviço `manhua-manager.service` via `systemctl --user restart manhua-manager` e verificar resposta HTTP 200.
