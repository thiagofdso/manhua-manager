# Design Specification: Embedded Reader (Iframe), Direct Reading, Eye View Button & Edit Modal

## 1. Overview
Esta especificação define o refinamento completo da experiência de leitura e gerenciamento do Manhua Manager:
1. **Leitura Embutida no Próprio App (Iframe / Embedded Viewer):** Clicar no card do manhua na lista principal (ou no botão de ler nos detalhes) abre uma tela de leitura dedicada dentro da própria aplicação (`#readerView`), exibindo a página do capítulo via `iframe` com barra superior de navegação (`← Voltar`, `◀ Anterior`, `Próximo ▶`, e `↗ Abrir no Navegador`).
2. **Botão Visualizar (👁️):** Um botão de ação dedicado no card que leva à visualização de detalhes e controles manuais da obra (`#detailView`).
3. **Modal de Edição (✏️):** Um botão de edição no card (e na tela de detalhes) que abre um modal (`#editModal`) permitindo alterar Nome, URL/Template e Capítulo da obra.
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
- **Tela 1: Lista Principal (`#listView`):**
  - Card com área clicável principal que abre o leitor embutido (`openReader(id)`).
  - Botão Visualizar (`class="action-btn"`) com ícone `👁️` chamando `selectManhua(id, event)`.
  - Botão Editar (`class="action-btn"`) com ícone `✏️` chamando `openEditModal(id, event)`.
- **Tela 2: Detalhes da Obra (`#detailView`):**
  - Controles de avançar/voltar e input manual.
  - Botão "📖 Ler Capítulo Atual" passa a invocar `openReader(selectedManhua.id)`.
  - Botão de edição rápido ✏️ no cabeçalho.
- **Tela 3: Leitor Embutido (`#readerView`):**
  - Barra superior fixa contendo:
    - Botão `← Voltar` (para voltar à lista ou aos detalhes).
    - Título e Capítulo Atual centralizados.
    - Botões rápidos `◀ Anterior` e `Próximo ▶` (atualiza o capítulo no backend e recarrega o iframe).
    - Botão `↗ Abrir Externo` (para abrir a URL em uma nova aba do navegador caso o site ative proteção contra frame como Cloudflare ou `X-Frame-Options: SAMEORIGIN`).
  - Quadro `iframe` ocupando `100vw` e altura total menos a barra superior.
- **Modal de Edição (`#editModal`):**
  - Backdrop escuro translúcido com painel centralizado.
  - Campos: Nome da Obra, URL / Template e Capítulo Atual.
  - Validação inteligente: se o usuário digitar uma URL contendo o capítulo, substitui automaticamente por `{chapter}`. Se já contiver `{chapter}`, aceita diretamente.
  - Botão Salvar (executa `PATCH` e recarrega dados) e Botão Cancelar.

## 3. Verification Plan
- **Backend Test:** Teste com `pytest` cobrindo o `PATCH` com `title`, `urlTemplate` e `chapter`.
- **Frontend Test:** Teste validando a presença dos botões `👁️`, `✏️`, do modal `#editModal` e da tela `#readerView` com seu `iframe`.
- **Systemd Restart:** Reiniciar o serviço `manhua-manager.service` via `systemctl --user restart manhua-manager` e verificar resposta HTTP 200.
