# CONTEXTO — classificacao-chamados (panorama único)

> Arquivo **único** de contexto/continuidade deste repositório. Consolida e
> substitui os antigos `CONTINUIDADE_*.txt` e `PROMPT_CONTINUACAO_OUTRA_IA.txt`
> (removidos; histórico preservado no git). **Atualizar este arquivo** a cada
> etapa importante, em vez de criar arquivos novos.
>
> Última consolidação: 2026-06-04 (America/Bahia, UTC-03:00) — roteiro + Etapa 1 progressiva.

## Objetivo
Experimento controlado de **classificação e reclassificação automática de
chamados**, separado do Malha IA operacional, preservando rastreabilidade, logs,
snapshot inicial, validação humana futura e separação experimento/produção.

## 🎯 OBJETIVO FINAL (meta do projeto)
Chegar a um **modelo de IA bem treinado** que, para a **maioria das categorias**,
indique com **confiança ≥95% CALIBRADA** se a categoria de um chamado está correta
ou não. "Calibrada" = quando o modelo diz "≥95%", ele realmente acerta ~≥95% das
vezes (confiança ligada ao acerto real, não só softmax inflado). A meta não é só
acurácia média — é **confiabilidade por faixa e por categoria**.

### Estratégia — ciclo de melhoria contínua
1. Classificar (Etapa 1) → reclassificar baixa confiança (Etapa 2) → **validação
   humana** dos divergentes/duvidosos → **base validada** (`usar_para_treino=SIM`).
2. **Re-treinar** o modelo com a base validada (rótulos de maior qualidade) — etapas 41-42.
3. Repetir, **subindo a confiança calibrada e a cobertura** por categoria.

### Alavancas (acionar conforme a necessidade, guiado por dados)
- **Aumentar a capacidade do LSTM**: mais `units`/`embed_dim`/vocabulário/épocas,
  ou embeddings PT pré-treinados (parâmetros em `src/modelo_lstm.py`).
- **Reforçar a reclassificação**: lotes maiores, mais rodadas, critérios de melhoria.
- **Memória mais robusta**: a base validada cresce e vira a **memória de treino** —
  quanto mais validada, melhor o re-treino e a confiança.
- **Modelo robusto (quase-LLM local)**: roda em **baixa frequência** e **devagar**,
  só nos casos difíceis/baixa confiança, elevando a qualidade onde o LSTM não chega.

### Como medir o sucesso
- **Confiança × acerto** (Etapa 38): na faixa ≥95%, o acerto **validado** deve ser ~≥95%.
- **Cobertura**: maioria das categorias com bom desempenho (métricas por categoria).

## ⭐ FONTE DE VERDADE: roteiro metodológico (50 etapas)
O desenho do experimento segue o **"Roteiro Metodológico para Avaliação da
Evolução da Classificação e Reclassificação Automática de Chamados no Malha IA"**
(PDF do usuário, 50 etapas). Qualquer escolha técnica deve aderir a ele. Pontos
que estavam DESVIADOS e foram reconduzidos em 2026-06-04:
- **Modelos no escopo (Etapa 15):** LSTM **primário** + RF **fallback**, com
  executor por faixa (`LSTM`, `LSTM_BAIXA_CONF`, `RF_Fallback`, `RF_Fallback_BAIXA_CONF`).
  O TF-IDF+LogReg pode ser usado como **baseline comparativo**, mas NÃO é o padrão.
- **Processar em TURNOS de 15 (Etapa 10-13), progressivamente** — observar a
  evolução da concordância turno a turno e acumulada (NÃO classificar tudo de uma vez).
- **Logs/config/snapshot vão para as ABAS da planilha** (Etapas 6-9,16,18), não só
  para JSON no repo. GitHub-first = processa no GitHub e **exporta em lote para as abas**.
- **Conferência = IA × classificação ORIGINAL** (col C no layout reduzido), fórmula K
  `=SE(G="";"";G=C)` (Etapa 4). No layout de produção é Z×M; aqui original = C.
- **Limpeza inicial de G:J** antes de começar (Etapa 3) = "começar do zero".

## ⭐ ETAPA 1 PROGRESSIVA (estado atual — 2026-06-04)
Script `src/executar_etapa1.py` + workflow `etapa1_turnos.yml` (agendado `*/15`):
- A cada execução classifica só os PENDENTES (G vazia) em **turnos de 15**, até
  `--max-turnos` (padrão 60), com **LSTM** (executor por faixa) e criticidade.
- **APPEND** em `LOG_TURNOS_CLASSIFICACAO` (taxa por turno + acumulada),
  `LOG_LINHA_A_LINHA`, `SNAPSHOT_ETAPA_1`; atualiza `EXPERIMENTO_CONFIG` e
  `METRICAS_EXPERIMENTO`; grava G:J + fórmula K.
- **Todas as taxas/confianças são FRAÇÃO 0-1 formatadas como %** (corrigido o bug
  em que apareciam 100× maiores, ex.: 6000%).
- Validado no CI (run verde): modelo `LSTM_Bidirecional`, 60 turnos/run, % correto.
- Comportamento esperado: ~16 execuções para classificar os 13.801; no-op quando
  não há pendentes ("Etapa 1 concluída").
- Disparo manual: `gh workflow run etapa1_turnos.yml -f modelo=producao -f max_turnos=60`.

## 📚 Documentação do repositório
- `docs/GUIA_TECNICO.md` — o que **cada script/arquivo** faz, como funciona, com o
  que se relaciona e como executar; + significado de **G/H/I/J** e de cada
  **executor** (LSTM vs LSTM_BAIXA_CONF, por que existe baixa_conf acima de 90%).
- `dados/README.md` — schemas dos arquivos JSON.
- **Dashboard** (`docs/index.html`, GitHub Pages): abas Classificação/Categorias/
  Métricas/Modelos/Reclassificação/Documentação. Tem **filtros multi-seleção**
  (Grupo, Faixa, Executor, Situação concorda/diverge, Validação humana) que
  recalculam faixa/categorias/métricas a partir de `docs/dados/registros.json`
  (por chamado, SEM texto: linha, grupo, categoria original/IA, confiança, faixa,
  executor, concorda, validação). Gerado por `exportar_dashboard.py`. O filtro de
  Validação humana fica pronto para a comparação após a revisão manual.

> ⚠️ DADOS DINÂMICOS: `registros.json` **NÃO é fixo** (foi ~7.200 num instante, mas
> **cresce** conforme a Etapa 1 classifica mais turnos) e a **base de chamados também
> aumenta** com o tempo (sync GLPI). Nada no código deve assumir total fixo: tudo é
> recontado dinamicamente a cada execução (totais são "observados", não limites).
- Panorama GERAL do Malha IA (5 eixos, dashboards, motores) fica no repositório
  **`malha-ia`** (`contexto_projeto.txt`). Este repo é só o experimento de
  classificação/reclassificação.

## 🧪 COMPARAÇÃO MULTI-MODELO (2026-06-04) — aditivo, não altera etapa1/etapa2
Estrutura para comparar VÁRIOS modelos locais sobre o **mesmo lote** de registros
(mesma ordem), de forma progressiva. NÃO substitui o fluxo atual (LSTM/RF seguem).
- `src/modelos_zoo.py` — registro modular com interface uniforme (`criar_modelo(nome)`
  → `.fit` / `.predict_score`). Modelos leves (TF-IDF +): `naive_bayes`,
  `regressao_logistica`, `linear_svc`, `sgd`, `extra_trees`, `random_forest`; e `lstm`
  (reusa o de produção, exige TF). FastText/Transformer = extensão futura (é só
  acrescentar no zoo).
- `src/comparar_modelos_lote.py` — runner por lote. Protocolo justo: o lote de teste
  `[inicio, inicio+limite)` é o MESMO para todos; cada modelo treina na base rotulada
  **excluindo o lote** e prediz o lote. Controle: `--modelo` (ou `todos`), `--inicio`,
  `--limite`, `--executar-todos`, `--aplicar` (sem isso = dry-run).
- Métricas por modelo/lote: acurácia, F1-macro, F1-weighted, balanced accuracy,
  nº revisão (score<0,95), acerto em baixa confiança, tempo treino/inferência;
  + precision/recall/F1/suporte **por categoria**.
- Saídas (abas novas; abas atuais intactas): `COMPARACAO_MODELOS` (métricas/lote),
  `COMPARACAO_CATEGORIA` (por categoria), `COMPARACAO_PREVISOES` (por registro +
  campos VAZIOS p/ validação humana: `validacao_humana_final`, `quem_estava_correto`
  [dropdown IA/ORIGINAL/NENHUM/DUVIDOSO], `observacao_avaliador`, `data_validacao`).
- Workflow `comparar_modelos.yml` (manual; inputs modelo/inicio/limite). TF só se
  `modelo=lstm`. Concorrência `escrita-planilha` (só escreve nas abas COMPARACAO_*).
- Cuidado metodológico: a categoria ORIGINAL é referência inicial, **não verdade
  absoluta**; divergências ficam preservadas p/ auditoria/validação humana.
- 1º dry-run (lote [0:200], holdout): linear_svc acc 0,65 > logreg/rf 0,61 > sgd 0,605
  > extra_trees 0,585 > naive_bayes 0,50. (holdout estrito, fatia específica.)

## MULTIMODELO COMPLETO (2026-06-05) — classificação e reclassificação por IA
Implementado ciclo completo por modelo, ainda como fluxo manual/controlado:
- `src/classificacao_multimodelo.py` materializa `CLASSIF__<modelo>` para cada IA,
  com predição out-of-fold. A IA que rotula uma linha não treina naquela linha.
- `src/reclassificacao_multimodelo.py` reclassifica baixa confiança por modelo,
  preservando `CLASSIF__<modelo>` e gravando em `RECLASS__<modelo>`.
- `config_experimento.json` ganhou bloco `multimodelo`: modelos leves, LSTM pesado,
  K-fold, tamanho de turno 15, abas de classificação/reclassificação/métricas.
- Workflows manuais:
  - `multimodelo_classificacao.yml`
  - `multimodelo_reclassificacao.yml`
- Segurança: ambos têm input `aplicar=false` por padrão; sem aplicar, rodam dry-run.
- Perfil LSTM seguro global permanece `padrao`. O perfil `robusto` fica disponível
  por `LSTM_PERFIL=robusto` ou input `lstm_perfil`, para execuções mais lentas.

## Regras de ouro
- Não presumir totais fixos de linhas: `total_linhas_*` são **observados** na
  execução; a planilha cresce; os scripts releem a fonte.
- Colunas localizadas por **cabeçalho**, não por posição fixa.
- Linhas totalmente vazias são ignoradas.
- Escrita na planilha só com flag explícita (`--aplicar`).
- Segredos (URL/token do Web App) só em GitHub Secrets — nunca em código/commit/txt.
- Datas/horas sempre no formato `dd/mm/aaaa hh:mm` (America/Bahia).
- Faltando evidência: responder exatamente `Informação insuficiente para verificar.`

## Planilha experimental
- ID da planilha: **não versionado** (Secret/env `SPREADSHEET_ID` no CI, ou arquivo
  local `spreadsheet_id.local`). Aba `CHAMADOS_ESQUELETO_REDUZIDO`, range `A:M`.
- Colunas: A ID Chamado · B TÍTULO · C CATEGORIA COMPLETA · D DESCRIÇÃO GLPI ·
  E TÍTULO O.S.M. · F DESCRIÇÃO O.S.M. · **G Classificação IA · H Avaliação (%) ·
  I Executor · J Criticidade Atribuída por IA** · K Comparação ·
  L Classificado_Confiança_IA · M CONFERÊNCIA.
- Saída da IA = **G:J**. `M=TRUE` ⇒ não sobrescrever (revisão humana).
- Medições observadas (não fixas): ~18.859 linhas lidas, 18.858 dados,
  **13.789 não-vazias**; lastRow 18.859, lastColumn 13.
- run_id: `EXP_CLASSIFICACAO_CHAMADOS_2026_06_001`.
- Parâmetros (config_experimento.json): tamanho_lote 15; limiar_confianca_baixa 0.7;
  limiar_alta_confianca 0.95; reclassificação (desabilitada) lote 200, conf < 0.95.

## Acesso à planilha: CONTA DE SERVIÇO (gspread) — atual
Desde 2026-06-03 o acesso é via **conta de serviço Google Cloud + Sheets API
(gspread)**, no lugar do Apps Script Web App (que exigia reimplantar a cada
rotação de token).
- Projeto GCP: `classificacao-chamados`; Google Sheets API ativada.
- Conta de serviço: e-mail **não versionado** (a planilha foi compartilhada com a
  conta de serviço; a chave fica no Secret `GCP_SA_KEY`).
- A planilha foi **compartilhada com esse e-mail (Editor)**.
- Chave JSON salva em `credenciais_sa.json` na raiz — **NUNCA versionada** (.gitignore).
  Para Actions, guardar o conteúdo como Secret e recriar o arquivo no runner.
- Módulo de acesso: `src/planilha.py` (abre worksheet, lê e grava em lote).

### Apps Script (LEGADO, opcional)
`apps_script/Code.gs` (Web App com token) continua no repo, mas **não é mais usado
pelo fluxo principal**. Mantido só como alternativa/histórico.

## Abas experimentais (já criadas na planilha)
EXPERIMENTO_CONFIG · LOG_TURNOS_CLASSIFICACAO · LOG_LINHA_A_LINHA ·
SNAPSHOT_ETAPA_1 · LOG_TURNOS_RECLASSIFICACAO · VALIDACAO_HUMANA · METRICAS_EXPERIMENTO.

## Linha do tempo (resumo do que foi feito)
1. Repo criado; `validar_planilha_experimento.py` (offline + via Apps Script).
2. Web App criado e validado (`listar_abas`/`validar`/`ler`).
3. GitHub Secrets `APPS_SCRIPT_URL`/`APPS_SCRIPT_TOKEN`; token rotacionado (forte).
4. `preparar_abas_experimento.py --aplicar` criou as 7 abas experimentais.
5. `registrar_config_experimento.py --aplicar` gravou EXPERIMENTO_CONFIG (21 linhas);
   totais gravados como `*_observado` (não fixos).
6. `registrar_snapshot_inicial.py --aplicar` gravou SNAPSHOT_ETAPA_1 (13.789 linhas).
7. Seleção de lote (`classificar_lote_inicial.py`) e baseline TF-IDF+LogReg
   (`classificar_lote_baseline.py`) em **dry-run** (sem escrever G:J).
   1º lote dry-run: linhas 2–16; concordância aparente 10/15 (preliminar, não validada).
8. Ajuste de horário para America/Bahia (`formatarDataBahia_` no Code.gs).
   PENDÊNCIA: confirmar que o deploy ativo do Web App usa o Code.gs atualizado
   (SNAPSHOT_ETAPA_1 chegou a ficar com timestamp UTC `Z`).
9. **2026-06-03 — arquitetura GitHub-first, export em lote (PR #1).**

## Arquitetura atual: GitHub-first, export em lote
Processa tudo no repo (JSON em `dados/`) e toca a planilha só para **1 leitura
(snapshot) + 1 escrita (export) por etapa**, reduzindo o uso de API.

Fluxo:
```
registrar_snapshot_inicial.py -> dados/snapshot_etapa_1.json   (lê a planilha 1x)
classificar_etapa.py          -> dados/classificacao_etapa_1.json
                                 dados/log_turnos.jsonl
                                 dados/log_linha_a_linha.jsonl
                                 dados/metricas_experimento.json
exportar_etapa.py --aplicar   -> grava G:J na planilha (1 update gspread em lote)
                                 dados/manifest_exportacao.json
```
Decisões confirmadas: 6 arquivos JSON em `dados/` (schemas em `dados/README.md`);
exportação grava **G:J**; **pula M=TRUE**; **não sobrescreve célula vazia**
(preserva J/Criticidade, que o baseline não gera). Classificação é **out-of-fold**
(StratifiedKFold) para evitar vazamento. Nenhum script escreve sem `--aplicar`.
Acesso à planilha via conta de serviço (`src/planilha.py`).

### Execução validada (2026-06-03, planilha real)
snapshot: 18.858 linhas (13.801 com categoria+texto, elegíveis) ·
classificação baseline TF-IDF+LogReg out-of-fold: **concordância 11.625/13.801 =
84,23%** (acc 0,8423 · F1-macro 0,8386) ·
export: **13.801 linhas gravadas em G2:J13802 numa única escrita em lote**, 0 puladas.

> Os arquivos `dados/*.json` e `*.jsonl` contêm texto real de chamados e estão
> no `.gitignore` (repo público). Não versionar.

## Arquivos do repositório
- `src/validar_planilha_experimento.py` — validação de cabeçalho/linhas (offline e via Web App).
- `src/preparar_abas_experimento.py` — cria abas experimentais (`--aplicar`).
- `src/registrar_config_experimento.py` — grava EXPERIMENTO_CONFIG (`--aplicar`).
- `src/planilha.py` — acesso à planilha via conta de serviço (abrir, ler, exportar lote).
- `src/registrar_snapshot_inicial.py` — lê a planilha (gspread) e gera `dados/snapshot_etapa_1.json`.
- `src/classificar_lote_inicial.py` — seleção de lote em dry-run (legado, via Apps Script).
- `src/classificar_lote_baseline.py` — baseline TF-IDF+LogReg em dry-run (legado, via Apps Script).
- `src/classificar_etapa.py` — classificação github-first (lê snapshot, grava JSON); modos full/incremental/reclassificacao.
- `src/exportar_etapa.py` — exportação em lote G:J via gspread + manifest.
- `apps_script/Code.gs` — Web App (LEGADO; inclui `exportar_lote`, não usado pelo fluxo atual).
- `credenciais_sa.json` — chave da conta de serviço (gitignored, NUNCA versionar).
- `dados/README.md` — schemas dos 6 arquivos JSON.
- `tests/test_github_first.py` — testes sem rede.
- `config_experimento.json`, `requirements.txt`, `AGENTS.md`, `README.md`.

## Comandos úteis
```bash
# validação de sintaxe
python -m py_compile src/classificar_etapa.py src/exportar_etapa.py src/registrar_snapshot_inicial.py
python tests/test_github_first.py

# fluxo real (conta de serviço: credenciais_sa.json na raiz)
python src/registrar_snapshot_inicial.py                 # snapshot JSON (1 leitura)
python src/classificar_etapa.py --modo incremental       # só linhas novas (cron)
#   modos: full (out-of-fold, base toda) | incremental (só G vazio) | reclassificacao
python src/exportar_etapa.py                 # dry-run do lote
python src/exportar_etapa.py --aplicar       # 1 escrita em lote (G:J)
```

### Etapa 2 — Reclassificação (`--modo reclassificacao`)
Reavalia linhas já classificadas com **baixa confiança** (< `reclassificacao.
selecionar_confianca_menor_que`, padrão 0,95), até `tamanho_lote` (200),
pulando `CONFERÊNCIA=TRUE`. Treina na base rotulada, reprediz e só sobrescreve
quem **melhora** (confiança nova > antiga + 0,05, ou categoria muda com
confiança ≥). Com o mesmo modelo e sem dados novos, é **no-op** (nada melhora);
passa a agir quando a base cresce. Disponível também no workflow (dispatch manual).

## Comparação de modelos (2026-06-04) — baseline vence
Holdout estratificado 80/20 (11.039 treino / 2.760 teste, 52 classes):
- baseline TF-IDF + LogReg: **77,57%** concordância · acc 0,7757 · F1-macro 0,5916
- LSTM Bidirecional (sem class_weight): 75,04% · acc 0,7504 · F1-macro 0,3336
- LSTM Bidirecional (com class_weight): 69,35% · acc 0,6935 · F1-macro 0,4718

O LSTM (arquitetura espelhada do motor de produção, treinada do zero) NÃO superou
o baseline nesta base (média, 52 classes desbalanceadas, textos curtos). Decisão:
**manter o baseline** no fluxo/cron. Scripts: `src/modelo_lstm.py` (BiLSTM, persiste
modelo) e `src/comparar_modelos.py` (requer `tensorflow`, não usado pelo cron).
Trabalho futuro: embeddings PT pré-treinados + tuning (payoff incerto).

## Pendências (próximos passos do roteiro)
1. (FEITO 2026-06-04) **Etapa 2 (reclassificação)** — `src/executar_etapa2.py` +
   `etapa2_reclassificacao.yml`: progressiva, antes/depois, **ganho líquido**, aba
   `LOG_TURNOS_RECLASSIFICACAO`, executor `Reclass_<tag>`. Dry-run validado.
2. (FEITO 2026-06-04) **3º modelo "quase-LLM" local** — `src/classificador_robusto.py`
   (embeddings de transformer multilíngue + LogReg; fallback LSTM) usado em
   `reclassificacao_robusta.yml` (a cada 6h, poucos chamados). `requirements-robusto.txt`.
3. Validação humana + métricas finais (etapas 24-50): `VALIDACAO_HUMANA`
   (IA_CERTA/GLPI_CERTO/AMBOS_ERRADOS/CASO_AMBIGUO/NAO_AVALIADO, usar_para_treino),
   matriz de confusão, métricas por categoria, indicadores consolidados, gráficos.
4. (Opcional) Métricas por faixa/executor ACUMULADAS na aba (hoje METRICAS guarda
   global acumulada + faixas do último lote).
5. Remover o Apps Script legado (`apps_script/Code.gs`) quando não for mais útil.

> Nota sobre modelos: o teste LSTM×baseline (abaixo) mediu o **baseline melhor**,
> mas o **roteiro (Etapa 15) manda LSTM primário + RF fallback** (paridade com a
> produção). Por isso o fluxo usa LSTM; o baseline fica como comparação/fallback.

## Registro de correção do painel/documentação (2026-06-05)
Correções aplicadas no site e na documentação após análise do repositório e do
GitHub Pages:

1. `docs/index.html` deixou de usar **Malha IA** como nome principal do site.
   O painel agora identifica o projeto como **Classificacao de Chamados - Painel
   Experimental**. Malha IA permanece apenas como contexto de origem.
2. O painel passou a exibir aviso explícito de **experimento em andamento** quando
   houver pendentes publicados em `docs/dados/metricas_experimento.json`.
3. O painel ganhou aba **Documentacao**, com explicação de escopo, fluxo, fontes
   de dados, indicadores, faixas de confiança, executor, ganho líquido e validação
   humana.
4. O painel ganhou aba **Metricas**, tabela de métricas consolidadas, resumo
   técnico e leitura analítica.
5. A aba de categorias foi ampliada com tabelas de maiores volumes e menor
   concordância, além da tabela completa filtrável.
6. A aba de reclassificação passou a mostrar tabela dos turnos, além dos gráficos.
7. A identidade visual foi ajustada para um padrão mais institucional e técnico:
   fundo claro, painéis neutros, acentos em verde/teal/azul/âmbar/vermelho, bordas
   de 6 px e tipografia mais sóbria.
8. `README.md` foi reescrito para refletir o fluxo atual por **conta de serviço
   gspread**, deixando `apps_script/Code.gs` apenas como legado.

Validação local desta correção:
- `python -m py_compile` nos scripts principais: OK.
- `python tests/test_github_first.py`: não executou no ambiente local por falta de
  `numpy`; instalar dependências ou rodar no GitHub Actions antes de declarar a
  suíte aprovada.

Próximo passo oficial depois desta correção:
1. Executar/preparar a **VALIDACAO_HUMANA** (`src/preparar_validacao_humana.py` ou
   workflow `preparar_validacao.yml`), priorizando divergentes e baixa confiança.
2. Após validação humana, calcular matriz de confusão, métricas por categoria,
   confiança calibrada por faixa e indicadores finais.

## Registro de execução da validação humana (2026-06-05)
Workflow executado: `preparar_validacao.yml`

Parâmetros:
- `modo=divergentes`
- `max=0`
- `forcar=nao`

Resultado verificado no GitHub Actions:
- run: `26987937701`
- status: `success`
- aba destino: `VALIDACAO_HUMANA`
- casos selecionados: `1654`
- gravação: `OK: 1654 casos gravados em VALIDACAO_HUMANA (com dropdowns).`

Próximo passo agora:
1. Revisar manualmente os 1.654 casos em `VALIDACAO_HUMANA`.
2. Preencher `categoria_validada`, `decisao`, `justificativa`, `avaliador`,
   `data_validacao` e `usar_para_treino`.
3. Depois da validação humana, calcular matriz de confusão, métricas por categoria,
   indicadores por faixa de confiança e confiabilidade/calibração da confiança.

## Redirecionamento antes da validação manual (2026-06-05)
Decisão do usuário: **não iniciar a validação humana agora**. A aba
`VALIDACAO_HUMANA` já está preparada, mas a etapa manual fica pausada até o
modelo e os scripts serem fortalecidos.

Arquivo criado para registrar a meta em formato `.txt`:
- `OBJETIVO_FINAL_MODELO_IA.txt`

Implementações aplicadas antes da validação manual:
1. `src/modelo_lstm.py` passou a aceitar perfis configuráveis de LSTM. O perfil
   `robusto` aumenta vocabulário, comprimento de sequência, embedding, unidades,
   camadas, épocas e paciência.
2. `src/classificador_producao.py` passou a receber `lstm_config` e treinar o
   LSTM com os parâmetros definidos em `config_experimento.json`.
3. `src/memoria_validada.py` foi criado para ler a aba `VALIDACAO_HUMANA` e usar
   apenas linhas com `categoria_validada` preenchida e `usar_para_treino=SIM`.
   Enquanto não houver validação humana, retorna memória vazia e não altera o
   treino.
4. `src/executar_etapa1.py` e `src/executar_etapa2.py` passaram a carregar a
   memória validada quando ela existir e a reforçar o treino com peso configurável.
5. `src/executar_etapa2.py` passou a ordenar candidatos por menor confiança antes
   de reclassificar, priorizando os casos mais incertos.
6. `src/classificador_robusto.py` passou a respeitar o perfil LSTM configurado
   quando o transformer local não estiver disponível e precisar cair no fallback.
7. `config_experimento.json` passou a documentar `objetivo_final`, `modelo_ia` e
   `memoria_validada`.

Próximo passo recomendado agora:
1. Validar sintaxe e testes.
2. Rodar um dry-run local/CI da Etapa 2 com `--modelo robusto` ou `--modelo producao`
   sem avançar validação humana.
3. Publicar essas alterações no GitHub.
4. Só depois decidir se a reclassificação robusta deve rodar manualmente ou em
   baixa frequência.

## Workflow seguro de dry-run da reclassificação (2026-06-05)
Criado `.github/workflows/reclassificacao_dry_run.yml` para testar a Etapa 2 sem
gravar na planilha. O workflow:
- usa conta de serviço apenas para leitura;
- aceita `modelo=producao`, `baseline` ou `robusto`;
- aceita `max_turnos`;
- executa `src/executar_etapa2.py` **sem `--aplicar`**.

Uso recomendado antes de qualquer nova escrita automática:
`gh workflow run reclassificacao_dry_run.yml -f modelo=producao -f max_turnos=2`

Observação de execução:
- Run `26988684880` foi disparado em `2026-06-05` com o perfil LSTM robusto ainda
  como padrão e precisou ser cancelado por demora excessiva para um dry-run rápido.
- Ajuste aplicado: `config_experimento.json` voltou a usar `perfil=padrao`, o
  perfil `robusto` permanece disponível e pode ser acionado por `LSTM_PERFIL` ou
  pelo input `lstm_perfil` do workflow dry-run.
- Run `26989026037` executou dry-run com sucesso e sem gravação, mas revelou que
  `LSTM_PERFIL` deixava a chave `perfil` sobrar nos parâmetros do LSTM, causando
  fallback para RF. Correção aplicada em `src/modelo_lstm.py`: remover `perfil`
  do dicionário antes de aplicar override por variável de ambiente.
- Run `26989233293` executou dry-run com sucesso e sem gravação, mas revelou que
  a chave documental `perfil_robusto_disponivel` também chegava ao construtor do
  LSTM. Correção aplicada: `resolver_parametros_lstm()` agora filtra apenas chaves
  válidas de arquitetura/treino.
- Run `26989390183` executou dry-run final com `modelo=producao`,
  `max_turnos=2`, `lstm_perfil=padrao`. Resultado: LSTM treinou sem fallback por
  erro de parâmetros; `memoria_validada=0`; `candidatos_reclass=4632`; lote de 30;
  `corrigidos=7`, `prejudicados=6`, `GANHO_LIQUIDO=1`; modo dry-run, sem gravação.

## Registro operacional — 2026-06-05
- Verificado o ponto crítico do texto de treino: os fluxos de classificação e
  reclassificação usam a concatenação de `TÍTULO` (B), `DESCRIÇÃO GLPI` (D),
  `TÍTULO O.S.M.` (E) e `DESCRIÇÃO O.S.M.` (F). A coluna `titulo` no
  `LOG_LINHA_A_LINHA` é apenas um resumo/auditoria; não significa treino só pelo
  título. Por isso não foi feito reset por suspeita de treino incompleto.
- Dashboard: filtros ajustados para recalcular também cards superiores, aviso e
  resumo técnico, além das tabelas e gráfico de faixa.
- Planilha: fórmula descritiva da coluna L (`Classificado_Confiança_IA`) aplicada
  em `CHAMADOS_ESQUELETO_REDUZIDO!L2:L18859`, contemplando `LSTM`, `RF_Fallback`,
  `*_BAIXA_CONF`, `Reclass_*`, baseline e modelos multimodelo.
- Abas multimodelo criadas com cabeçalhos: `CLASSIF__*`, `RECLASS__*`,
  `MULTIMODELO_TURNOS`, `MULTIMODELO_METRICAS` e `MULTIMODELO_RECLASS_TURNOS`.
  A primeira tentativa bateu limite de cota do Sheets e foi retomada após aguardar
  a janela de escrita; conferência final indicou que todas existem.

## Reset e retomada automática — 2026-06-05
- Reset completo executado a pedido do usuário: `CHAMADOS_ESQUELETO_REDUZIDO!G:K`
  limpo, preservando categoria histórica (C), fórmula descritiva (L) e conferência
  manual (M).
- Abas experimentais e multimodelo limpas: logs, snapshot, métricas,
  `COMPARACAO_*`, `CLASSIF__*`, `RECLASS__*`, `MULTIMODELO_*`.
- `src/resetar_experimento.py` atualizado para incluir abas multimodelo no reset.
- `dashboard.yml` atualizado para rodar automaticamente após conclusão bem-sucedida
  de Etapa 1, Etapa 2, comparação de modelos, multimodelo e reset.
- Dashboard regenerado com estado zerado (`registros=0`) antes do disparo das novas
  rodadas.
