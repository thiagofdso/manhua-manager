# Especificação Técnica: Coleta de Métricas e Telemetria Local

## 1. Visão Geral e Objetivos

O objetivo desta especificação é definir a implementação da Fase 1 da observabilidade no backend do `manhua-manager`, conforme descrito em [`observabilidade.md`](file:///home/thiagofdso/Projetos/manhua-manager/observabilidade.md).

Esta primeira fase foca em uma solução de **histórico local estruturado e de baixo overhead**, sem dependência de Docker ou serviços externos como Prometheus/Grafana. A telemetria coletará dados de latência, vazão, I/O, falhas e consumo de recursos de hardware de forma reproduzível para estabelecer a linha de base (*baseline*) do backend Python atual.

---

## 2. Contrato de Eventos (Schema Version 1)

Todos os eventos gerados pela instrumentação seguirão o formato JSON especificado abaixo, gravados como JSONL com campos estritos e de baixa cardinalidade em rotas:

```json
{
  "schema_version": 1,
  "timestamp": "2026-10-23T05:07:45.123456Z",
  "service": "manhua-manager-backend",
  "implementation": "python",
  "revision": "e3a89f1",
  "request_id": "req-9f3b12",
  "span_id": "span-41a2c3",
  "parent_span_id": null,
  "operation": "http.server.request",
  "route": "/api/manhuas/<int:item_id>",
  "domain": null,
  "duration_ms": 12.45,
  "outcome": "success",
  "cache_state": "not_applicable",
  "http_status": 200,
  "upstream_status": null,
  "error_type": null,
  "bytes_received": 1420,
  "image_count": null,
  "benchmark_run_id": null
}
```

### 2.1 Regras do Contrato:
- **`timestamp`**: Horário UTC em formato ISO 8601 com fuso explícito (`Z`).
- **`duration_ms`**: Float em milissegundos calculado estritamente via `time.perf_counter_ns() / 1_000_000`.
- **`route`**: Rota parametrizada obtida de `request.url_rule.rule` no Flask (ex: `/api/manhuas/<int:item_id>`), evitando a inclusão de parâmetros dinâmicos para prevenir explosão de cardinalidade.
- **`outcome`**: Valores possíveis: `success`, `partial`, `error`, `timeout`, `cancelled`.
- **`cache_state`**: Valores possíveis: `hit`, `miss`, `stale_fallback`, `bypass`, `not_applicable`.
- **`revision`**: Hash curto do commit Git atual (`git rev-parse --short HEAD`), armazenado na inicialização do serviço.

---

## 3. Arquitetura e Componentes

### 3.1 Estrutura de Diretórios
Os artefatos de telemetria ficarão contidos na pasta `telemetry/`, ignorada no Git (com exceção do diretório e seus arquivos de configuração/código):

```text
telemetry/
├── events/                 # Arquivos JSONL ativos rotacionados diariamente
│   └── events-YYYY-MM-DD.jsonl
├── runs/                   # Diretórios com artefatos de benchmarks controlados
│   └── <run-id>/
│       ├── manifest.json
│       ├── samples.jsonl
│       ├── resources.jsonl
│       └── summary.json
├── backups/                # Backups locais de integridade do SQLite
├── benchmarks.sqlite3      # Banco SQLite histórico
└── requirements-observability.txt # Dependências fixadas (psutil, httpx)
```

### 3.2 Módulo `telemetry.py`
Módulo responsável por gerenciar o ciclo de vida dos spans, filas e persistência de eventos:

1. **Contexto e Rastreamento (`TelemetryContext` e `span`):**
   - Utiliza `contextvars` para manter a pilha de spans ativos e `request_id` isolados por thread/requisição.
   - Fornece o context manager `telemetry.span(operation, route=None, domain=None, **kwargs)`.
   - Fecha a contagem de tempo sempre em bloco `finally`.
   - Em caso de exceção, anota `outcome="error"` e `error_type=exc.__class__.__name__`, e re-emite a exceção sem engoli-la.
2. **Buffer Assíncrono (`EventQueue`):**
   - Fila em memória `queue.Queue(maxsize=10000)`.
   - Inserções via `put_nowait()`. Em caso de fila saturada (`queue.Full`), incrementa o contador atômico `dropped_events_count` e descarta o evento sem lançar exceção.
3. **Worker Thread e Rotação:**
   - Thread daemon responsável por consumir a fila em lotes de até 100 eventos ou a cada 250ms.
   - Grava em modo append no arquivo `telemetry/events/events-YYYY-MM-DD.jsonl`.
   - Cria o arquivo do novo dia automaticamente na mudança de data UTC.
   - Registra gancho via `atexit.register()` para efetuar `flush()` com limite de 2 segundos ao encerrar o servidor.

### 3.3 Amostragem de Recursos (`psutil`)
- Utilitário para coletar amostras de CPU e memória (`RSS` e `PSS` em Linux) do processo do backend e de seus subprocessos (Node, Brave, Xvfb).
- Amostrador executável de forma contínua durante benchmarks ou em intervalo configurável.

### 3.4 Ingestão e Agregação SQLite (`telemetry_db.py`)
Utilitário para ler eventos JSONL e consolidá-los no banco `telemetry/benchmarks.sqlite3` com o seguinte esquema:

- **`runs`**: Identificação do benchmark, data/hora, implementação, cenário, revisão e status.
- **`samples`**: Amostras detalhadas de cada span (`span_id` como chave primária para inserção idempotente via `INSERT OR IGNORE`).
- **`resource_samples`**: Amostras temporais de CPU e memória com identificação de PID e processo.
- **`summaries`**: Agregações consolidadas por execução e operação (contagem, taxa de sucesso, mediana p50, p95 e vazão).

---

## 4. Pontos de Instrumentação no Backend

1. **Servidor HTTP ([`server.py`](file:///home/thiagofdso/Projetos/manhua-manager/server.py)):**
   - `@app.before_request`: Inicia o span raiz `http.server.request`, gera `request_id`, identifica rota parametrizada via `request.url_rule.rule`.
   - `@app.teardown_request`: Conclui o span com o código HTTP resultante (`http_status`).
2. **Armazenamento e Persistência:**
   - [`load_data()`](file:///home/thiagofdso/Projetos/manhua-manager/server.py#L24-L31): Span `storage.read` (duração, contagem de obras).
   - [`save_data()`](file:///home/thiagofdso/Projetos/manhua-manager/server.py#L33-L36): Span `storage.write` (duração, bytes gravados).
   - Manipulação de `notifications.json`: Spans de leitura e escrita correspondentes.
3. **Proxy de Imagens (`/api/proxy-image`):**
   - Span `image.proxy`: Registra TTFB da origem e tempo total de transferência dos bytes ao cliente.
4. **Provedores de Capítulos:**
   - [`comix_provider.py`](file:///home/thiagofdso/Projetos/manhua-manager/comix_provider.py), [`mangafire_provider.py`](file:///home/thiagofdso/Projetos/manhua-manager/mangafire_provider.py) e [`manhuaus_provider.py`](file:///home/thiagofdso/Projetos/manhua-manager/manhuaus_provider.py): Span `chapter.extract` registrando domínio, contagem de imagens, tentativas e tempo total.

---

## 5. Estratégia de Testes e Validação

1. **Testes Unitários da Telemetria (`tests/test_telemetry.py`):**
   - Verificação de geração de `request_id`, `span_id` e hierarquia com `parent_span_id`.
   - Verificação do cálculo de `duration_ms` (> 0).
   - Verificação de captura de exceções com preenchimento correto de `outcome="error"` e `error_type`, re-lançando o erro.
   - Verificação do comportamento sob saturação de fila (descarte gracioso sem falhar chamadas e incremento de contador).
   - Verificação de escrita correta em arquivo JSONL.
2. **Testes do Banco de Dados e Ingestão (`tests/test_telemetry_db.py`):**
   - Verificação de criação de tabelas e integridade do banco SQLite.
   - Verificação de idempotência da importação de eventos JSONL.
   - Verificação dos cálculos agregados (p50, p95, taxa de erros).
3. **Testes de Integração e Não-Regressão:**
   - Teste de chamadas HTTP reais no Flask e verificação dos eventos gerados.
   - Execução completa da suíte de testes existente (`./.venv/bin/pytest tests/`) garantindo 100% de aprovação.
