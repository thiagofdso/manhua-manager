# Implementation Plan: Mobile Navigation Drawer (Menu Sanduíche ☰)

## Overview
Implementar o Menu Sanduíche lateral (`Drawer`) no Flutter para eliminar o overflow horizontal na `AppBar` da `HomeScreen`, organizando downloads ativos, armazenamento offline, ordenação de lista, configurações de IP e sincronização.

## Proposed Changes

### Task 1: Componente `StorageManagementDialog` e Testes
- Arquivos:
  - Criar: `mobile_app/lib/screens/widgets/storage_management_dialog.dart`
  - Testar: `mobile_app/test/screens/storage_management_dialog_test.dart`
- Responsabilidades:
  - Exibir contagem de capítulos salvos no dispositivo.
  - Fornecer opção de limpeza de downloads com modal de confirmação.

### Task 2: Componente `AppDrawer` e Testes
- Arquivos:
  - Criar: `mobile_app/lib/screens/widgets/app_drawer.dart`
  - Testar: `mobile_app/test/screens/app_drawer_test.dart`
- Responsabilidades:
  - Itens: Downloads em Andamento, Armazenamento Offline, Organizar Obras, Configurações, Atualizar Lista.
  - Indicadores e badges de status.

### Task 3: Integração do `AppDrawer` na `HomeScreen` e Ajuste da `AppBar`
- Arquivos:
  - Modificar: `mobile_app/lib/screens/home_screen.dart`
  - Atualizar testes: `mobile_app/test/home_screen_reorder_test.dart`, `mobile_app/test/widget_test.dart`
- Responsabilidades:
  - Adicionar `drawer: AppDrawer(...)` no `Scaffold`.
  - Simplificar ações da `AppBar` para no máximo 2 ícones (Downloads com badge se ativo + Atualizar).
  - Adicionar `RefreshIndicator` para pull-to-refresh na lista.

### Task 4: Validação Geral e Geração dos APKs
- Responsabilidades:
  - Executar suíte de testes backend: `./.venv/bin/pytest tests/`
  - Executar suíte de testes mobile: `cd mobile_app && /home/thiagofdso/development/flutter/bin/flutter test`
  - Recompilar APK release e debug:
    - `flutter build apk --release`
    - `flutter build apk --debug`
  - Merge para `master` e entrega ao usuário.
