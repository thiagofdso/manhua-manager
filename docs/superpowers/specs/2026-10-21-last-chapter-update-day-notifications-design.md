# Design: Último Episódio, Dia de Atualização, Rotina 23:50 e Notificações (Web & Mobile)

**Data:** 21/10/2026  
**Status:** Aprovado  
**Escopo:** Backend Flask (`server.py`), Interface Web (`index.html`), Aplicativo Móvel Flutter (`mobile_app/`).

---

## 1. Contexto e Objetivos

O **Manhua Manager** permite acompanhar o progresso de leitura de mangás/manhuas de múltiplos agregadores na Web e no Mobile (Flutter).

Este design introduz as seguintes capacidades:
1. **Novos Campos por Obra:**
   - **Último Episódio (`lastChapter`):** Número do último episódio lançado no agregador.
   - **Dia de Atualização (`updateDay`):** Dia da semana em que novos episódios costumam ser disponibilizados (Seg, Ter, Qua, Qui, Sex, Sáb, Dom).
   - **Hiato (`isHiatus`):** Checkbox indicando se a obra está temporariamente suspensa/interrompida.
2. **Controle de Visualização e Bloqueio de Navegação:**
   - Quando `lastChapter` estiver definido, impedir o usuário de avançar para episódios inexistentes na interface Web e Mobile (botão próximo desabilitado, avanço manual validado, gestos de swipe bloqueados).
   - Se `lastChapter` não estiver definido, nenhum controle ou restrição é imposto.
   - Suporte ao modo offline do mobile: o valor de `lastChapter` deve persistir localmente e continuar protegendo a navegação.
3. **Rotina Agendada Noturna (23:50) e Disparo Manual:**
   - Executada diariamente às 23:50 no backend (e acionável sob demanda pelo usuário na Web e no Mobile).
   - Analisa todas as obras que possuem `lastChapter` e `updateDay` preenchidos, não estão em hiato (`isHiatus == false`) e cujo `updateDay` coincide com o dia atual.
   - Para cada uma, tenta obter imagens do episódio `lastChapter + 1`. Havendo imagens válidas, atualiza `lastChapter = lastChapter + 1` e emite uma notificação.
4. **Sistema de Notificações Unificado:**
   - Compartilhado entre Web e Mobile com sincronização via backend.
   - Ao ser visualizada/descartada, a notificação é removida da lista.

---

## 2. Modelo de Dados

### 2.1 Modelo da Obra (`database.json`)
Cada obra no array recebe os novos campos:
```json
{
  "id": 1,
  "title": "Overgeared",
  "urlTemplate": "https://asurascans.com/comics/overgeared-11fe7da3/chapter/{chapter}",
  "currentChapter": 243,
  "lastChapter": 244,
  "updateDay": 4,
  "isHiatus": false,
  "updatedAt": 1792623272,
  "customOrder": -1,
  "isFavorite": true
}
```

- `lastChapter` (*int?*, opcional): Número inteiro `>= 1` indicando o último episódio lançado. `null` indica sem limite.
- `updateDay` (*int?*, opcional): Inteiro de `0` a `6` representando o dia da semana:
  - `0`: Segunda-feira
  - `1`: Terça-feira
  - `2`: Quarta-feira
  - `3`: Quinta-feira
  - `4`: Sexta-feira
  - `5`: Sábado
  - `6`: Domingo
  - `null`: Nenhum dia definido.
- `isHiatus` (*bool*, padrão `false`): Booleano indicando pausa na serialização da obra.

### 2.2 Modelo de Notificações (`notifications.json`)
Armazenado em arquivo dedicado na raiz do projeto (`notifications.json`):
```json
[
  {
    "id": 1792623272000,
    "manhuaId": 1,
    "title": "Overgeared",
    "chapter": 244,
    "message": "Novo episódio 244 de Overgeared disponível!",
    "createdAt": 1792623272
  }
]
```

### 2.3 Modelo Flutter (`mobile_app/lib/models/manhua.dart`)
- Campos adicionados:
  - `final int? lastChapter;`
  - `final int? updateDay;`
  - `final bool isHiatus;`
- Atualizados construtor com valores default, `fromJson()`, `toJson()` e `copyWith()`.
- Persistência offline garantida via `StorageService` (`saveCachedManhuas` e `getCachedManhuas`).

---

## 3. Backend e Rotina Diária (`server.py`)

### 3.1 Endpoints da API

#### `POST /api/manhuas` & `PATCH /api/manhuas/<int:item_id>`
- Aceitam `lastChapter`, `updateDay` e `isHiatus`.
- Validações:
  - `lastChapter`: inteiro `>= 1` ou `null`.
  - `updateDay`: inteiro `0..6` ou `null`.
  - `isHiatus`: booleano.
- Ao atualizar, persiste em `database.json`.

#### `GET /api/notifications`
- Retorna a lista de notificações armazenadas em `notifications.json`.

#### `DELETE /api/notifications/<int:notification_id>`
- Remove a notificação correspondente pelo `id`.
- Retorna `{"status": "ok"}`.

#### `DELETE /api/notifications` (ou `POST /api/notifications/clear`)
- Remove todas as notificações.
- Retorna `{"status": "ok"}`.

#### `POST /api/routine/run-check`
- Executa a verificação imediatamente (para checagem manual via interface e testes).
- Parâmetro opcional `checkAll=true` (permite forçar verificação de todas as obras ativas com `lastChapter` preenchido, independentemente do dia). Por padrão, verifica as obras do dia da semana atual.
- Retorna:
  ```json
  {
    "status": "ok",
    "checkedCount": 3,
    "newChaptersFound": 1,
    "results": [
      {"id": 1, "title": "Overgeared", "newChapter": 245, "status": "updated"}
    ]
  }
  ```

### 3.2 Lógica da Rotina Agendada (23:50)
- Inicia uma *daemon thread* ao iniciar o `server.py`.
- A cada 30 segundos, verifica `datetime.now()`.
- Se `now.hour == 23` e `now.minute == 50` e a rotina ainda não foi executada no dia atual (`last_run_date != today_str`):
  1. Marca `last_run_date = today_str`.
  2. Determina o dia da semana atual (`now.weekday()`, onde Segunda = 0 ... Domingo = 6).
  3. Filtra obras elegíveis:
     - `not obra.get("isHiatus", False)`
     - `obra.get("lastChapter") is not None`
     - `obra.get("updateDay") == current_weekday`
  4. Para cada obra:
     - `target_chapter = obra["lastChapter"] + 1`
     - `target_url = obra["urlTemplate"].replace("{chapter}", str(target_chapter))`
     - Executa `extract_images_from_url(target_url)` protegida em `try/except`.
     - Se `len(images) > 0`:
       - `obra["lastChapter"] = target_chapter`
       - `obra["updatedAt"] = int(time.time())`
       - Adiciona registro em `notifications.json`.
  5. Salva `database.json` e `notifications.json`.

---

## 4. Interface Web (`index.html`)

### 4.1 Formulários (Adicionar e Editar)
- **Seleção de Dia da Semana:**
  - Grupo de 7 botões compactos: `[Seg] [Ter] [Qua] [Qui] [Sex] [Sáb] [Dom]`.
  - Clique único seleciona; clique no ativo desseleciona (valor `null`).
- **Input de Último Episódio:**
  - Campo numérico `"Último Episódio Lançado (opcional)"`.
- **Checkbox de Hiato:**
  - `"Obra em Hiato"` com legenda explicativa.

### 4.2 Card da Obra na Lista Principal
- Badges informativos:
  - Dia da semana: ex. `<span class="badge">Qua</span>`.
  - Hiato: ex. `<span class="badge" style="background:#ef4444">Hiato</span>`.
  - Progresso de episódios: `Capítulo 243 / 244`.

### 4.3 Bloqueio de Navegação além do Último Episódio
- Quando `lastChapter` estiver definido:
  - Botão de avanço rápido no item/card fica desabilitado se `currentChapter >= lastChapter`.
  - Na tela de detalhes: botão `Próximo ▶` desabilitado quando `currentChapter >= lastChapter`. Campo de definir capítulo manual bloqueia valores `> lastChapter`.
  - No leitor contínuo (`readerView`): botão `▶` desabilitado, atalho de teclado `ArrowRight` bloqueado quando `currentChapter >= lastChapter`.
- Se `lastChapter` não estiver definido, navegação permanece sem limites.

### 4.4 Central de Notificações
- Ícone de sino `🔔` no cabeçalho com indicador numérico de notificações não lidas.
- Modal/Dropdown de notificações listando obras com novos episódios.
- Ao clicar em uma notificação:
  - Abre a obra correspondente.
  - Remove a notificação via API (`DELETE /api/notifications/<id>`).
- Botão `"Limpar todas"` (`DELETE /api/notifications`).
- Botão `"Verificar Atualizações Agora"` (`POST /api/routine/run-check`) com feedback visual de carregamento e resultado.

---

## 5. Aplicativo Móvel (`mobile_app/`)

### 5.1 Diálogos de Cadastro e Edição (`AddManhuaDialog` e `EditManhuaDialog`)
- Seletor de botões `SegmentedButton` ou `Row` de `ChoiceChip` para os 7 dias da semana (`Seg`, `Ter`, `Qua`, `Qui`, `Sex`, `Sáb`, `Dom`).
- Campo numérico `TextFormField` para `Último Episódio`.
- `CheckboxListTile` ou `SwitchListTile` para `Obra em Hiato`.

### 5.2 Bloqueio de Navegação (`HomeScreen` e `ReaderScreen`)
- **`HomeScreen`:**
  - Botão `+1` desabilitado (`onPressed: null`) quando `lastChapter != null && currentChapter >= lastChapter`.
  - Exibição de chips de dia da semana, badge de hiato e indicação de `Capítulo X / Y`.
- **`ReaderScreen`:**
  - Botão `Próximo` na barra inferior desabilitado quando `currentChapter >= lastChapter`.
  - No gesto de swipe (`onHorizontalDragEnd`), se `velocity < -300` e `currentChapter >= lastChapter`, bloqueia o avanço e exibe `SnackBar('Você já está no último episódio disponível ($lastChapter).')`.
- **Modo Offline:**
  - Persiste via `StorageService`. O leitor e a tela inicial respeitam o limite de capítulos mesmo desconectado.

### 5.3 Notificações no Mobile
- Ícone de sino com `Badge` na `AppBar` da `HomeScreen`.
- Ao tocar no sino, abre um `showModalBottomSheet` com a lista de notificações ativas:
  - Card para cada notificação com título, novo capítulo e botão descartar `IconButton(Icons.close)`.
  - Tocar na notificação: abre o leitor na obra e descarta a notificação.
  - Botão `"Limpar todas"`.
  - Botão `"Verificar Atualizações Agora"` chamando `POST /api/routine/run-check`.

---

## 6. Estratégia de Testes

### 6.1 Testes Backend (`pytest tests/`)
- Testes unitários para criação/edição com `lastChapter`, `updateDay` e `isHiatus`.
- Testes para persistência, recuperação e exclusão de notificações (`GET`, `DELETE`, `clear`).
- Teste unitário da função `run_daily_update_check()`:
  - Mock de `datetime.now()` para dia específico.
  - Mock de `extract_images_from_url` para simular retorno com sucesso (novo capítulo) e falha (sem novo capítulo).
  - Verificação de incremento de `lastChapter` e geração de notificação.
  - Verificação de que obras em hiato ou com dia divergente são ignoradas.

### 6.2 Testes Mobile (`flutter test`)
- Testes unitários de serialização `Manhua.fromJson` e `Manhua.toJson` com os novos campos.
- Testes de widget no `HomeScreen` validando desativação do botão `+1` quando `currentChapter >= lastChapter`.
- Testes de widget no `ReaderScreen` validando desativação do botão `Próximo` e bloqueio de swipe.
