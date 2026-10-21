# Design: Favoritos e Reordenação Manual de Obras (Web & Mobile)

**Data:** 21/10/2026  
**Status:** Aprovado  
**Escopo:** Backend Flask (`server.py`), Interface Web (`index.html`), Aplicativo Móvel Flutter (`mobile_app/`).

---

## 1. Contexto e Objetivos

O **Manhua Manager** gerencia uma lista de manhuas/mangás e atualmente armazena os registros em `database.json`, ordenando-os exclusivamente por `updatedAt DESC` (data da última leitura/atualização).

Este design introduz duas funcionalidades integradas para as versões Web e Mobile:
1. **Favoritar Obras (Ícone de Estrela):** O usuário pode favoritar uma ou mais obras. Obras favoritas são exibidas estritamente no topo da lista.
2. **Reordenação Manual:** O usuário pode reordenar a lista manualmente.
   - **Regra de Ouro Inviolável:** Uma obra favorita **nunca** poderá ficar abaixo de uma obra não-favorita.
   - **Ordenação Híbrida ao Atualizar Capítulos:** Ao ler ou alterar o capítulo de uma obra, ela sobe para o topo do seu respectivo grupo (se favorita, vai para o topo das favoritas; se não-favorita, vai para o topo das não-favoritas).

---

## 2. Modelo de Dados (`database.json`)

Cada item manhua receberá dois novos campos:
```json
{
  "id": 1792485389283,
  "title": "The extras academy survival guide",
  "urlTemplate": "https://asurascans.com/comics/.../chapter/{chapter}",
  "currentChapter": 74,
  "updatedAt": 1792485439,
  "isFavorite": true,
  "customOrder": 0
}
```

- `isFavorite` (*bool*, default `false`): Indica se a obra está favoritada.
- `customOrder` (*int*, default calculado sequencialmente): Define a posição relativa da obra dentro do seu grupo.

### Regra de Ordenação Central
A ordenação padrão aplicada pelo backend e replicada nos clientes é:
1. `isFavorite DESC` (true primeiro, false depois).
2. `customOrder ASC` (menor valor indica posição superior).
3. `updatedAt DESC` (desempate mantendo o item mais recente no topo).

---

## 3. Backend API (`server.py`)

### 3.1 `GET /api/manhuas`
- Carrega as obras de `database.json`.
- Garante valores default para itens legados (`isFavorite: false`, `customOrder: 0`).
- Aplica a ordenação: `(not isFavorite, customOrder, -updatedAt)`.
- Retorna o array JSON ordenado.

### 3.2 `PATCH /api/manhuas/<int:item_id>`
- **Favoritar/Desfavoritar (`isFavorite: bool` no payload):**
  - Se `isFavorite == True`:
    - Define `isFavorite = True`.
    - Ajusta `customOrder` para o menor valor entre as obras favoritas existentes menos 1 (ou `0`), colocando-a no topo das favoritas.
  - Se `isFavorite == False`:
    - Define `isFavorite = False`.
    - Ajusta `customOrder` para o menor valor entre as obras não-favoritas existentes menos 1 (ou `0`), colocando-a no topo das não-favoritas.
- **Atualização de Capítulo (`chapter` ou `delta` no payload):**
  - Atualiza o capítulo e `updatedAt = int(time.time())`.
  - **Regra Híbrida:** Calcula o menor `customOrder` entre as obras do mesmo status de `isFavorite` e atribui `min_order - 1` à obra atual, promovendo-a ao topo do seu grupo.
- Persiste em `database.json` e retorna o item atualizado.

### 3.3 `PUT /api/manhuas/reorder`
- **Payload:** `{"order": [id1, id2, id3, ...]}`
- **Validação de Integridade:**
  - O backend verifica a lista de IDs: todas as obras com `isFavorite == True` devem aparecer antes de qualquer obra com `isFavorite == False`.
  - Se a ordem violar a restrição, o backend reajusta automaticamente agrupando todas as favoritas no início (preservando a ordem relativa desejada de cada subgrupo).
- Reatribui `customOrder = 0, 1, 2, ...` sequencialmente para cada item da lista informada.
- Salva `database.json` e retorna `{"status": "ok", "items": [...]}`.

---

## 4. Interface Web (`index.html`)

### 4.1 Ícone de Estrela
- No início de cada card de manhua (lado esquerdo do título):
  - Botão com ícone de estrela: `★` (dourado `#f59e0b`) se favoritado, `☆` (cinza `#71717a`) se não favoritado.
  - Tooltip: *"Favoritar obra"* / *"Remover dos favoritos"*.
  - Clique imediato faz `PATCH /api/manhuas/<id>` com `{ isFavorite: !m.isFavorite }` e re-renderiza com animação sutil.

### 4.2 Divisores de Seção
- Se houver pelo menos uma obra favorita, a lista exibe cabeçalhos de seção estilizados:
  - `★ Obras Favoritas (N)`
  - `Todas as Obras (M)`

### 4.3 Modo de Mover em Dois Cliques (Seleção Inline)
- Cada card exibe um botão de ação `↕` (*"Mover posição"*).
- **Ao clicar em `↕` em um item `A`:**
  - Aplicação entra em estado `movingManhuaId = A.id`.
  - Banner no topo da lista:
    - *"Movendo: [Título] • Escolha a nova posição abaixo ou [Cancelar (Esc)]"*
  - O card selecionado recebe classe `.moving-active`:
    - Borda destacada em roxo primário (`#8257e6`), sombra suave (*glow*) e badge *"Posição atual"*.
  - **Restrição Estrita nos Marcadores de Destino:**
    - Se `A` for favorita: Marcadores de destino `[+ Mover para cá]` só aparecem dentro da seção de Favoritas (no topo das favoritas, entre favoritas e no fim das favoritas).
    - Se `A` for não-favorita: Marcadores de destino só aparecem dentro da seção de Não-Favoritas.
  - **Design do Marcador de Destino:**
    - Linha com botão sutil `[+ Inserir aqui]` com animação ao expandir.
  - **Ao clicar no marcador:**
    - Calcula o novo array de IDs com `A` inserido na posição escolhida.
    - Dispara `PUT /api/manhuas/reorder`.
    - Finaliza o modo mover e atualiza a interface.
  - Tecla `Esc` ou botão "Cancelar" encerra o modo sem salvar.

---

## 5. Aplicativo Mobile Flutter (`mobile_app/`)

### 5.1 Atualizações no Modelo e Serviços
- **`Manhua` (`models/manhua.dart`):**
  - Adiciona `final bool isFavorite;` (default `false`).
  - Adiciona `final int? customOrder;`.
  - Atualiza `fromJson`, `toJson`, `copyWith`.
- **`ApiService` (`services/api_service.dart`):**
  - `toggleFavorite(int id, bool isFavorite)` -> `PATCH /api/manhuas/<id>` com `{"isFavorite": isFavorite}`.
  - `reorderManhuas(List<int> orderedIds)` -> `PUT /api/manhuas/reorder` com `{"order": orderedIds}`.
- **`ManhuaController` (`controllers/manhua_controller.dart`):**
  - `Future<void> toggleFavorite(int id)`: Atualiza status otimista/reativo e sincroniza.
  - `Future<void> saveReorder(List<int> orderedIds)`: Envia reordenação e atualiza lista.

### 5.2 Telas e Interações (`HomeScreen`)
- **Modo Normal:**
  - Cada card exibe um `IconButton` com estrela à esquerda:
    - `Icons.star` (cor `#F59E0B`) para favoritas.
    - `Icons.star_border` (cinza) para não-favoritas.
  - No `AppBar`:
    - Ação `IconButton(icon: Icon(Icons.sort_rounded), tooltip: 'Editar Ordem da Lista')` para ativar o modo de edição.
- **Modo "Editar Ordem":**
  - O `AppBar` muda para o modo de edição:
    - Título: *"Editar Ordem"*.
    - Botão `IconButton(icon: Icon(Icons.close), tooltip: 'Cancelar')`.
    - Botão `IconButton(icon: Icon(Icons.check), tooltip: 'Concluir')`.
  - O `FloatingActionButton` de adicionar obra é ocultado.
  - **Seções Separadas e Segregadas (`ReorderableListView`):**
    - Seção 1: *"★ Favoritas"* (se houver favoritas):
      - Lista `ReorderableListView` contendo apenas as obras favoritas.
      - Cada card exibe o título, capítulo e o ícone de arraste (`Icons.drag_handle_rounded`).
    - Seção 2: *"Demais Obras"*:
      - Lista `ReorderableListView` contendo apenas as obras não-favoritas.
      - Cada card exibe o título, capítulo e o ícone de arraste (`Icons.drag_handle_rounded`).
    - **Garantia Nativa da Regra:** Como cada seção possui seu próprio `ReorderableListView`, o usuário nunca consegue arrastar uma obra favorita para dentro do bloco das não-favoritas nem vice-versa.
  - **Salvar:**
    - Ao tocar em `✓` (Concluir), combina `[...favoritasIds, ...demaisIds]` e chama `controller.saveReorder(...)`.
    - Retorna ao modo normal e exibe um `SnackBar` com confirmação.

---

## 6. Testes e Verificação

1. **Testes Unitários Backend (`tests/test_server.py`):**
   - Testar listagem padrão com ordenação `(isFavorite DESC, customOrder ASC)`.
   - Testar endpoint `PATCH /api/manhuas/<id>` com `isFavorite: true` e `false`.
   - Testar promoção para o topo do grupo ao alterar capítulo (`delta` e `chapter`).
   - Testar endpoint `PUT /api/manhuas/reorder` com reordenação válida.
   - Testar autocorreção caso a ordem enviada tente colocar não-favorita antes de favorita.
2. **Testes Mobile (`mobile_app/test/`):**
   - Testes de modelo (`Manhua.fromJson` com e sem `isFavorite`/`customOrder`).
   - Testes de controle e serviço para toggle e reorder.
3. **Verificação Manual e E2E:**
   - Testar no navegador Web desktop e mobile.
   - Testar compilação/análise do Flutter (`flutter analyze` / `flutter test`).
