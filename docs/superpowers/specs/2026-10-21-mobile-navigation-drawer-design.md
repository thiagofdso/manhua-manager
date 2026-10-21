# Design: Mobile Navigation Drawer (Menu Sanduíche ☰)

## Contexto e Problema
Na tela inicial do aplicativo mobile (`HomeScreen`), o acúmulo de ícones na `AppBar` (`Downloads em Andamento`, `Editar Ordem`, `Configurações de IP`, `Atualizar Lista`) causou um erro de *overflow* horizontal de interface (`A OVERFLOWED BY 42 PIXELS`), prejudicando o título e os botões em telas de smartphone padrão.

## Solução Arquitetural
Substituir o excesso de ações na `AppBar` por um **Navigation Drawer** lateral (Menu Sanduíche ☰), centralizando navegação, status e configurações em um menu retrátil intuitivo e elegante, garantindo uma `AppBar` totalmente responsiva e desobstruída.

## Especificação dos Componentes

### 1. `AppDrawer` (`mobile_app/lib/screens/widgets/app_drawer.dart`)
Widget de Drawer que recebe/consome `ManhuaController`, `DownloadManager` e `DownloadService`:
- **Header:**
  - Ícone temático (`Icons.auto_stories`, cor `#8257E6`).
  - Título: **Manhua Manager**.
  - Subtítulo com status da conexão ou modo offline (`Modo Offline` ou `Conectado: <IP>`).
- **Seção de Downloads & Armazenamento:**
  - 📥 **Downloads em Andamento:** Abre `ActiveDownloadsDialog`. Exibe badge de contagem se houver downloads ativos.
  - 💾 **Armazenamento Offline:** Exibe o total de capítulos salvos no dispositivo e permite abrir diálogo para visualizar ou limpar o cache local.
- **Seção de Gerenciamento & Configurações:**
  - 🔀 **Organizar Obras:** Dispara o modo de reordenação (`_enterEditOrderMode`) na lista principal.
  - ⚙️ **Configurações:** Abre o diálogo de configuração do IP do backend (`SettingsDialog`).
  - 🔄 **Atualizar Lista:** Executa sincronização com o backend (`controller.loadManhuas()`).

### 2. `StorageManagementDialog` (`mobile_app/lib/screens/widgets/storage_management_dialog.dart`)
Diálogo simples e seguro para o gerenciamento do armazenamento local:
- Exibe o total de capítulos baixados.
- Botão "Excluir Todos os Downloads" com confirmação explícita.

### 3. Reformulação da `AppBar` na `HomeScreen`
- `leading`: Gerenciado nativamente pelo `Scaffold(drawer: AppDrawer(...))` com o ícone sanduíche ☰.
- `title`: `Text('Manhua Manager')` limpo e legível.
- `actions`:
  - Modo Edição de Ordem: Cancelar (✕) e Concluir (✓).
  - Modo Normal:
    - Se houver download em andamento: Badge discreto no ícone `Icons.downloading` para acompanhamento rápido.
    - Botão de atualização rápida (`Icons.refresh`).
  - Resultado: No máximo 2 ícones de ação na AppBar (largura consumida < 96px), eliminando completamente qualquer overflow.

### 4. Pull-to-Refresh (`RefreshIndicator`)
- Adicionado ao corpo da lista de obras na `HomeScreen` para permitir atualizar deslizando o dedo para baixo.

## Garantias e Regras
- Zero exclusão automática (capítulos e cache só são removidos sob ação explícita do usuário).
- Compatibilidade total com testes existentes e mocks de serviços.
