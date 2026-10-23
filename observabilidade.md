# Observabilidade e comparação de desempenho do backend

## Objetivo e escopo

Registrar uma linha de base do backend Python atual e comparar mudanças de arquitetura ou uma futura implementação em Go/Rust com dados reproduzíveis. Medir latência, capacidade, consumo de recursos e equivalência dos resultados.

Este documento é um plano de implementação. A instrumentação, os scripts de benchmark, os bancos e os serviços descritos abaixo ainda precisam ser criados. Os comandos de instalação são instruções para essa etapa; documentá-los não instala dependências nem inicia a coleta.

A avaliação inicial foi estática, sem benchmarks. Rede e inicialização de navegadores são hipóteses de gargalos que a coleta deverá confirmar.

## Estratégia recomendada

Começar com logs estruturados em JSONL, armazenamento histórico em SQLite e benchmarks controlados. Essa opção funciona localmente, permite consultar os resultados meses depois e não exige Docker.

Adicionar Prometheus e Grafana quando houver necessidade de acompanhamento contínuo. Adicionar OpenTelemetry quando for útil visualizar a sequência de operações entre servidor, workers e extratores. Essas ferramentas complementam o arquivo histórico de benchmarks.

Manter o mesmo contrato de operações, unidades e resultados em Python, Go e Rust. Usar `schema_version` para identificar mudanças no formato da telemetria.

## O que medir no projeto

| Área e ponto inicial | Operações propostas | Dados específicos |
| --- | --- | --- |
| Rotas em `server.py` | `http.server.request` | Método, rota parametrizada, status, duração e requisições em andamento |
| `load_data`, `save_data` e notificações | `storage.read`, `storage.write` | Tipo de arquivo, bytes, registros e duração |
| Importadores em `importers/` | `catalog.browse`, `catalog.parse`, `cache.read`, `cache.write` | Domínio, página, itens, cache e fallback |
| Provedores e extração HTML | `chapter.extract`, `chapter.parse`, `http.client.request` | Domínio, imagens, tentativas, status externo e erros |
| `mangafire_provider.py` | `token.generate`, `process.start`, `http.client.request` | Tempo de Node, geração de token, renovação dos assets e consultas externas |
| Scripts `*_extractor.mjs` | `browser.launch`, `browser.navigate`, `browser.wait`, `browser.extract`, `browser.close` | Etapas internas, sessão nova/reutilizada e tipo de espera |
| Endpoint de capítulos em lote | `batch.extract`, `chapter.extract` | Capítulos solicitados/concluídos, sucessos parciais e concorrência |
| Proxy de imagens | `image.proxy`, `http.client.request` | Tempo até primeiro byte da origem, transferência completa, bytes e falhas |
| Rotina automática/manual | `routine.check`, `routine.check_item` | Obras elegíveis/verificadas, capítulos encontrados e duração por obra |
| Processo e seus descendentes | `process.resources` | CPU, memória, quantidade de processos e amostras por execução |
| Cliente de benchmark e Flutter | `client.request`, `client.download` | Primeiro byte, transferência completa, timeout e resultado percebido pelo cliente |

O backend fornece URLs e faz proxy; a gravação de downloads offline e o controle das tarefas estão no Flutter. O download de imagens dentro de cada tarefa é atualmente sequencial. Separar o benchmark do servidor do fluxo completo no aplicativo.

O cliente Flutter usa timeout padrão de dez segundos, enquanto alguns extratores podem esperar quarenta ou cinquenta segundos. Registrar timeouts dos dois lados e a configuração usada em cada execução.

## Definições de tempo e correlação

- Usar `time.perf_counter_ns()` no Python e `performance.now()` ou `process.hrtime.bigint()` no Node para intervalos locais. Nunca calcular duração pela diferença entre horários de calendário.
- Persistir durações em milissegundos nos eventos históricos. Para métricas Prometheus, usar segundos e o sufixo `_seconds`.
- Usar horário UTC com fuso explícito para localizar eventos e correlacionar máquinas. Não subtrair valores de relógios monotônicos de processos diferentes.
- Criar `request_id` na entrada HTTP e `span_id`/`parent_span_id` para operações internas. Passar a correlação aos subprocessos e às tarefas do executor explicitamente.
- Medir tempo de fila separado de tempo de execução, quando existir fila.
- Registrar resultado e duração mesmo em exceção, timeout ou cancelamento. Um bloco `finally` deve encerrar a medição.
- Separar o retorno do handler da entrega completa da resposta. Isso é essencial para comparar um proxy com buffering com outro usando streaming.
- Em lotes paralelos, registrar duração total e duração por capítulo. A soma dos capítulos pode ser maior que a duração do lote; tempos de spans sobrepostos não são parcelas somáveis.

Os extratores Node precisam medir suas próprias etapas. Medir apenas `subprocess.run` mostra o tempo total do processo, sem revelar quanto foi inicialização, navegação, desafio do site ou extração.

Quando o processo terminar por timeout antes de emitir o resumo, registrar o tempo observado pelo processo pai e marcar as etapas internas como indisponíveis. Não registrar duração zero para etapas sem medição.

## Contrato dos eventos

Exemplo ilustrativo, sem representar uma medição real:

```json
{
  "schema_version": 1,
  "timestamp": "2026-10-23T18:30:00Z",
  "service": "manhua-manager-backend",
  "implementation": "python",
  "revision": "abc123",
  "request_id": "req-123",
  "span_id": "span-2",
  "parent_span_id": "span-1",
  "operation": "chapter.extract",
  "route": "/api/chapter-images",
  "domain": "comix.to",
  "duration_ms": 2840.5,
  "outcome": "success",
  "cache_state": "miss",
  "browser_state": "new",
  "attempt": 1,
  "image_count": 32,
  "benchmark_run_id": null
}
```

Campos adicionais: `http_status`, `upstream_status`, `error_type`, `bytes_received`, `queue_duration_ms`, `requested_chapters`, `completed_chapters` e `worker_limit`.

Valores sugeridos para `outcome`: `success`, `partial`, `error`, `timeout` e `cancelled`. Para cache: `hit`, `miss`, `stale_fallback`, `bypass` e `not_applicable`. Diferenciar fallback para cache antigo de uma consulta externa bem-sucedida.

Usar rotas parametrizadas, como `/api/manhuas/<int:item_id>`, em vez do caminho com cada ID. Não registrar cookies, tokens, cabeçalhos de autenticação ou URLs com parâmetros sensíveis. Para relacionar fixtures, usar um identificador ou hash estável.

## Instalação mínima: histórico local

### Componentes

| Componente | Obrigatoriedade | Finalidade |
| --- | --- | --- |
| Python e `.venv` existentes | Obrigatório | Executar backend e instrumentação |
| `logging`, `queue`, `sqlite3`, `time`, `json`, `statistics` | Biblioteca padrão | Eventos, persistência, intervalos e relatórios básicos |
| `psutil` | Recomendado | Amostrar CPU e memória do servidor e descendentes |
| `httpx` | Recomendado para benchmark | Cliente reutilizável para cenários HTTP sequenciais e concorrentes |
| CLI `sqlite3` | Opcional | Consultas e backups pelo terminal |
| Node, Puppeteer, Brave e Xvfb quando aplicável | Já fazem parte dos fluxos existentes | Executar os mesmos extratores durante a comparação |

Instalar as dependências de observabilidade no ambiente existente, na raiz do projeto:

```bash
.venv/bin/python -m pip install psutil httpx
```

Durante a implementação, registrar versões fixas dessas dependências em um arquivo próprio, por exemplo `requirements-observability.txt`. Registrar também o ambiente resolvido de cada benchmark:

```bash
.venv/bin/python -m pip freeze > telemetry/python-environment.txt
```

O diretório `telemetry/` precisa ser criado antes desse último comando. Não é necessário instalar um servidor SQLite: o módulo Python já permite criar e consultar o banco.

Em Debian/Ubuntu, caso seja desejada a interface de terminal:

```bash
sudo apt-get update
sudo apt-get install sqlite3
```

### Organização dos dados

Estrutura proposta, ainda não criada:

```text
telemetry/
  events/                 # JSONL ativo e segmentos rotacionados
  archive/                # Segmentos encerrados e comprimidos
  benchmarks.sqlite3      # Execuções, amostras e resumos históricos
  runs/
    <run-id>/
      manifest.json       # Ambiente, cenário, versões e configurações
      samples.jsonl       # Observações brutas do benchmark
      resources.jsonl     # CPU/memória com horário e processos observados
      summary.json        # Agregações calculadas
      report.md           # Comparação legível
  backups/                # Cópias locais; manter também cópia fora da máquina
```

Na implementação, criar os diretórios e ignorar dados gerados no Git. Versionar contratos, scripts, configurações e definições de cenários; preservar snapshots e fixtures conforme seu tamanho e conteúdo. Guardar o hash das fixtures no manifesto.

### Caminho de escrita

O módulo proposto `telemetry.py` deverá oferecer um medidor reutilizável, receber contexto de correlação e emitir eventos JSON estruturados. Os hooks do Flask cuidarão da entrada HTTP; operações de domínio terão medições explícitas.

Usar fila limitada com um consumidor para a escrita dos logs. Definir tamanho máximo, política de saturação e contador de eventos descartados. Não permitir crescimento ilimitado nem falhar uma requisição porque a telemetria falhou. No encerramento normal, esvaziar a fila com prazo definido.

Durante benchmarks, registrar descartes e invalidar a execução se faltarem amostras necessárias à análise. Telemetria assíncrona pode perder eventos em uma interrupção abrupta; essa limitação deve constar do relatório.

Preferir importar segmentos JSONL encerrados para SQLite em lotes, fora do caminho HTTP. O consumidor deve evitar inserções duplicadas, usando uma chave única por evento ou o par execução/amostra. Usar um único escritor, transações e uma versão de esquema do banco.

### Esquema histórico proposto

| Tabela | Conteúdo |
| --- | --- |
| `runs` | ID, início/fim, revisão, implementação, cenário, ambiente, configurações e validade da execução |
| `samples` | ID único, execução, operação, domínio, cache, duração, resultado, tamanho e contagens |
| `resource_samples` | Execução, horário, PID, identidade do processo, CPU e memória |
| `summaries` | Execução e grupo, contagem, sucessos/falhas, mediana, p95, vazão e versão do cálculo |

Manter amostras brutas, além dos resumos. Elas permitem recalcular percentis, corrigir análises e criar agrupamentos futuros. Indexar execução, operação, domínio e estado do cache.

Não armazenar exclusivamente médias ou percentis já calculados. Não calcular o p95 de um conjunto fazendo a média dos p95 de suas partes.

### Retenção e backup

Política inicial sugerida, ajustável após medir o volume:

- Logs operacionais: rotação diária ou por tamanho, com até 30 dias locais.
- Execuções oficiais de benchmark: preservar amostras, manifesto e relatórios durante todo o período da migração e por pelo menos 12 meses após a decisão.
- Banco histórico: preservar enquanto houver comparações ativas, com backup diário e após cada linha de base oficial.
- Fazer cópia fora da máquina dos benchmarks oficiais e verificar periodicamente se ela pode ser restaurada.
- Monitorar espaço disponível e registrar qualquer descarte por retenção. A rotação operacional não deve remover arquivos de execuções oficiais.

Com a CLI opcional instalada e o banco já criado, exemplo de backup consistente:

```bash
sqlite3 telemetry/benchmarks.sqlite3 ".backup 'telemetry/backups/benchmarks-backup.sqlite3'"
sqlite3 telemetry/backups/benchmarks-backup.sqlite3 "PRAGMA integrity_check;"
```

Usar nomes datados na rotina definitiva para preservar versões. Como alternativa sem CLI, implementar backup com `sqlite3.Connection.backup()` da biblioteca padrão. Evitar copiar somente o arquivo principal de um banco ativo, especialmente em modo WAL.

## Protocolo dos benchmarks

### Dois grupos de cenários

**Controlados:** usar fixtures de HTML, JSON e imagens, servidas localmente, e uma cópia isolada da biblioteca. Comparar parsing, armazenamento, proxy e concorrência com entradas idênticas. Para medir inicialização e automação do navegador, usar uma página local determinística; ela não reproduz desafios externos.

**Reais:** executar os fluxos contra os sites e registrar suas condições. Separar domínios, cache frio/quente, sessões e presença de desafios. Esses testes mostram o resultado prático, mas misturam o custo do sistema com variações dos sites e da rede.

Não apresentar resultado com fixture como se medisse a latência real do site. Não usar os mesmos cookies/perfis simultaneamente em implementações concorrentes.

### Matriz inicial

| Cenário | Variações sugeridas |
| --- | --- |
| Listar biblioteca | 100, 1.000 e 10.000 obras sintéticas |
| Atualizar progresso/favorito | Biblioteca pequena/grande e escritores concorrentes |
| Consultar catálogo | Por domínio, com hit/miss e fallback separados |
| Extrair capítulo | HTML direto, API com token e navegador |
| Consultar lote | 5, 20 e 50 capítulos; registrar limite de workers |
| Proxy de imagem | Conjunto fixo de imagens de tamanhos conhecidos |
| Rotina de atualização | Quantidade fixa de obras, respostas positivas/negativas/erros |
| Fluxo no aplicativo | Mesmo aparelho, rede e conjunto de capítulos |

Começar com um cliente e repetir com 5 e 10 clientes em ambiente controlado. Ajustar a carga à máquina e usar uma carga pequena e limitada nos sites reais.

Para cada cenário, registrar:

1. Implementação, revisão Git e presença de alterações locais. Para uma linha de base oficial, guardar também um patch das alterações relevantes ou um snapshot reproduzível; o hash do commit sozinho não descreve uma árvore modificada.
2. Sistema operacional, CPU, RAM, versões de runtime, dependências, navegador e configuração do servidor HTTP.
3. Dataset, hashes das fixtures, seed, estado inicial do armazenamento e procedimento de limpeza/aquecimento de cache.
4. Concorrência, limites por domínio, timeouts, retries, tamanho dos lotes e modo de sessão do navegador.
5. Quantidade de aquecimentos, duração ou quantidade de requisições medidas, repetições e critério de encerramento.
6. Instrumentação habilitada, amostragem, intervalo de coleta de recursos e eventos perdidos.

Usar diretórios temporários ou cópias isoladas para cache e biblioteca. Não apagar o cache de uso diário nem executar testes de escrita sobre `database.json` real.

Separar inicialização fria de estado aquecido. Para o cenário aquecido, excluir os aquecimentos da estatística e registrar quantos foram feitos. Executar várias rodadas alternando a ordem das implementações para reduzir viés de horário, temperatura e rede.

Preservar a mesma configuração de coleta nos dois lados. Registrar separadamente mudanças de linguagem, banco, cache, streaming, concorrência e persistência do navegador. Quando possível, comparar uma mudança por vez para atribuir os ganhos.

### Como reportar

- Latência: mediana, p95, máximo e número de amostras por cenário/domínio/cache. Usar p99 apenas com volume suficiente e declarar a contagem.
- Confiabilidade: sucessos, resultados parciais, erros, timeouts e cancelamentos, incluindo tentativas.
- Vazão: operações úteis concluídas com sucesso por segundo, considerando a janela de carga definida. Informar também a taxa de requisições e falhas.
- Proxy: tempo até primeiro byte e tempo até transferência completa, medidos pelo cliente, junto dos bytes entregues.
- Recursos: CPU acumulada, pico de memória observado, intervalo de amostragem e processos incluídos.
- Correção: conferir quantidade/ordem das imagens, navegação, alterações persistidas e resultados das rotinas. Um resultado vazio ou incompleto mais rápido não é uma melhoria.

Calcular latência dos sucessos e apresentar falhas separadamente com seus tempos. Não ocultar timeouts: a operação pode continuar no servidor depois que o cliente desiste. Quando houver cancelamento propagado, registrar esse comportamento.

Para duração, calcular redução percentual como `100 * (tempo_baseline - tempo_novo) / tempo_baseline`, com baseline positivo. Comparar o mesmo indicador e grupo. Para vazão, reportar aumento com a fórmula correspondente, identificando a direção desejada.

Não somar RSS dos processos como se fosse memória física exclusiva: bibliotecas e páginas podem ser compartilhadas. Se usar soma de RSS, identificá-la como tal; em Linux, preferir PSS quando disponível. Amostras podem perder picos muito curtos. Incluir Node, Brave e Xvfb quando fizerem parte da execução, sem atribuir processos de outros serviços ao benchmark.

O SQLite padrão não oferece uma função universal de percentil. Calcular os percentis no relatório com método documentado e estável entre versões, preservando a precisão e as amostras originais.

## Evolução opcional: Prometheus e Grafana

### O que instalar

- Docker Engine e plugin Docker Compose, seguindo as instruções oficiais para a distribuição, se optar por containers.
- `prometheus-client` no ambiente Python para expor métricas da aplicação.
- Prometheus para coletar e guardar séries temporais.
- Grafana para consultar o Prometheus e visualizar painéis.

```bash
.venv/bin/python -m pip install prometheus-client
docker --version
docker compose version
```

Na implementação, criar configuração e Compose próprios, fixar versões de imagens e preservar os arquivos utilizados em cada benchmark. Expor `/metrics` ou uma porta dedicada. Se houver múltiplos processos Python, configurar a coleta multiprocessos ou um agregador; a memória de um processo não representa todos os workers.

Em containers, configurar explicitamente o acesso ao backend no host. `localhost` no container aponta para o próprio container, não para o Flask no host. Definir também como o Prometheus alcançará os serviços futuros em Go/Rust.

### Persistência

| Serviço | Dados que precisam persistir |
| --- | --- |
| Prometheus | Diretório TSDB, normalmente `/prometheus`, em volume ou bind mount |
| Grafana | `/var/lib/grafana`, incluindo configurações e banco interno |
| Provisionamento | Arquivos de fontes de dados, painéis e configurações no repositório |

Grafana não guarda automaticamente as amostras consultadas no Prometheus. Preservar apenas seu volume não preserva o histórico das métricas.

Proposta inicial: coleta a cada 15 segundos, retenção de 90 dias e limite de tamanho compatível com o disco. Configurar a retenção pelos parâmetros suportados pela versão fixada; quando houver limites de tempo e tamanho, o tamanho pode provocar remoção antes dos 90 dias. Manter margem para WAL e compactação.

O intervalo de coleta não permite medir precisamente o pico de uma tarefa muito curta. Usar as amostras locais do benchmark para isso. Para comparações meses depois, manter o histórico SQLite/JSONL independentemente da retenção operacional do Prometheus.

### Métricas propostas

| Métrica | Tipo |
| --- | --- |
| `manhua_http_requests_total` | Counter |
| `manhua_http_request_duration_seconds` | Histogram |
| `manhua_operation_duration_seconds` | Histogram |
| `manhua_operations_total` | Counter por resultado |
| `manhua_cache_accesses_total` | Counter por estado |
| `manhua_image_proxy_bytes_total` | Counter |
| `manhua_active_tasks` | Gauge |
| `manhua_telemetry_dropped_events_total` | Counter |

Labels limitadas: operação, rota parametrizada, método, classe de status, domínio suportado, implementação e estado do cache. Não usar URL completa, título, capítulo, `request_id` ou ID de execução como labels. Identificar revisões no manifesto ou metadados controlados, evitando uma nova série para cada evento.

Definir histogramas compatíveis com operações de milissegundos a dezenas de segundos. Em histogramas clássicos, manter os mesmos buckets entre implementações e registrar os limites. Validar o suporte de biblioteca e servidor antes de escolher histogramas nativos. Percentis de histogramas são estimativas; o histórico bruto serve para análises detalhadas.

## Evolução opcional: OpenTelemetry

OpenTelemetry fornece instrumentação e exportação; não é, por si só, um banco histórico de traces.

Para instrumentação explícita no Python, instalar os pacotes necessários aos caminhos escolhidos:

```bash
.venv/bin/python -m pip install \
  opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp \
  opentelemetry-instrumentation-flask \
  opentelemetry-instrumentation-requests \
  opentelemetry-instrumentation-urllib
```

Instalar um OpenTelemetry Collector se houver necessidade de centralizar os envios e um backend de traces, como Tempo ou Jaeger, para armazená-los. Escolher um backend e configurar sua persistência e retenção antes de depender dos traces para comparação. O Collector não substitui esse armazenamento.

Configurar identidade do serviço, versão, endpoint/protocolo OTLP, exportação em lote e política de amostragem. Evitar instrumentação automática e manual duplicadas na mesma operação HTTP. As etapas de navegador, fila e operações de domínio continuarão exigindo spans próprios.

Registrar todos os eventos necessários durante benchmarks oficiais. Se houver amostragem em uso cotidiano, registrá-la no manifesto e não tratar os traces amostrados como o universo de requisições. Propagar contexto às threads e ao Node explicitamente; o contexto não atravessa subprocessos sozinho.

Um caminho de evolução possível é manter os mesmos nomes conceituais dos eventos locais e mapeá-los para spans OpenTelemetry, adotando as convenções HTTP oficiais. Registrar o mapeamento e suas versões.

## Validação da instrumentação

Antes de coletar a linha de base oficial:

- Confirmar eventos para sucesso, exceção, timeout, cancelamento e resposta parcial.
- Confirmar correlação entre requisição, executor e subprocesso, inclusive sob concorrência.
- Conferir unidades, ausência de duplicação e compatibilidade dos eventos com o contrato.
- Comparar uma carga controlada com telemetria habilitada/desabilitada para estimar seu overhead.
- Reiniciar o servidor e confirmar rotação, persistência, importação idempotente e recuperação de backup.
- Conferir que nenhuma credencial ou parâmetro sensível aparece nos eventos.
- Restaurar uma execução arquivada e gerar novamente o resumo a partir das amostras.

## Ordem de implementação

1. Criar contrato, módulo de medição e configuração por ambiente.
2. Instrumentar HTTP, armazenamento, proxy, provedores e extratores Node.
3. Implementar logs JSONL, rotação, importação SQLite e backup.
4. Implementar cenários controlados, coletor de recursos e gerador de relatórios.
5. Coletar a linha de base Python sem alterações de arquitetura simultâneas.
6. Coletar uso real por alguns dias como complemento, identificando carga e variações externas.
7. Avaliar cada otimização ou migração usando os mesmos cenários e contratos.
8. Adicionar Prometheus/Grafana e tracing quando a investigação justificar esses serviços.

Critério de conclusão da primeira etapa: conseguir selecionar duas execuções preservadas, reproduzir seus ambientes/dados e gerar uma comparação por cenário com duração, confiabilidade, recursos e verificação de resultados.

## Referências oficiais

- [Python: relógios e medição de intervalos](https://docs.python.org/3/library/time.html#time.perf_counter_ns).
- [Python: SQLite e API de backup](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup).
- [Node.js: Performance measurement APIs](https://nodejs.org/api/perf_hooks.html).
- [psutil: documentação](https://psutil.readthedocs.io/).
- [HTTPX: documentação](https://www.python-httpx.org/).
- [Docker Engine: instalação](https://docs.docker.com/engine/install/).
- [Docker Compose: instalação do plugin](https://docs.docker.com/compose/install/linux/).
- [Prometheus: boas práticas de instrumentação](https://prometheus.io/docs/practices/instrumentation/).
- [Prometheus: histogramas e percentis](https://prometheus.io/docs/practices/histograms/).
- [Prometheus: armazenamento e retenção](https://prometheus.io/docs/prometheus/latest/storage/).
- [Cliente Python do Prometheus](https://prometheus.github.io/client_python/).
- [Grafana: execução com Docker e persistência](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/).
- [OpenTelemetry: instrumentação Python](https://opentelemetry.io/docs/languages/python/instrumentation/).
- [OpenTelemetry: convenções semânticas HTTP](https://opentelemetry.io/docs/specs/semconv/http/).

As versões exatas devem ser escolhidas e fixadas na implementação. As recomendações de retenção, carga e diretórios deste documento são decisões propostas para o projeto, não valores obrigatórios das ferramentas.
