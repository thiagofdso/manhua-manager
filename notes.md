# Auditoria de produto e open source: Manhua Manager

Data da análise: 2026-10-21  
Escopo: estado atual do worktree, incluindo mudanças locais ainda não commitadas.  
Regra seguida: nenhum código foi alterado; este arquivo é o único artefato criado pela análise.

## Veredito executivo

O projeto já é um protótipo funcional e relativamente rico para uso pessoal: há backend Flask, PWA web, app Flutter, leitura vertical, favoritos, ordenação, notificações, verificação de novos capítulos e downloads offline. A suíte Python passa inteira (`62 passed`).

Ele ainda não está pronto para um lançamento oficial nem para ser apresentado no GitHub como um projeto fácil de instalar e contribuir. O maior problema não é falta de funcionalidades; é falta de um contrato operacional confiável: a arquitetura depende de um servidor local configurado manualmente, de scraping de sites externos mutáveis, de HTTP sem autenticação e de arquivos JSON sem concorrência, migração ou backup. Além disso, a suíte Flutter atualmente não fecha: há erro de compilação no fake de `ApiService.addManhua` e um teste de armazenamento que não concluiu quando a execução foi interrompida.

Minha classificação atual:

- Produto para uso pessoal na mesma máquina/LAN: **promissor, mas frágil**.
- Beta privado para poucos usuários técnicos: **ainda não**.
- Release oficial para usuários gerais: **não**.
- Publicação open source no GitHub: **possível apenas como código em desenvolvimento**, não como projeto pronto para adoção.

## O que está bom

### Produto

- O problema é claro: acompanhar capítulos, abrir a leitura e manter uma lista pessoal.
- O fluxo principal existe nas duas interfaces: cadastrar, editar, remover, avançar/voltar capítulo e abrir o leitor.
- A evolução recente cobre necessidades reais: favoritos, reordenação, hiato, último capítulo, dia de atualização, notificações e download offline.
- O leitor web e o leitor Flutter têm fallback local; o Flutter tenta usar arquivos locais antes da rede (`mobile_app/lib/screens/reader_screen.dart:60`).
- Há suporte explícito para múltiplos provedores e adapters separados (`mangafire_provider.py`, `comix_provider.py`, `manhuaus_provider.py`), o que é melhor que concentrar todo scraping em um único caminho.
- Existe uma camada de testes backend razoável para operações de CRUD, campos, notificações, PWA, rotina e serviço.

### Engenharia

- O servidor usa `BASE_DIR` absoluto para localizar banco e arquivos (`server.py:16-18`), evitando uma classe comum de erro ao iniciar via systemd.
- O código tem cobertura de casos de domínio específicos, inclusive conversão de templates de URL e navegação entre capítulos.
- O limite de 50 capítulos por lote é uma proteção útil contra solicitações acidentais muito grandes (`server.py:814-818`).
- Há separação mínima entre modelo, controlador, serviços e telas no Flutter.
- O repositório preserva specs e planos de implementação, o que ajuda a reconstruir a intenção das mudanças.

## Bloqueadores antes de release

### P0: build e distribuição

1. **A suíte Flutter não está verde.** `flutter test` falhou ao compilar `mobile_app/test/controllers/manhua_controller_test.dart`: `FakeApiService.addManhua` não aceita os argumentos nomeados agora exigidos por `ApiService.addManhua` (`mobile_app/test/controllers/manhua_controller_test.dart:52`, `mobile_app/lib/services/api_service.dart:31`). Também houve falha de encerramento/teste incompleto em `storage_management_dialog_test.dart`. Não publicar APK enquanto `flutter test` e `flutter analyze` não passarem.
2. **O APK release ainda usa assinatura debug.** `mobile_app/android/app/build.gradle.kts:43` declara `signingConfig = signingConfigs.getByName("debug")`. Isso é incompatível com distribuição séria e impede uma cadeia de atualização confiável.
3. **Não há documentação de instalação utilizável.** `mobile_app/README.md` é o README inicial do Flutter e não explica servidor, URL, build, permissões, limitações ou fluxo de uso. Na raiz não há README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY ou CHANGELOG rastreados.
4. **A versão do app continua genérica.** O pacote se chama `mobile_app`, a descrição é a template do Flutter, o application id é `com.manhuamanager.mobile_app` e há TODO de configuração (`mobile_app/pubspec.yaml:1-2`, `mobile_app/android/app/build.gradle.kts:18-21`).

### P0: segurança e confiança

1. **A API não tem autenticação nem autorização.** Qualquer dispositivo que alcance a porta pode ler, criar, alterar, excluir obras, limpar notificações e disparar checagens. A aplicação escuta em `0.0.0.0:5000` (`server.py:988`) e habilita CORS global (`server.py:21`). Isso é aceitável somente para uma LAN controlada e explicitamente documentada.
2. **Há um proxy SSRF aberto.** `/api/chapter-images` e `/api/proxy-image` aceitam URLs arbitrárias e fazem requisições server-side (`server.py:621-625`, `server.py:844-889`). Um usuário da rede pode usar isso para alcançar serviços internos, além de transformar a instalação em proxy abusável. É necessário allowlist de domínios, bloqueio de IPs privados/loopback, limites de tamanho, redirect policy e validação de content-type.
3. **A aplicação usa HTTP puro por padrão.** O Flutter aponta para `http://100.84.57.79:5000` (`mobile_app/lib/controllers/manhua_controller.dart:15`, `mobile_app/lib/services/storage_service.dart:6`), e o Android permite cleartext global (`mobile_app/android/app/src/main/AndroidManifest.xml:11`). Isso expõe dados e comandos na rede local e torna o IP embutido uma dependência de ambiente.
4. **Não há limites de payload, rate limit ou limites de resposta.** O proxy lê conteúdo inteiro em memória (`server.py:884-887`); endpoints de scraping também podem receber respostas HTML grandes. Isso cria risco de consumo de memória e travamento do serviço.
5. **Persistência não é segura contra concorrência ou queda.** `save_data` sobrescreve diretamente JSON (`server.py:32-34`); downloads paralelos e requisições simultâneas podem perder atualizações ou deixar arquivo truncado. Falta escrita atômica, lock, validação de schema, backup e recuperação.

## Diagnóstico de produto

### Proposta e público

Hoje o produto mistura três propostas: tracker pessoal, leitor online/offline e gateway de scraping. Isso aumenta muito a superfície de falha. Para um lançamento, é preciso escolher uma promessa principal:

- **Tracker + leitor pessoal self-hosted:** prioriza estabilidade, importação simples e controle local.
- **Aplicativo multiplataforma pronto para usuário final:** exige distribuição, onboarding, sincronização e suporte.
- **Framework de provedores de leitura:** exige contrato de adapter, testes por fonte e documentação de manutenção.

O estado atual tenta atender as três, mas não define qual delas recebe prioridade quando um provedor quebra ou quando o servidor não está acessível.

### Jornada principal

O caminho feliz é bom, mas a experiência real ainda tem pontos de ruptura:

- O usuário precisa instalar/iniciar um backend separado e descobrir o endereço correto na rede.
- O IP padrão do Flutter está fixo e provavelmente só funciona no ambiente do autor.
- Não há onboarding que explique servidor, conectividade, permissões, modo offline, armazenamento ou fontes suportadas.
- Falhas de scraping são exibidas como erro técnico ou ausência de imagens; falta diagnóstico acionável por provedor.
- O cadastro aceita URLs de fontes externas, mas o contrato de URL suportado não é apresentado de forma clara.
- O web app concentra grande parte da interface em um único `index.html` de cerca de 1.600 linhas de script, dificultando evolução e testes de interação.
- O download offline aparenta ter dois modelos diferentes: IndexedDB no web (`index.html:1145`) e filesystem no Flutter (`mobile_app/lib/services/download_service.dart`). Não existe manifesto/versionamento/sincronização comum entre plataformas.

### Funcionalidade e semântica

- A rotina verifica a existência do próximo capítulo pelo retorno de imagens (`server.py:908-920`). Isso pode confundir bloqueio, página vazia, anti-bot e capítulo inexistente.
- `lastChapter` e `currentChapter` têm semânticas diferentes, mas o produto não as explica com clareza; um usuário pode interpretar “último capítulo” como progresso atual.
- A rotina agendada roda dentro do processo Flask em uma thread daemon (`server.py:965-986`). Reinício, múltiplos workers WSGI ou processo duplicado podem gerar execução perdida ou duplicada.
- Notificações são persistidas sem deduplicação; a mesma checagem pode gerar notificações repetidas em cenários de concorrência ou falha parcial.
- Downloads ignoram erros de imagens individuais e ainda podem terminar como sucesso (`mobile_app/lib/services/download_manager.dart:103-119`). Para leitura offline, um capítulo parcialmente salvo deveria ser marcado incompleto e não aparecer como disponível.
- O modo offline do catálogo permite alterar o capítulo localmente, mas não há fila de sincronização/conflict resolution quando a conexão retorna (`mobile_app/lib/controllers/manhua_controller.dart:80-91`).
- O leitor Flutter atualiza o backend sem `await` em `_changeChapter` (`mobile_app/lib/screens/reader_screen.dart:112`), o que pode produzir corrida entre navegação rápida e resposta tardia.

### Compatibilidade e fontes

Scraping é uma dependência de produto, não um detalhe de implementação. Cada fonte pode mudar HTML, API, anti-bot, cookies, termos de uso e disponibilidade. O projeto precisa de:

- catálogo declarativo de provedores suportados;
- health check por provedor;
- fixtures HTML/JSON versionadas e testes de contrato;
- mensagem de status por fonte;
- estratégia de descontinuação e aviso ao usuário;
- revisão jurídica e de termos para redistribuição/uso do conteúdo.

## Diagnóstico open source

### O que falta para o GitHub

- README raiz com proposta, screenshots, arquitetura, pré-requisitos, quick start, configuração do servidor, instalação web e Flutter, troubleshooting e limitações.
- Licença explícita. Sem LICENSE, terceiros não têm uma permissão clara para usar, modificar ou redistribuir o código.
- `CONTRIBUTING.md` com ambiente, testes, padrão de PR, como adicionar provedor e como reproduzir falhas.
- `SECURITY.md` com escopo, risco de expor a porta, SSRF e canal de reporte.
- Issue templates, pull request template e política de releases.
- CI para pytest, Flutter test/analyze, build web/mobile e verificação de arquivos sensíveis.
- Versionamento e changelog; a branch atual contém alterações locais não commitadas e vários artefatos ainda sem histórico (`git status`).
- Política de dependências e atualização. O Flutter informou 15 pacotes com versões mais novas incompatíveis com as restrições atuais.
- Separação clara entre dados de exemplo e dados pessoais. `database.json` é rastreado e funciona como estado, o que é inadequado para o fluxo normal de colaboração; faltam `database.example.json`, diretório configurável e instruções de backup.
- Revisão dos artefatos gerados e locais: `node_modules`, `.cache`, APK symlink, logs e arquivos de ambiente precisam de política explícita, não apenas convenção local.

### Manutenibilidade

- `server.py` concentra CRUD, persistência, scraping, proxy, rotina e scheduler em quase 1.000 linhas. Isso aumenta risco de regressão e dificulta contribuições isoladas.
- `index.html` contém estrutura, CSS e grande volume de JavaScript inline. Um novo colaborador não tem fronteiras claras de módulo.
- O contrato de dados não está formalizado. Campos como `chapterId`, `nextChapter`, `prevChapter`, `customOrder`, `lastChapter` e `updateDay` aparecem de forma evolutiva e sem schema/migração.
- Providers não seguem um protocolo explícito comum; parte da lógica conhece cada domínio diretamente no servidor.
- Os planos em `docs/superpowers` registram muitos passos como checkboxes não marcados, mesmo quando partes aparentam ter sido implementadas. Isso cria dúvida sobre o que é histórico, backlog ou estado atual.
- O README Flutter ainda comunica que o projeto é apenas um starter, contradizendo o estado funcional atual.

## Qualidade e verificação

### Evidências executadas

- Backend: `./.venv/bin/pytest -q` -> **62 passed**.
- Flutter: `/home/thiagofdso/development/flutter/bin/flutter test` -> **falha** por incompatibilidade de assinatura em `FakeApiService.addManhua`; execução também registrou teste de `StorageManagementDialog` incompleto/erro de stream ao encerrar.
- Graphify: detectou **625 arquivos de código, 235 documentos e 66 imagens**, mas não completou a extração semântica por ausência de chave LLM. A análise deste relatório, portanto, não depende de relações inferidas pelo grafo.

### Gaps de teste

- Não há testes de integração reais contra um processo Flask iniciado em porta de rede.
- Não há teste de concorrência para gravação de JSON ou scheduler duplicado.
- Não há testes de SSRF, redirect, IP privado, tamanho de resposta e content-type do proxy.
- Não há testes de contrato/fixtures para cada provedor externo.
- Não há build release validado, assinatura, instalação limpa ou upgrade de versão.
- Não há testes E2E de PWA, IndexedDB, service worker, recuperação offline e reconexão.
- Não há validação do Flutter em Android/iOS reais, principalmente permissões e cleartext.
- Não há `flutter analyze` nem pipeline CI reproduzível registrado no repositório.

## Plano de prioridade recomendado

### Fase 0: tornar o estado publicável

1. Corrigir os testes Flutter quebrados e obter `flutter test` verde; executar `flutter analyze`.
2. Criar README raiz e documentação de instalação de uma única rota suportada.
3. Definir licença, política de segurança, contribuição e CI mínimo.
4. Remover IP hardcoded, tornar URL configurável desde o primeiro uso e documentar o modelo LAN.
5. Decidir se o lançamento é LAN-only; se sim, afirmar isso no produto e endurecer as barreiras da API. Se não, adicionar autenticação e HTTPS.

### Fase 1: reduzir risco operacional

1. Restringir proxy e scraping por allowlist de provedores, bloquear destinos privados e impor limites.
2. Trocar persistência direta por escrita atômica com lock, schema e backup versionado.
3. Tirar scheduler de dentro do Flask ou garantir lock distribuível e idempotência.
4. Definir um protocolo de provider com `parse`, `fetch_chapter`, `list_navigation`, `proxy_headers`, `health` e fixtures.
5. Corrigir o modelo de downloads para distinguir concluído, parcial, falho e cancelado.

### Fase 2: melhorar a experiência

1. Onboarding de servidor/conexão/permissões.
2. Estado de erro por provedor com ação de recuperação.
3. Sincronização offline com fila e conflitos explícitos.
4. Export/import/backup do catálogo e dos metadados.
5. Acessibilidade, responsividade, i18n e E2E das jornadas principais.

## Checklist de go/no-go

Não considero release oficial aprovado até todos estes itens serem verdadeiros:

- `pytest`, `flutter test`, `flutter analyze` e builds de release passam em CI.
- Instalação limpa funciona sem depender de caminho absoluto, IP do autor ou arquivo de estado pré-existente.
- API não aceita proxy para destinos arbitrários e tem uma política de exposição documentada.
- Há backup e recuperação do catálogo.
- Há versão, changelog, licença, README, contribuição e canal de segurança.
- Pelo menos um provedor tem testes de contrato e um procedimento de atualização quando quebra.
- O fluxo offline não apresenta download parcial como capítulo válido.
- Um usuário novo consegue instalar, conectar e ler o primeiro capítulo apenas seguindo o README.

## Conclusão honesta

O projeto tem uma base de produto real e mostra boa velocidade de iteração, especialmente no backend e nos testes Python. O gargalo agora é maturidade de distribuição: confiabilidade, segurança, empacotamento, documentação e contratos de integração. Adicionar novas fontes ou mais recursos antes de resolver esses pontos aumenta o volume de código e não aumenta proporcionalmente a capacidade de lançar.

O próximo investimento de maior retorno é uma rodada de estabilização e release engineering, não uma nova feature.
