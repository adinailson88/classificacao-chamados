# Pendências para a próxima sessão

Registrado em 2026-09-26. Ao iniciar uma nova sessão, ler este arquivo antes
de alterar qualquer coisa e perguntar ao Adinailson se deseja tratar alguma
das pendências abaixo (conforme regra do `AGENTS.md`).

---

## Pendência 1 — Promover a aba COPIA a aba principal (migração de fonte de verdade)

### Contexto / motivação

A planilha `CHAMADOS_ESQUELETO_REDUZIDO` (id
`1lohPUQOgxzt_DMxnNLKMxnieZq1sVmh4uwBLbbgvfiQ`) tem hoje duas abas paralelas
com o mesmo schema (`A1:Q`):

- **`CHAMADOS_ESQUELETO_REDUZIDO`** — aba principal atual, usada por
  `config_experimento.json["aba_principal"]` e lida/escrita por ~37 scripts
  do repositório (`src/*.py`, `scripts/migracoes/*.py`). Coluna A:F
  historicamente alimentada por `IMPORTRANGE`, sujeita a erros
  intermitentes (`#REF!`, `#N/A`, quota, "Carregando...").
- **`COPIA`** — aba construída pelo Adinailson via Apps Script
  ("API Classificacao Chamados", projeto ligado à planilha) para eliminar
  o `IMPORTRANGE` na faixa A:F, puxando os dados diretamente das fontes via
  script (mais confiável).

O pedido é avaliar se dá para tornar `COPIA` a fonte de verdade única —
tanto para o pipeline Python deste repositório quanto para as demais
abas/dashboards que hoje importam de `CHAMADOS_ESQUELETO_REDUZIDO`.

### O que já foi confirmado (lendo o código do Apps Script, arquivo
`SincronizarCopia.gs`/`SincronizarGQ.gs` do projeto "API Classificacao
Chamados" ligado à planilha)

**Sincronização de A:F (`sincronizarCopiaPorId`, `COPIA_SYNC_CFG`)**
- Lê de três planilhas externas, NUNCA de `CHAMADOS_ESQUELETO_REDUZIDO`:
  - `historicalSpreadsheetId = "1xnU5sDcEWrDjs_trU3tC0jOHCljp7o_SmRNvyJzqkUg"` (aba `Pagina1`) — fonte histórica de id/título/categoria/subcategoria;
  - `currentSpreadsheetId = "1VgHY6NmCQLtA3lcfQAzGIRqJFZGHwcGhZ4zaXkqOmz4"` (aba `CHAMADOS`) — espelho GLPI atual (id/título/categoria/descrição/solução);
  - `osSpreadsheetId = "1zTSo5oTFDyo3espWmYl1WjpFU57PwHDeZqnxUkrGQ2Y"` (aba `Ordens de Serviços`) — título/descrição de O.S.
- Escreve em `COPIA!A:F` por `ID Chamado` (chave lógica), nunca em G:Q — há
  pós-condição explícita que aborta (`throw`) se G:Q mudar durante a
  sincronização.
- Fluxo com governança própria (bem parecida com a deste repo):
  `preflightCopiaSemImportrange()` → revisar `PREVIEW_COPIA_A_F` → escrever
  `APLICAR_COPIA` em `PREVIEW_COPIA_A_F!B1` → `aplicarCopiaSemImportrange()`
  → só depois `simularSincronizacaoCopiaPorId()`. Tem backup automático
  (`BACKUP_COPIA_AF_<timestamp>`, aba oculta) e readback de validação antes
  de confirmar.
- Baseline de exclusão (`knownExcludedIds`, 55 IDs) nunca é inserida como
  "nova"; `allowNewIds: true` hoje — candidatos novos (ausentes na COPIA)
  SÃO inseridos automaticamente.
- Gatilho: `instalarGatilhoCopiaPorId()` — a cada 2h.
- **Status confirmado em produção (26/09/2026, print do painel de
  Acionadores do Apps Script "API Classificacao Chamados"): ATIVO.**
  Última execução 26/09/2026 14:09:34, **taxa de erro 13,58%** — não
  bloqueia esta migração, mas é uma pendência separada a investigar (ver
  Pendência 1.1 abaixo).

**Sincronização de G:Q (`sincronizarGQPorId`, `GQ_SYNC_CFG`)**
- Comentário do próprio script (fonte primária, não interpretação minha):
  > "a aba principal e a fonte de verdade de G:Q (pipeline de classificação
  > Python + conferência humana escrevem lá, nunca em COPIA). COPIA teve
  > G:Q copiados uma vez (materialização inicial) e ficou parada desde
  > então -- este sincronizador fecha esse gap continuamente."
- `sourceSheetName = 'CHAMADOS_ESQUELETO_REDUZIDO'` (hardcoded, não lê de
  config) → `destSheetName = COPIA`. **Sentido único: principal → COPIA.**
- Sobrescreve em COPIA qualquer célula onde o valor da principal for
  não-vazio e diferente do que já está em COPIA (nunca apaga por a
  principal estar vazia). K/L (`Comparação`, `Classificado_Confiança_IA`)
  nunca são copiados como valor — são sempre fórmulas locais recalculadas
  em COPIA a partir de G/H/I/C da própria linha (copiadas da linha 2 como
  modelo a cada atualização).
- Gatilho: `instalarGatilhoGQPorId()` — a cada 2h.
- **Status confirmado em produção (mesmo print, 26/09/2026): ATIVO.**
  Última execução 26/09/2026 14:39:37, taxa de erro 0%.

### O bloqueador real (por que não é só trocar uma config)

Se `config_experimento.json["aba_principal"]` for trocado para `"COPIA"`
com o trigger `sincronizarGQPorId` ainda ativo, o pipeline Python passa a
escrever G:Q direto em `COPIA`. Só que esse trigger continua lendo
`CHAMADOS_ESQUELETO_REDUZIDO` (que ninguém mais vai escrever) a cada 2h e
**sobrescrevendo em COPIA qualquer célula cujo valor antigo (na principal,
agora congelada) divirja do valor novo (em COPIA, recém-gravado pelo
pipeline)** — isso reverteria classificações/reclassificações/conferências
novas para o valor velho, violando a regra 6 do `AGENTS.md` (nunca
apagar/sobrescrever M, N, P, Q).

**Ação obrigatória antes de qualquer troca de `aba_principal`:** excluir o
acionador de `sincronizarGQPorId` no painel de Acionadores do Apps Script
(projeto "API Classificacao Chamados" ligado à planilha) — menu ⋮ na linha
correspondente → Excluir acionador. **Ainda não foi feito** até o registro
desta pendência (26/09/2026) — confirmar com o Adinailson se já foi
excluído antes de prosseguir.

O trigger `sincronizarCopiaPorId` (A:F) e `ocultarAbasSecundarias` podem
continuar ativos sem problema — não têm relação com este risco.

### Outros pontos de blast radius já mapeados no repositório

1. **`src/recongelar_ensemble_online.py`** (linha 74 e 152) — tem uma
   constante travada `ABA_CANONICA = "CHAMADOS_ESQUELETO_REDUZIDO"` e
   **recusa rodar** (`RuntimeError`) se `config["aba_principal"]` divergir
   dela. É guarda deliberada da trilha científica congelada (Trilha A,
   `docs/dados/MANIFESTO_ARTIGO_CONGELADO.json`). Precisa de decisão
   consciente de como tratar — provavelmente manter essa constante fixa em
   `"CHAMADOS_ESQUELETO_REDUZIDO"` (lendo essa aba especificamente, à parte
   do `aba_principal` corrente) para não misturar a fonte do artigo já
   publicado com a operação corrente.
2. **`config_experimento.json["aba_principal"]`** é lido por ~37 scripts
   (`grep -rln "aba_principal" src/*.py scripts/migracoes/*.py`) — é um
   valor único, então a troca em si é barata; o risco está todo na
   coordenação com o Apps Script (acima) e no item 1.
3. **`dashboard.yml`** (dashboard estático deste repo, GitHub Pages) já lê
   via `gspread`/API (não via `IMPORTRANGE`) — não é afetado pelo problema
   de `IMPORTRANGE` que motivou a COPIA, e seguiria `aba_principal`
   automaticamente sem esforço extra.
4. **Abas/dashboards externos que hoje importam de
   `CHAMADOS_ESQUELETO_REDUZIDO` por nome** (fora deste repositório e fora
   desta planilha) — não mapeado; não tenho ferramenta nesta sessão para
   ler fórmulas de outras planilhas. Precisa de levantamento manual pelo
   Adinailson.

### Sequência recomendada (retomar a partir daqui)

1. Confirmar que `sincronizarGQPorId` foi removido do painel de
   Acionadores (bloqueador acima).
2. Rodar `python src/verificar_artigo_congelado.py` antes de qualquer
   mudança (linha de base).
3. Decidir e implementar o tratamento de
   `src/recongelar_ensemble_online.py` (manter fixo na aba antiga,
   explicitamente, sem depender de `aba_principal`).
4. Trocar `config_experimento.json["aba_principal"]` para `"COPIA"`, com
   dry-run reportado antes de qualquer escrita real (regra 5 do
   `AGENTS.md`).
5. Rodar `python src/verificar_artigo_congelado.py` de novo (confirmar que
   a trilha congelada não foi afetada).
6. Levantar e repontar manualmente as abas/planilhas externas que hoje
   importam de `CHAMADOS_ESQUELETO_REDUZIDO` por nome.

### Pendência 1.1 (secundária, não bloqueia a migração)

`sincronizarCopiaPorId` (A:F) está com 13,58% de taxa de erro no painel de
Acionadores. Vale investigar depois: Apps Script → ícone de execuções (⏱️)
→ ver mensagens de erro das execuções falhas. Hipótese mais provável:
falhas transitórias ao ler as 3 planilhas-fonte (GLPI atual, histórico, OS)
— o script já tem `LockService` e não teria retry automático de erro de
leitura externa.

---

## Pendência 2 — Escrita de volta no GLPI via API (pedido para o futuro)

### Pedido do Adinailson

Quer, no futuro, uma forma de escrever da planilha (categoria
reclassificada pela IA, por exemplo) de volta para o GLPI via API — hoje o
fluxo é só leitura (GLPI → planilha, via IMPORTRANGE/script → pipeline
Python → coluna G/O na planilha). Pediu para adiantar, ainda nesta sessão,
se é viável e como seria feito.

### Viabilidade — SIM, é viável. GLPI tem API REST nativa

O GLPI expõe uma API REST própria (`apirest.php`) desde a versão 9.1,
madura e documentada oficialmente
(https://github.com/glpi-project/glpi/blob/main/apirest.md). Não é preciso
proxy nem scraping. Resumo técnico do que seria necessário:

**1. Habilitar a API no GLPI (feito por quem tem acesso admin ao GLPI,
não pelo repositório):**
- `Configurar > Geral > API` → habilitar "API REST".
- Criar um "Cliente API" (`Configurar > Geral > API > aba Clientes API`)
  com: IP de origem liberado (o runner do GitHub Actions usa IPs
  dinâmicos — normalmente libera-se por faixa da Microsoft/Azure ou
  desabilita-se a checagem de IP para esse cliente específico, com o
  App-Token compensando o controle de acesso), e o "App-Token" gerado
  ali é fixo e vai para um GitHub Secret (ex.: `GLPI_APP_TOKEN`).
- Gerar um "Token de API" pessoal para o usuário de serviço que vai
  escrever (`Aba "Minhas configurações" > Chaves de API remotas` do
  usuário no GLPI) — vira outro secret (`GLPI_USER_TOKEN`). Alternativa:
  autenticação por login/senha (menos recomendável para automação).
- O usuário de serviço no GLPI precisa de perfil com direito de
  **atualização** sobre `Ticket` (e leitura sobre `ITILCategory`).

**2. Fluxo de autenticação (por execução do workflow, sessão curta):**
```
POST {GLPI_URL}/apirest.php/initSession
Headers: App-Token: <GLPI_APP_TOKEN>
         Authorization: user_token <GLPI_USER_TOKEN>
-> retorna session_token
```
Todas as chamadas seguintes levam `Session-Token: <session_token>` e
`App-Token: <GLPI_APP_TOKEN>` no header. Ao final, `POST .../killSession`.

**3. Escrever a categoria reclassificada em um chamado:**
GLPI guarda categoria como FK numérica (`itilcategories_id`), não como
texto — a árvore de categorias do GLPI (`ITILCategory`) tem um id próprio
por nó. Portanto:
- Precisa de um **mapa de-para "nome de categoria (texto, coluna G/O da
  planilha) → itilcategories_id (inteiro, GLPI)`**, no mesmo espírito do
  `config_categorias_canonicas.json` que já existe neste repo para
  renomeações. Esse mapa se constrói uma vez lendo
  `GET {GLPI_URL}/apirest.php/ITILCategory/?range=0-9999` (ou usando
  `completename` para casar hierarquia) e persistindo localmente.
- Escrita em si:
```
PUT {GLPI_URL}/apirest.php/Ticket/{id}
Headers: Session-Token, App-Token, Content-Type: application/json
Body: {"input": {"itilcategories_id": <id_mapeado>}}
```
- Resposta 200 com o campo atualizado confirma sucesso; 400/401/403 indicam
  erro de payload/sessão/permissão.

**4. Riscos e por que isso é mais delicado que escrever na planilha**
- O GLPI é o sistema de registro oficial da instituição — diferente da
  planilha (que é um ambiente de experimento), um erro de categoria
  escrito lá é visível para todos os usuários do GLPI e pode disparar
  regras de negócio do GLPI (SLA por categoria, notificações, etc.).
- Recomendação: só escrever de volta linhas onde **já existe conferência
  humana validada** (M/N/P/Q, conforme a mesma governança que este
  repositório já aplica para "verdade validada"), nunca a partir de uma
  classificação de IA sem revisão.
- Seguir o mesmo padrão de segurança já usado neste repo: dry-run
  obrigatório (listar o que seria escrito, sem aplicar), flag explícita de
  aplicação, log de auditoria (parecido com `LOG_COPIA_GQ` do Apps Script),
  e um "circuit breaker" por lote (não escrever mais que N tickets por
  execução, como o `maxExistingUpdatesPerRun` do Apps Script).
- GLPI tem histórico de alterações por ticket nativo (aba "Histórico" do
  chamado) — toda alteração via API já fica auditável automaticamente lá,
  o que ajuda a reverter manualmente se necessário.

**5. Onde isso entraria no repositório (esboço, não implementado)**
- Novo módulo `src/glpi_api.py` (paralelo a `src/planilha.py`): sessão,
  retry em erros transitórios (mesmo padrão de `_com_retry` já usado para
  a API do Sheets), função `atualizar_categoria_ticket(id_ticket,
  categoria_texto)`.
- Novo script `src/escrever_categoria_glpi.py`: lê linhas validadas (M/N/P
  confirmando a categoria corrigida, ou Q preenchida), aplica o mapa
  de-para, chama `glpi_api`, e reporta dry-run/aplicação como os demais
  scripts do repo.
- Novo workflow `.github/workflows/escrever_glpi.yml`,
  `workflow_dispatch`-only no início (nunca `schedule` até ganhar
  confiança), secrets `GLPI_URL`, `GLPI_APP_TOKEN`, `GLPI_USER_TOKEN`.
- Precisa de decisão explícita do Adinailson sobre: qual GLPI (produção ou
  homologação) usar primeiro, quem é o usuário de serviço, e qual o
  critério exato de "linha pronta para escrever de volta".

Nada disso foi implementado ainda — é o levantamento de viabilidade e o
esboço de arquitetura pedidos, para retomar quando o Adinailson quiser
avançar.
