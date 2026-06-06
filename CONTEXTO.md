# CONTEXTO — classificacao-chamados (panorama único)

> Arquivo **único** de contexto/continuidade deste repositório. Consolida e
> substitui os antigos `CONTINUIDADE_*.txt` e `PROMPT_CONTINUACAO_OUTRA_IA.txt`
> (removidos; histórico preservado no git). **Atualizar este arquivo** a cada
> etapa importante, em vez de criar arquivos novos.
>
> Última consolidação: 2026-06-06 (America/Bahia, UTC-03:00) — Etapa 1 CONCLUÍDA (0 pendentes),
> dashboard atualizado, robustez de workflows, estatística não paramétrica explícita e plano
> de calibração. Ver a última seção deste arquivo para o estado final.

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

## Correção de quota do dashboard — 2026-06-05
- Após a primeira rodada, um disparo automático do dashboard falhou por cota 429
  de leitura do Google Sheets.
- Correção aplicada: `src/exportar_dashboard.py` ganhou retentativas com espera
  progressiva para falhas transitórias de API.
- `dashboard.yml` passou a enfileirar atualizações do dashboard sem cancelar uma
  execução em curso.

## Execuções após reset — 2026-06-05 04:31
- Reset completo aplicado e confirmado antes da retomada das classificações.
- Etapa 1 foi executada em rodadas sucessivas, com dashboard automático após cada
  finalização bem-sucedida.
- Estado publicado no dashboard em `docs/dados/resumo.json`: 6.300 registros,
  420 turnos de classificação, 48 categorias em métricas e calibração total de
  6.300 registros (`ece_historico=0.0645`, sem validação humana).
- Comparação de modelos publicada em 5 recortes completos de 200 registros:
  `0-200`, `200-400`, `400-600`, `600-800` e `800-1000`, totalizando 35 linhas
  comparativas (`naive_bayes`, `regressao_logistica`, `linear_svc`, `sgd`,
  `extra_trees`, `random_forest`, `lstm`).
- Observação de evidência: nos cinco recortes publicados até aqui, os modelos
  lineares/TF-IDF superaram o LSTM em acurácia; o LSTM ainda não atingiu o
  patamar objetivo de confiança/acurácia para uso automático sem revisão.

## Materialização multimodelo — 6 leves completos (2026-06-05, run 27026217228)
- `multimodelo_classificacao.yml` (modelos=leves, max_turnos=0, aplicar=true) rodou
  out-of-fold em TODA a base: cada IA classificou **13.825** linhas, **0 pendentes**,
  método `kfold_5`, 922 turnos/modelo.
- Concordância vs histórico (OOF, honesta): linear_svc **80,3%** > extra_trees 78,5%
  > sgd 77,5% > random_forest 76,8% > regressao_logistica 76,6% > naive_bayes 70,1%.
  O linear_svc supera o LSTM da Etapa 1 (77,65%).
- Dashboard: aba **Multimodelo** mostra tabela de progresso + **curva de evolução da
  concordância acumulada por turno, uma por IA** (lê `multimodelo_turnos.json`).
- Corrigido overflow horizontal do painel (min-width:0 em grid/card/kpi; canvas max-width).
- **Falta**: LSTM (modelos=pesados) e reclassificação multimodelo.

## Correção do dashboard (P0) — 2026-06-05 (commit e8df9b2)
- Filtros: chips dos filtros ativos (removíveis), botões destacados, Limpar com
  contagem; rótulos explícitos "série temporal não usa filtros" vs "recalcula com filtros".
- Aba **Modelos**: deixou de usar só a última execução por modelo; agora mostra
  **média por modelo** (todos os recortes) + **ranking** + **evolução por lote**.
- Nova aba **Multimodelo**: progresso/concordância por IA + reclassificação (estado
  vazio quando não materializado). Já populada: 6 leves com ~60 linhas cada (OOF kfold_5).
- **Metricas**: banner de honestidade (`validados=0`, concordância vs histórico) +
  status da meta ≥95% ("aprovado vs histórico, NÃO validado, NÃO liberado").
- **Reclassificação**: aviso "Etapa 2 não executada após o reset".
- `exportar_dashboard.py`: publica `comparacao_categoria` (819) + `multimodelo_turnos/
  metricas/reclass_turnos`. NÃO exporta `COMPARACAO_PREVISOES`/`CLASSIF__*` crus
  (contêm título do chamado = texto; repo público). Dashboard run `27025224132` OK.
- Pendência: UI de comparação por categoria/modelo (consumir `comparacao_categoria.json`).

## Continuidade para Claude — 2026-06-05 11:55
- **Pendências/próximos passos consolidados em `FALTA_FAZER.md`** (substitui o
  antigo handoff `CLAUDE_CONTINUACAO_2026-06-05.md`, removido). Ordem: P0 painel →
  P1 materializar multimodelo → P2 workflows → P3 calibração → P4 validação humana.
- Estado mais recente do dashboard após `git pull --rebase`: `docs/dados/resumo.json`
  com `gerado_em=05/06/2026 11:55`, `registros=8100`,
  `log_turnos_classificacao=540`, `metricas_por_categoria=49`,
  `comparacao_modelos=35`, `calibracao.total=8100`, `ece_historico=0.0537`,
  `validados=0`.
- `docs/dados/metricas_experimento.json` indica `processados_acumulado=8100`,
  `pendentes_restantes=5725`, `concordancia_acumulada_global=0.7765` e modelo
  `LSTM_Bidirecional`.
- Run manual `27001950857` da Etapa 1 falhou antes de executar o script por
  download incompleto de `tensorflow==2.17.0` no `pip`
  (`IncompleteRead`, exit code 2). Não foi erro de lógica do classificador.
  Execuções agendadas posteriores continuaram e avançaram o experimento.
- Correção necessária de workflow: adicionar cache/retry de `pip`, separar
  dependências leves de TensorFlow quando possível e reduzir chance de falha por
  download grande.
- Problema do dashboard a corrigir: a aba `Modelos` usa apenas a última execução
  por modelo no gráfico (`ult[r.modelo]=r`), escondendo os recortes anteriores.
  Deve mostrar médias, ranking, evolução por lote e todos os recortes.
- Problema do dashboard a corrigir: `exportar_dashboard.py` não publica
  `COMPARACAO_CATEGORIA`, `COMPARACAO_PREVISOES` nem as abas multimodelo
  (`MULTIMODELO_*`, `CLASSIF__*`, `RECLASS__*`). O painel, portanto, não mostra
  tudo que o experimento já produz.
- Problema do dashboard a corrigir: deixar muito explícito que `validados=0` e
  que as métricas atuais são concordância contra histórico, não acerto validado
  humanamente.

## Execucao pos-Claude - 2026-06-05 13:48

- Verificado run `27026916670`: `Multimodelo - classificacao completa` concluiu com sucesso.
- As 7 IAs estao materializadas com 13.825 registros por modelo e 0 pendentes.
- `src/analise_estatistica.py` foi executado localmente com `PYTHONPATH=.codex_deps` e gerou `docs/dados/estatistica.json` para 13.825 linhas comuns e 7 modelos.
- `docs/index.html` ganhou aba `Estatistica`, consumindo `estatistica.json`, e seletor no grafico de modelos para acuracia/F1 por lote e acumulados.
- Criado workflow `.github/workflows/estatistica.yml` para recalcular estatistica manualmente ou apos `Multimodelo - classificacao completa`.
- Criado `requirements-estatistica.txt` para dependencias estatisticas sem pesar o dashboard de 30 em 30 minutos.
- Criado `DOCUMENTACAO_MODELOS_E_ESTATISTICA.md` e PDFs em `docs/ESTADO_DO_ROTEIRO.pdf` e `docs/DOCUMENTACAO_MODELOS_E_ESTATISTICA.pdf`.
- Reclassificacao segue sem prioridade por decisao do usuario; proximo foco e estatistica/documentacao/dashboard.

## Correcao metodologica do dashboard - Classificacao x Modelos (2026-06-05)

- A tentativa de usar registros multimodelo na aba `Classificacao` foi removida, porque multiplicava chamados por 7 e podia exibir 96.775 predicoes como se fossem chamados.
- A aba `Classificacao` voltou a usar somente `docs/dados/registros.json`, isto e, Etapa 1/LSTM. Filtros dessa aba nao comparam modelos.
- A aba `Modelos` passou a usar a materializacao completa das 7 IAs (`multimodelo_metricas` e `multimodelo_turnos`) como comparacao principal: 13.825 chamados por modelo, out-of-fold.
- Os 5 recortes de 200 registros (`COMPARACAO_MODELOS`, total 1.000 por modelo) ficam apenas como recorte piloto/amostral, nao como resultado principal.
- Normalidade: como Shapiro rejeitou normalidade a 5%, a analise deve assumir pressupostos nao parametricos: Spearman, Friedman/Nemenyi, McNemar/Cochran Q e bootstrap. Nao usar inferencia parametrica como criterio principal.

## Etapa 1 CONCLUIDA + robustez de workflows + calibracao (2026-06-06 03:1x, America/Bahia)

Estado final apos a Etapa 1 zerar:

- **Etapa 1 / LSTM CONCLUIDA**: run manual `27051019863` (workflow `etapa1_turnos.yml`)
  classificou os ultimos **325** chamados -> **0 pendentes**. Base elegivel = **13.825**,
  todos classificados. `log_turnos_classificacao=922`.
- **Dashboard atualizado**: `dashboard.yml` rodou via `workflow_run` (`27051075802`) e
  manual (`27051109204`). `docs/dados/resumo.json` agora: `registros=13825`,
  `calibracao.total=13825`, `ece_historico=0.0379`, `validados=0`,
  `log_turnos_reclassificacao=0`. Pendentes = 0.
- **7 IAs materializadas** (estado mantido, out-of-fold `kfold_5`, 13.825 cada):
  linear_svc 80,26% > extra_trees 78,47% > sgd 77,51% > random_forest 76,80% >
  regressao_logistica 76,59% > naive_bayes 70,07% > lstm 67,57%.
- `Classificacao` = Etapa 1/LSTM (`registros.json`). `Modelos`/`Multimodelo`/`Estatistica`
  = comparacao das 7 IAs. `multimodelo_registros.json` permanece removido (nao recriar).

Documentacao:

- `FALTA_FAZER.md`: corrigido o "Estado atual" (estava em ~8.100/5.725 pendentes e dizia
  que o multimodelo nao tinha rodado); P1/P6 marcados como concluidos (7 IAs, incl. LSTM);
  P5 (estatistica) e P2 (etapa1 ja robusto) atualizados.
- `README.md`: secao das 7 IAs (tabela de concordancia), distincao das abas, lista
  completa dos JSONs consumidos pelo painel, nota de pressupostos nao parametricos.

Robustez de workflows (P2): alem do `etapa1_turnos.yml` (ja robusto), aplicado
`cache: pip` + `pip install --retries 5 --timeout 120` em `multimodelo_reclassificacao.yml`
(alvo principal), `etapa2_reclassificacao.yml`, `reclassificacao_robusta.yml`,
`classificacao_incremental.yml`, `dashboard.yml`, `preparar_validacao.yml`, `resetar.yml`.

Estatistica (nao parametrica, explicita): `src/analise_estatistica.py` ganhou bloco
`pressupostos` no JSON (normalidade rejeitada nos 7 modelos -> assume nao parametrico;
base de comparacao = historico, nao validacao humana) e `observacao` reforcada. Os metodos
ja eram nao parametricos (Spearman, Friedman/Nemenyi, Cochran Q, McNemar, bootstrap, Kappa).

Calibracao (plano inicial): criado `PLANO_CALIBRACAO.md` (CalibratedClassifierCV/Platt p/
linear_svc e demais lineares TF-IDF; isotonica p/ arvores/NB; temperature scaling separado
p/ o LSTM; out-of-fold; linear_svc como candidato principal; nada de producao sem validacao
humana). `src/calibracao.py` passou a marcar no JSON que a confianca e **bruta, nao
calibrada** (`tipo_confianca`, `calibrador_ajustado=false`, `plano_calibracao`).

Reclassificacao multimodelo: continua **nao executada** (so dry-run apos tudo acima). A
validacao humana permanece **pausada** por decisao do usuario.

Validacoes locais OK: `py_compile` dos modulos-chave + `tests/test_github_first.py` (4 ok).

Run IDs (2026-06-06): Etapa 1 final `27051019863`; dashboard `27051075802`/`27051109204`;
estatistica (regenerou `estatistica.json` com bloco `pressupostos`) `27051205684`;
dry-run reclassificacao `27051252248`. Pages publicado e conferido ao vivo:
`registros=13825`, `validados=0`, `estatistica.gerado_em=06/06 00:22`, `assume=nao_parametrico`.

### Dry-run da reclassificacao multimodelo (leves, max_turnos=1, aplicar=false) — `27051252248`

Resultado (1 turno de 15 por modelo, **nada aplicado**): ganho liquido **nulo ou negativo**.

| Modelo | corrigidos | prejudicados | GANHO |
|---|---|---|---|
| naive_bayes | 0 | 0 | 0 |
| regressao_logistica | 0 | 1 | -1 |
| linear_svc | 0 | 2 | -2 |
| sgd | 1 | 1 | 0 |
| extra_trees | 1 | 2 | -1 |
| random_forest | 3 | 3 | 0 |

Total: 90 reclassificacoes simuladas, **corrigidos=5 / prejudicados=9 (liquido -4)**.
**Conclusao: NAO aplicar reclassificacao em massa agora** — nao ha ganho liquido contra
o historico. Observacao relevante: `candidatos_baixa` cobre quase toda a base nos modelos
lineares (linear_svc=13825, regressao_logistica=12358), porque a "baixa confianca" usa a
saida BRUTA (decision_function/softmax). Isso reforca o `PLANO_CALIBRACAO.md`: sem confianca
**calibrada**, o filtro de baixa confianca da reclassificacao perde sentido. Proximo passo
tecnico recomendado: calibrar por modelo (comecar por linear_svc) antes de qualquer Etapa 2
em massa; validacao humana segue pausada.

## Feedback do usuario — UI, seletor de modelo, tiling e robusto (2026-06-06 ~03:40-04:15)

Pedidos do usuario atendidos nesta rodada:

- **Seletor de Modelo na aba Classificacao**: novo `<select>` troca a aba para as predicoes
  de UMA IA por vez (out-of-fold), 13.825 linhas, nunca os 7 somados. `exportar_dashboard.py`
  passou a exportar `registros_<modelo>.json` (sem texto/ID) das abas `CLASSIF__<modelo>`;
  `resumo.registros_modelos` lista os 7. Dados reais conferidos (linear_svc 80,26%, lstm
  67,57% etc.). **Por que so havia LSTM antes**: a aba Classificacao e a Etapa 1/LSTM oficial
  (RF_Fallback so dispara se o LSTM falhar, o que nunca ocorreu).
- **Grafico "Evolucao da concordancia por turno" acompanha o modelo** escolhido (usa
  `multimodelo_turnos` filtrado por modelo; Etapa 1 usa `log_turnos_classificacao`).
- **Recortes 0-1000 -> base completa**: `comparar_modelos_lote.py` ganhou modo `--passo`
  (tiling held-out que SUBSTITUI `COMPARACAO_MODELOS`/`_CATEGORIA` via `escrever_aba`).
  Rodado com passo=1000 (run `27051714113`): `COMPARACAO_MODELOS=84` (14 janelas x 6 leves,
  0-13825). LSTM fica de fora do tiling por custo (segue na visao out-of-fold). Nao grava
  `COMPARACAO_PREVISOES` no tiling. A gravacao so ocorre no fim (falha no meio = tabela
  antiga intacta).
- **Modelo robusto RELIGADO**: `reclassificacao_robusta.yml` voltou ao schedule (cron
  `0 */6`), agora que a Etapa 1 concluiu. Aplica reclassificacao (poucos chamados por vez).
- **UI**: cor secundaria verde -> AZUL (`--teal #1d4ed8`, `--green #2563eb`); removida a nota
  "fonte: Etapa 1/LSTM"; removidas as referencias a Malha IA (eyebrow e docs); tabela de
  modelos compacta sem scroll horizontal.
- **Estatistica**: parou de dizer "normal? sim/nao"; afirma uso SO de testes nao-parametricos
  + **histograma de normalidade** (concordancia por turno) na aba Estatistica.
- **Documentacao rica**: aba Documentacao com TF-IDF + 1 card por modelo (equacao, analogia
  em celulas de Excel, referencias bibliograficas).
- **Workflows**: actions bumpadas para `checkout@v6`/`setup-python@v6` (fim do Node 20);
  `dashboard.yml` com push resiliente (`pull --rebase --autostash` + retry) — antes falhava
  por corrida de push (run `27052207833`).

Commits: a9b1ede, bd73e45, e10941e, a562cf3, d911611/b5eaed2, ca8dceb. Painel verificado no
preview (troca de modelo, normalidade, docs sem overflow, cor azul) e no `main` via raw.
Pendencias inalteradas: validacao humana pausada; calibracao por modelo e o proximo passo.

## Atualizacao Codex - diagnostico de calibracao por IA (2026-06-06 01:37)

Estado verificado apos pull do `main`: ultimos commits do Claude presentes ate `080a311`
(`dados do dashboard [skip ci]`). Worktree local tinha apenas `.claude/` nao versionado antes
desta rodada. A execucao automatica de continuidade foi configurada no Codex com heartbeat
de 20 minutos (`continuar-classificacao-chamados`); a ferramenta permite apenas um heartbeat
ativo por thread, portanto o disparo separado fixo de 05:15 nao foi criado em paralelo.

Novo passo executado sem iniciar validacao humana e sem aplicar reclassificacao:

- Criado `src/calibracao_modelos.py`, diagnostico read-only de calibracao por IA a partir de
  `docs/dados/registros_<modelo>.json`.
- `src/exportar_dashboard.py` agora gera `docs/dados/calibracao_modelos.json` automaticamente
  depois de exportar os sete arquivos `registros_<modelo>.json`.
- `docs/index.html` ganhou tabela "Diagnostico de calibracao por IA" na aba `Metricas`, com
  ECE, Brier, acerto historico, confianca media e faixa >=95% por IA.
- Ranking da faixa >=95% exige suporte minimo (`suporte_minimo_faixa_95=138`) para evitar
  destacar modelo com poucos casos (ex.: 3 linhas).

Resultado local preliminar contra historico (`docs/dados/calibracao_modelos.json`, gerado em
06/06/2026 01:37):

| modelo | acerto_hist | ECE | Brier | >=95% n | >=95% acerto_hist |
|---|---:|---:|---:|---:|---:|
| lstm | 0,6757 | 0,0102 | 0,1272 | 4.276 | 0,9827 |
| naive_bayes | 0,7007 | 0,0363 | 0,1396 | 5.784 | 0,9355 |
| extra_trees | 0,7847 | 0,0753 | 0,1274 | 4.666 | 0,9940 |
| random_forest | 0,7680 | 0,1227 | 0,1485 | 3.879 | 0,9979 |
| regressao_logistica | 0,7659 | 0,2540 | 0,2260 | 1.467 | 0,9980 |
| sgd | 0,7751 | 0,3172 | 0,2560 | 3 | 1,0000 |
| linear_svc | 0,8026 | 0,7101 | 0,6479 | 0 | 0,0000 |

Leitura tecnica: `linear_svc` continua melhor em concordancia global, mas sua confianca bruta
nao serve como criterio direto (`decision_function` normalizada, ECE muito alto e nenhuma linha
na faixa >=95%). `lstm` tem menor ECE, mas menor acerto global. `regressao_logistica`,
`random_forest` e `extra_trees` mostram faixas >=95% fortes contra historico, mas isso ainda
nao e acerto validado. Proximo passo recomendado permanece: ajustar calibrador real por modelo
(Platt/CalibratedClassifierCV para lineares; isotonica para arvores/NB; temperature scaling para
LSTM) antes de qualquer reclassificacao em massa.

Validacoes locais desta rodada:

- `python -m py_compile src\calibracao_modelos.py src\exportar_dashboard.py src\calibracao.py src\analise_estatistica.py`
- JavaScript de `docs/index.html` extraido e validado com `node --check`.
- `PYTHONPATH=.codex_deps python tests\test_github_first.py` -> 4 testes OK.

Publicacao: commit `125f5bb` enviado ao `main`; workflow `dashboard.yml` disparado manualmente
no run `27052859362` e concluido com sucesso. O workflow gerou novo commit de dados
`0c1be12`, atualizando `docs/dados/calibracao.json`, `docs/dados/calibracao_modelos.json` e
`docs/dados/resumo.json`. Pages build `27052867799` iniciou em seguida; pode haver cache de
borda por alguns minutos no GitHub Pages.

## Atualizacao Codex - trava de seguranca da reclassificacao robusta (2026-06-06 01:54)

Ao revisar os proximos passos, foi encontrada uma inconsistencia: o projeto havia concluido
que a reclassificacao nao deveria ser aplicada em massa antes da calibracao (dry-run
`27051252248`: corrigidos=5, prejudicados=9, liquido=-4), mas
`.github/workflows/reclassificacao_robusta.yml` ainda estava com `schedule` a cada 6h e
passava `--aplicar`, escrevendo na planilha automaticamente.

Correcao aplicada: removido o `schedule` do workflow robusto; mantido apenas
`workflow_dispatch`, com input `aplicar` booleano default `false`. A etapa agora roda
em dry-run por padrao e so grava na planilha se `aplicar=true` for escolhido manualmente.
Isso preserva a regra atual: sem reclassificacao automatica antes de calibracao por modelo
e sem validacao humana sem pedido explicito.

## Atualizacao Codex - Etapa 2 manual em dry-run por padrao (2026-06-06 02:13)

Nova revisao de workflows confirmou que `.github/workflows/etapa2_reclassificacao.yml` ainda
chamava `src/executar_etapa2.py` com `--aplicar` sempre que o workflow manual fosse disparado.
Como a reclassificacao esta sem prioridade e o dry-run anterior teve ganho liquido negativo,
isso foi alterado para evitar gravacao acidental.

Correcao aplicada: adicionado input `aplicar` booleano default `false`; o workflow agora roda
sem `--aplicar` por padrao e so escreve na planilha quando `aplicar=true` for escolhido
explicitamente. `multimodelo_reclassificacao.yml` e `reclassificacao_robusta.yml` ficam
alinhados: ambos tambem usam dry-run por padrao.

## Atualizacao Codex - calibracao escalar ajustada (2026-06-06 02:35)

Proximo passo tecnico executado sem acessar validacao humana e sem escrever na planilha:
criado `src/calibracao_confianca.py`, que calibra a decisao operacional
`P(previsao correta | confianca_bruta)` para cada IA, usando somente
`docs/dados/registros_<modelo>.json` (sem texto de chamado). A calibracao e out-of-fold
e compara dois calibradores escalares: sigmoid e isotonica. O alvo ainda e a categoria
historica; a versao definitiva deve usar `categoria_validada`.

Integracoes:

- `src/exportar_dashboard.py` gera `docs/dados/calibracao_ajustada_modelos.json`.
- `docs/index.html` ganhou tabela "Calibracao ajustada preliminar" na aba `Metricas`.
- `.github/workflows/dashboard.yml` passou a instalar `numpy` e `scikit-learn`.

Resultado local (`docs/dados/calibracao_ajustada_modelos.json`, gerado em 06/06/2026 02:35):

| modelo | metodo | ECE bruto | ECE ajustado | Brier bruto | Brier ajustado | >=95 ajustado n | >=95 acerto hist |
|---|---|---:|---:|---:|---:|---:|---:|
| sgd | isotonic | 0,3172 | 0,0016 | 0,2560 | 0,1336 | 2.675 | 0,9989 |
| linear_svc | isotonic | 0,7101 | 0,0019 | 0,6479 | 0,1181 | 5.125 | 0,9836 |
| naive_bayes | isotonic | 0,0363 | 0,0019 | 0,1396 | 0,1378 | 4.127 | 0,9557 |
| random_forest | isotonic | 0,1227 | 0,0020 | 0,1485 | 0,1260 | 5.190 | 0,9917 |
| regressao_logistica | isotonic | 0,2540 | 0,0045 | 0,2260 | 0,1360 | 4.163 | 0,9877 |
| extra_trees | isotonic | 0,0753 | 0,0048 | 0,1274 | 0,1183 | 5.790 | 0,9891 |
| lstm | isotonic | 0,0102 | 0,0096 | 0,1272 | 0,1295 | 3.655 | 0,9860 |

Leitura: a calibracao escalar corrige o problema operacional do `linear_svc` (maior
concordancia global, mas confianca bruta inutil). Depois da calibracao preliminar, o
`linear_svc` passa a ter faixa ajustada >=95% com suporte alto e acerto historico >95%.
Ainda nao liberar producao: esses numeros sao contra historico, nao contra validacao humana.

## Atualizacao Codex - documentacao alinhada a calibracao (2026-06-06 02:54)

Rodada de manutencao documental apos a publicacao da calibracao ajustada. Foram atualizados:

- `PLANO_CALIBRACAO.md`: agora distingue diagnostico bruto, calibracao escalar preliminar
  publicada e calibracao definitiva apos validacao humana.
- `README.md`: lista `calibracao_modelos.json` e `calibracao_ajustada_modelos.json` como
  artefatos consumidos pelo dashboard e registra que workflows de reclassificacao rodam em
  dry-run por padrao.
- `DOCUMENTACAO_MODELOS_E_ESTATISTICA.md`: adiciona explicacao operacional da calibracao
  preliminar, incluindo o caso do `linear_svc` (ECE bruto 0,7101 -> ECE ajustado 0,0019;
  faixa ajustada >=95% com 5.125 casos e 98,36% contra historico).

Nenhum script foi executado contra a planilha nesta rodada. Validacoes locais: leitura dos
documentos, `py_compile` dos scripts de calibracao/exportacao e status git.

## Atualizacao Codex - robustez do workflow estatistico (2026-06-06 03:14)

Revisao de CI encontrou que `.github/workflows/estatistica.yml` ainda fazia `git push` direto
apos commitar `docs/dados/estatistica.json`. Isso podia falhar por corrida de push, problema ja
observado e corrigido antes em `dashboard.yml`.

Correcao aplicada: o passo `Commit estatistica` agora faz `git diff --cached --quiet` para sair
sem mudancas, commita quando necessario e tenta `git pull --rebase --autostash origin main &&
git push` ate 5 vezes. Nao altera planilha nem dashboard; apenas reduz falhas de publicacao de
dados estatisticos.

## Atualizacao Codex - comandos seguros por padrao (2026-06-06 03:34)

Revisao dos documentos encontrou exemplos antigos em `FALTA_FAZER.md` usando
`-f aplicar=true` para `multimodelo_classificacao.yml` e `multimodelo_reclassificacao.yml`.
Isso conflita com a decisao atual de manter reclassificacao/aplicacao em dry-run ate revisar
calibracao e ganho liquido.

Correcao aplicada: exemplos de comandos agora rodam sem `aplicar=true`; a gravacao manual fica
descrita como passo posterior a revisao do dry-run. `README.md` tambem reforca que `--aplicar`
ou input `aplicar=true` so deve ser usado apos revisar logs e impacto esperado.

## Atualizacao Codex - guia tecnico sem reclassificacao automatica (2026-06-06 03:54)

Revisao documental encontrou `docs/GUIA_TECNICO.md` ainda descrevendo a Etapa 2 como
`python src/executar_etapa2.py ... --aplicar` e o workflow robusto como execucao a cada 6h.
Isso estava desatualizado depois das travas de seguranca.

Correcao aplicada: guia agora descreve Etapa 2 e robusto como manuais e dry-run por padrao,
com `--aplicar`/`aplicar=true` apenas apos revisao de ganho liquido, calibracao e impacto
esperado. `dados/README.md` tambem removeu a referencia legada a `doPost` e passou a falar
em escrita `gspread` em lote.

## Atualizacao Codex - heartbeat 08:14Z / alinhamento de pendencias (2026-06-06 05:14)

Sincronizacao do `main`: `git pull --ff-only origin main` trouxe apenas dados regenerados
pelo dashboard no commit remoto `982d494` (`docs/dados/calibracao*.json` e `resumo.json`).
`gh run list --limit 12` confirmou runs recentes bem-sucedidos: dashboard agendado
`27056590550` e Pages `27056604445`.

Revisao de pendencias encontrou itens documentais desatualizados:

- `multimodelo_classificacao.yml` e `multimodelo_reclassificacao.yml` ja usam cache pip,
  retry/timeout e instalacao separada de dependencias leves/TensorFlow.
- `dashboard.yml`, `estatistica.yml`, `etapa2_reclassificacao.yml`,
  `reclassificacao_robusta.yml`, `reclassificacao_dry_run.yml`, `preparar_validacao.yml`,
  `resetar.yml` e `comparar_modelos.yml` tambem usam retry/timeout.
- `resumo.json` ja registra 7 arquivos `registros_<modelo>.json`, todos com 13.825 linhas.

Correcao aplicada: `FALTA_FAZER.md` foi alinhado em P2/P3 para indicar que robustez de
instalacao e calibracao escalar preliminar ja foram executadas, restando calibracao definitiva
apenas apos validacao humana. `docs/index.html` tambem teve o estado vazio da aba
`Multimodelo` corrigido: ele nao diz mais que as 7 IAs nao foram materializadas nem sugere
`aplicar=true`; agora orienta verificar os JSONs publicados e manter reclassificacao em
dry-run ate revisao.

Publicacao: commit `75803b6` enviado ao `main`; Pages build `27057244923` concluido com
sucesso para `headSha=75803b60b8cbd6f9171dbfb5029c489773a5dd52`.

## Atualizacao Codex - comparacao categoria/modelo no painel (2026-06-06 05:34)

Nova sincronizacao: `git pull --ff-only origin main` retornou `Already up to date`.
Sem iniciar validacao humana e sem executar reclassificacao aplicada.

Correcao aplicada: a aba `Categorias` do `docs/index.html` agora consome
`docs/dados/comparacao_categoria.json` e mostra uma tabela "Comparacao por categoria e
modelo". Como o JSON vem em janelas held-out, o painel agrega `precision`, `recall` e `f1`
por `modelo + categoria` ponderando pelo `suporte`, com filtro textual por categoria ou
modelo. Isso fecha a pendencia P0.3-extra, que antes dizia que o JSON existia mas ainda nao
aparecia no dashboard.

`FALTA_FAZER.md` foi atualizado para marcar `comparacao_categoria.json`,
`multimodelo_turnos.json`, `multimodelo_metricas.json`,
`multimodelo_reclass_turnos.json` e a UI categoria/modelo como concluidos. Mantida como
pendencia apenas `comparacao_previsoes.json`, pois depende de a aba `COMPARACAO_PREVISOES`
existir ou ser necessaria para auditoria linha a linha.

Validacao/publicacao: JavaScript de `docs/index.html` extraido e validado com `node --check`.
Commit `5a6a323` enviado ao `main`; Pages build `27057619862` concluido com sucesso para
`headSha=5a6a323c6777e436150f8619c06bdd1d25dd4a71`.

## Atualizacao Codex - filtros do dashboard P0.1 (2026-06-06 05:54)

Nova sincronizacao: `git pull --ff-only origin main` retornou `Already up to date`.
Revisao estatica confirmou que a barra de filtros ja tinha chips ativos, contador, botao
`Limpar` destacado, recalc de cards/aviso/grafico de faixa/categorias/metricas e rotulos
indicando series temporais nao filtraveis. O exportador tambem ja populava os campos
`g`, `f`, `e`, `k` e `v` em `registros.json`/`registros_<modelo>.json`.

Correcao aplicada: no `docs/index.html`, o dropdown multi-selecao agora fecha apos cada
selecao/desselecao de checkbox, reduzindo a chance de cobrir abas ou graficos. `FALTA_FAZER.md`
foi alinhado marcando P0.1 como concluido por verificacao estatica e ajuste de UX.

Validacao/publicacao: JavaScript de `docs/index.html` extraido e validado com `node --check`.
Commit `604d32b` enviado ao `main`; Pages build `27057996073` concluido com sucesso para
`headSha=604d32b2df02b3346cbb97a6b33b900fac6a60cb`.

## Atualizacao Codex - alinhamento P0 do dashboard (2026-06-06 06:14)

Nova sincronizacao: `git pull --ff-only origin main` retornou `Already up to date`.
Revisao estatica do `docs/index.html` confirmou que os itens P0.2, P0.4, P0.5, P0.6 e
P0.7 ja estavam implementados no painel:

- `Modelos`: nao ha mais logica de ultima execucao (`const ult`); a comparacao principal
  usa `multimodelo_metricas`, ranking na base completa, evolucao por turno e tabela de
  recortes held-out de 1.000 ate 13.825.
- `Multimodelo`: mostra progresso por modelo, pendentes, concordancia e reclassificacao
  multimodelo quando houver dados.
- `Metricas`: separa consolidado, resumo tecnico, calibracao bruta, diagnostico por IA,
  calibracao ajustada preliminar e aviso `validados=0`.
- `Reclassificacao`: tem estado vazio objetivo quando a Etapa 2 ainda nao foi executada.
- Meta 95%: explicita que a faixa pode estar aprovada contra historico, mas nao validada
  humanamente e nao liberada para producao.

Correcao aplicada apenas em documentacao: `FALTA_FAZER.md` foi alinhado marcando P0.2,
P0.4, P0.5, P0.6 e P0.7 como concluidos. Restou no P0 somente a evolucao opcional
`comparacao_previsoes.json`, dependente de necessidade de auditoria linha a linha.

## Atualizacao Codex - comparacao_previsoes sanitizada (2026-06-06 06:34)

Nova sincronizacao: `git pull --ff-only origin main` retornou `Already up to date`.
Sem iniciar validacao humana e sem escrever na planilha.

Correcao aplicada: `src/exportar_dashboard.py` agora exporta
`docs/dados/comparacao_previsoes.json` quando a aba `COMPARACAO_PREVISOES` existir, mas
somente em versao sanitizada. Campos removidos do JSON publico: `id_chamado`, `titulo` e
`observacao_avaliador`. Campos mantidos: modelo, linha da planilha, categorias original/
prevista, score, divergencia, enviado_revisao, datas/statuses de validacao e
`quem_estava_correto`. Se a aba nao existir ou estiver vazia, o JSON publicado fica `[]`.

Tambem foi criado `docs/dados/comparacao_previsoes.json` inicial com `[]`, e `README.md`/
`FALTA_FAZER.md` foram atualizados para fechar o P0 sem publicar texto de chamado.

Validacao/publicacao: `python -m py_compile src\exportar_dashboard.py` OK; JSON inicial
validado com `python -m json.tool`. Commit publicado apos rebase como `5ca0cfd`. Workflow
manual `dashboard.yml` run `27058838065` concluiu com sucesso e gerou commit de dados
`e3d1689`. `resumo.json` passou a registrar `comparacao_previsoes=7000`; leitura local do
JSON confirmou 7.000 registros com campos permitidos:
`categoria_original`, `categoria_prevista`, `data_validacao`, `divergencia`,
`enviado_revisao`, `executado_em`, `linha_planilha`, `modelo`, `quem_estava_correto`,
`score`, `validacao_humana_final`. Busca textual por `id_chamado`, `"titulo"` e
`observacao_avaliador` nao retornou ocorrencias. Pages build `27058852407` concluiu com
sucesso para `headSha=e3d16898ab78c7adee601f68103e5d235192d255`.

## Atualizacao Codex - separacao de dependencias leves/TensorFlow (2026-06-06 06:54)

Nova sincronizacao: `git pull --ff-only origin main` retornou `Already up to date`.
Sem iniciar validacao humana e sem escrever na planilha.

Correcao aplicada em P2: criado `requirements-leves.txt` com `gspread`, `google-auth`,
`numpy` e `scikit-learn`, deixando `requirements.txt` como ambiente completo com
`tensorflow==2.17.0`. Workflows ajustados para instalar dependencias leves como base e
baixar TensorFlow apenas quando o caminho pede LSTM/producao:

- `classificacao_incremental.yml`: TensorFlow somente quando `modelo=producao`; baseline
  usa apenas `requirements-leves.txt`.
- `etapa1_turnos.yml`: schedule/producao instala TensorFlow; workflow manual `baseline`
  usa apenas leves.
- `etapa2_reclassificacao.yml`: TensorFlow somente quando `modelo=producao`; baseline usa
  apenas leves.
- `reclassificacao_dry_run.yml`: leves sempre; TensorFlow apenas para `producao`; robusto
  instala `requirements-robusto.txt`.
- `reclassificacao_robusta.yml`: leves + `requirements-robusto.txt`, sem TensorFlow.
- `comparar_modelos.yml`, `multimodelo_classificacao.yml` e
  `multimodelo_reclassificacao.yml`: cache passou a considerar `requirements-leves.txt`;
  TensorFlow continua condicional ao escopo LSTM.
- `dashboard.yml`: usa `requirements-leves.txt` como cache/install base.

`README.md`, `docs/GUIA_TECNICO.md` e `FALTA_FAZER.md` foram alinhados; P2 fica concluido
quanto a retry/cache e separacao leve/LSTM. `requirements-robusto.txt` permanece separado
para o transformer local pesado.

Validacao/publicacao: `python -m py_compile src\classificar_etapa.py src\executar_etapa1.py
src\executar_etapa2.py src\exportar_dashboard.py` OK. `requirements-leves.txt` validado
localmente sem `tensorflow`. Busca nos workflows confirmou que nao restou
`pip install -r requirements.txt` direto. Parser YAML local indisponivel (`ModuleNotFoundError:
No module named 'yaml'`), entao a validacao funcional foi feita em CI: commit `853e925`
publicado no `main`; workflow `dashboard.yml` run `27059243157` concluiu com sucesso usando
`python -m pip install --retries 5 --timeout 120 -r requirements-leves.txt`. O workflow
gerou commit de dados `0df07fb`; Pages build `27059254566` concluiu com sucesso para
`headSha=0df07fb845a1e3cf3aaf06434ea4034edaf5317d`.

## Atualizacao Codex - checklist estatistico Fleiss (2026-06-06 07:04)

Nova verificacao local sem iniciar validacao humana: `docs/dados/estatistica.json` ja contem
`fleiss_kappa_entre_ias=0,7721`; `src/analise_estatistica.py` implementa o calculo via
`statsmodels.stats.inter_rater.fleiss_kappa`; `docs/index.html` exibe o indicador na aba
`Estatistica`. Portanto, `FALTA_FAZER.md` foi ajustado para marcar Kappa de Fleiss entre
as IAs como concluido e deixar aberto apenas o refinamento das figuras ABNT quando houver
validacao humana.

## Atualizacao Codex - sincronizacao do dashboard agendado (2026-06-06 07:14)

Nova sincronizacao: `git pull --ff-only origin main` avancou de `c673fbb` para `9d26a00`,
commit automatico `dados do dashboard [skip ci]` gerado pelo workflow agendado
`dashboard.yml` run `27059398325` (sucesso). O Pages correspondente, run `27059410945`,
tambem concluiu com sucesso.

Validacao local dos JSONs publicados: `python -m json.tool` OK para
`docs/dados/resumo.json`, `docs/dados/calibracao_modelos.json` e
`docs/dados/calibracao_ajustada_modelos.json`. `resumo.json` registra
`gerado_em=06/06/2026 07:06`, `registros=13825`, `validados=0`,
`ece_historico=0,0379`, 7 modelos com 13.825 registros cada e
`comparacao_previsoes=7000`. `FALTA_FAZER.md` foi alinhado para trocar o ECE antigo
aproximado (`0,0399`) pelo valor atual do JSON (`0,0379`). Sem iniciar validacao humana e
sem escrever na planilha.

## Atualizacao Codex - dry-run reclassificacao multimodelo leve (2026-06-06 07:36)

Nova sincronizacao previa: `git pull --ff-only origin main` retornou `Already up to date`.
Sem iniciar validacao humana.

Acao executada: workflow `multimodelo_reclassificacao.yml` disparado manualmente em
dry-run com `modelos=leves`, `max_turnos=1`, `aplicar=false`: run `27059977070`, concluido
com sucesso em 1m37s. O proprio workflow pulou TensorFlow porque o escopo foi apenas dos
6 modelos leves. Como `--aplicar` nao foi usado, `src/reclassificacao_multimodelo.py`
retornou antes de qualquer `append_aba`; nao houve escrita na planilha nem commit de dados.

Resultado do log: `elegiveis=13825`, `memoria_validada=0`, 90 simulacoes no total.
Por modelo: `naive_bayes` 15 reclassificados, ganho 0; `regressao_logistica` 15,
ganho -1; `linear_svc` 15, ganho -2; `sgd` 15, ganho 0; `extra_trees` 15, ganho +1;
`random_forest` 15, ganho 0. Resultado consolidado: ainda nao ha evidencia para aplicar
reclassificacao em massa; manter apenas dry-runs/calibracao ate haver ganho liquido
positivo e/ou validacao humana.

## Atualizacao Codex - dry-run reclassificacao multimodelo LSTM (2026-06-06 07:58)

Nova sincronizacao previa: `git pull --ff-only origin main` retornou `Already up to date`.
Sem iniciar validacao humana.

Acao executada: workflow `multimodelo_reclassificacao.yml` disparado manualmente em
dry-run com `modelos=pesados`, `max_turnos=1`, `aplicar=false`, `lstm_perfil=padrao`:
run `27060370440`, concluido com sucesso em 3m32s. Desta vez o workflow instalou
TensorFlow, pois o escopo incluiu LSTM. Como `--aplicar` nao foi usado, nao houve escrita
na planilha.

Resultado do log: `modelos=['lstm']`, `elegiveis=13825`, `memoria_validada=0`,
`candidatos_baixa=9549`, `lote_agora=15`, `base=13810`, `reclass=15`,
`corrigidos=2`, `prejudicados=2`, ganho 0, metodo `topup`, dry-run. Em conjunto com o
dry-run dos 6 modelos leves, todos os 7 modelos ja foram testados em lote minimo de
reclassificacao sem escrita; nenhum resultado justifica aplicacao em massa neste momento.

O workflow de dashboard foi acionado automaticamente apos o dry-run: run `27060443369`
concluiu com sucesso, gerando commit de dados `2a2cd39`; Pages run `27060455788` tambem
concluiu com sucesso. Validacao local: `python -m json.tool docs\dados\resumo.json` OK.
O `resumo.json` ficou com `gerado_em=06/06/2026 07:58`, `registros=13825`,
`validados=0`, `multimodelo_metricas=7` e `multimodelo_reclass_turnos=0`, confirmando
que o dry-run nao materializou reclassificacao no dashboard.

## Atualizacao Codex - Etapa 1 agendada sem pendencias (2026-06-06 08:14)

Nova sincronizacao: `git pull --ff-only origin main` avancou de `8fb89c4` para `5227678`,
commit automatico `dados do dashboard [skip ci]`.

Execucoes verificadas: workflow `etapa1_turnos.yml` agendado, run `27060670562`, concluiu
com sucesso; log registrou `total=18858`, `elegiveis=13825`, `pendentes=0`,
`modelo=producao` e `Etapa 1 concluida (0 pendentes)`. O dashboard automatico acionado em
seguida, run `27060687295`, tambem concluiu com sucesso; Pages run `27060701030`
concluiu com sucesso.

Validacao local: `python -m json.tool docs\dados\resumo.json` OK. O `resumo.json` ficou
com `gerado_em=06/06/2026 08:10`, `registros=13825`, 7 modelos com 13.825 registros cada,
`validados=0`, `ece_historico=0,0379`, `multimodelo_metricas=7` e
`multimodelo_reclass_turnos=0`. Sem iniciar validacao humana e sem aplicar
reclassificacao.
