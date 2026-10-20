# Especificação de Design: Aplicativo Móvel Flutter para Android (Manhua Manager)

**Data:** 20/10/2026  
**Status:** Aprovado  
**Branch Alvo:** `feature/flutter-android-app`  

## 1. Visão Geral e Objetivos

Desenvolver um aplicativo móvel nativo em Flutter para Android no subdiretório `mobile_app/`, conectando-se ao backend Flask em execução (padrão via Tailscale IP `http://100.84.57.79:5000`), replicando todas as funcionalidades do frontend web atual com performance nativa e suporte a gestos móveis.

### Requisitos Principais:
1. **Configuração Dinâmica de Host:** Salvar o endereço do backend localmente via `shared_preferences`, com padrão `http://100.84.57.79:5000` e tela/diálogo de configuração para testes ou alteração de IP.
2. **Gerenciamento de Obras:**
   - Listagem completa com cards escuros temáticos, mostrando título e capítulo atual.
   - Botões de incremento/decremento rápido de capítulo (`+1` / `-1`).
   - Adição de nova obra com conversão inteligente de URL para `{chapter}` template.
   - Edição de obras existentes e exclusão com diálogo de confirmação.
3. **Leitor Nativo Contínuo (Webtoon Style):**
   - Extração automática de páginas via `GET /api/chapter-images?url=...`.
   - Renderização vertical contínua das imagens via proxy `GET /api/proxy-image?url=...` para evitar bloqueios de CDN / hotlinking.
   - **Navegação por Gesto:** Suporte a gesto de arrastar/deslizar horizontalmente (swipe) para trocar de capítulo (swipe da direita para a esquerda: próximo capítulo; swipe da esquerda para a direita: capítulo anterior).
   - Botões de navegação na barra inferior para controle alternativo por clique.
4. **Build Android:**
   - Configuração de manifesto Android com permissão de internet.
   - Configuração do pipeline de compilação para gerar o pacote APK para Android.

---

## 2. Arquitetura e Estrutura de Código

### 2.1 Estrutura de Diretórios (`mobile_app/`)

```text
mobile_app/
├── android/
│   ├── app/
│   │   ├── build.gradle
│   │   └── src/main/AndroidManifest.xml
│   ├── build.gradle
│   └── settings.gradle
├── lib/
│   ├── models/
│   │   └── manhua.dart
│   ├── services/
│   │   ├── api_service.dart
│   │   └── storage_service.dart
│   ├── controllers/
│   │   └── manhua_controller.dart
│   ├── screens/
│   │   ├── home_screen.dart
│   │   ├── reader_screen.dart
│   │   └── widgets/
│   │       ├── add_manhua_dialog.dart
│   │       ├── edit_manhua_dialog.dart
│   │       └── settings_dialog.dart
│   └── main.dart
├── test/
│   ├── models/manhua_test.dart
│   ├── services/api_service_test.dart
│   └── widget_test.dart
└── pubspec.yaml
```

### 2.2 Modelos e Serviços

- **`Manhua` (`models/manhua.dart`):**
  - Campos: `int id`, `String title`, `String urlTemplate`, `int currentChapter`, `int? updatedAt`.
  - Métodos: `fromJson(Map<String, dynamic> json)`, `toJson()`, `targetUrlForChapter(int chapter)`.
- **`StorageService` (`services/storage_service.dart`):**
  - Armazena `backend_url` com fallback para `http://100.84.57.79:5000`.
- **`ApiService` (`services/api_service.dart`):**
  - `Future<List<Manhua>> fetchManhuas()` -> `GET /api/manhuas`
  - `Future<Manhua> addManhua(String title, String urlTemplate, int currentChapter)` -> `POST /api/manhuas`
  - `Future<Manhua> updateChapterDelta(int id, int delta)` -> `PATCH /api/manhuas/{id}` com `{"delta": delta}`
  - `Future<Manhua> updateManhua(int id, {String? title, String? urlTemplate, int? chapter})` -> `PATCH /api/manhuas/{id}`
  - `Future<void> deleteManhua(int id)` -> `DELETE /api/manhuas/{id}`
  - `Future<List<String>> fetchChapterImages(String targetUrl)` -> `GET /api/chapter-images?url=...`
  - `String getProxyImageUrl(String imageUrl)` -> `$baseUrl/api/proxy-image?url=$imageUrl`
- **`ManhuaController` (`controllers/manhua_controller.dart`):**
  - `ChangeNotifier` gerenciando lista de obras, carregamento, erros e seleção ativa.

---

## 3. Experiência de Uso e Gestos no Leitor

- **Leitor Contínuo (`ReaderScreen`):**
  - `GestureDetector(onHorizontalDragEnd: (details) { ... })`
  - Se `details.primaryVelocity < -300`: Avança para o próximo capítulo.
  - Se `details.primaryVelocity > 300`: Retorna ao capítulo anterior.
  - Rolagem vertical fluida sem conflito através de `ListView.builder`.
  - Barra superior recolhível exibindo `<Título> <Capítulo>`.
  - Barra inferior fixa ou retrátil com botões `◀ Anterior` e `Próximo ▶`.

---

## 4. Estratégia de Testes

1. **Testes Unitários:**
   - Deserialização e serialização de `Manhua`.
   - Interpolação de `{chapter}` na URL.
   - Mock de `ApiService` com `http.ClientMock` para validar todas as rotas REST.
2. **Testes de Integração e Widgets:**
   - Teste de renderização da `HomeScreen` e navegação para `ReaderScreen`.
   - Teste do gesto de swipe para troca de capítulos.
3. **Validação:**
   - Execução de `flutter test`.
