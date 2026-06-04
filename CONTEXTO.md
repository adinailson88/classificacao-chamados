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

## Regras de ouro
- Não presumir totais fixos de linhas: `total_linhas_*` são **observados** na
  execução; a planilha cresce; os scripts releem a fonte.
- Colunas localizadas por **cabeçalho**, não por posição fixa.
- Linhas totalmente vazias são ignoradas.
- Escrita na planilha só com flag explícita (`--aplicar`).
- Segredos (URL/token do Web App) só em GitHub Secrets — nunca em código/commit/txt.
- Timestamps sempre `YYYY-MM-DDTHH:mm:ss-03:00` (America/Bahia).
- Faltando evidência: responder exatamente `Informação insuficiente para verificar.`

## Planilha experimental
- ID `<SPREADSHEET_ID>`, aba `CHAMADOS_ESQUELETO_REDUZIDO`, range `A:M`.
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
- Conta de serviço: `<SERVICE_ACCOUNT_EMAIL>`.
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
1. **Etapa 2 (reclassificação) COMPLETA do roteiro** (etapas 17-23): estado
   antes/depois por chamado, casos corrigidos × prejudicados, **ganho líquido**,
   aba `LOG_TURNOS_RECLASSIFICACAO`, executor `Reclass_LSTM`. Hoje só existe um
   `--modo reclassificacao` básico em `classificar_etapa.py` (não no padrão completo).
2. **3º modelo mais pesado (quase-LLM local)** — pedido do usuário: roda no FINAL
   (após reclassificação total), em baixa frequência (a cada muitas horas) e em
   poucos chamados. Workflow separado de baixa frequência. NÃO implementado ainda.
3. Validação humana + métricas finais (etapas 24-50): `VALIDACAO_HUMANA`
   (IA_CERTA/GLPI_CERTO/AMBOS_ERRADOS/CASO_AMBIGUO/NAO_AVALIADO, usar_para_treino),
   matriz de confusão, métricas por categoria, indicadores consolidados, gráficos.
4. (Opcional) Métricas por faixa/executor ACUMULADAS na aba (hoje METRICAS guarda
   global acumulada + faixas do último lote).
5. Remover o Apps Script legado (`apps_script/Code.gs`) quando não for mais útil.

> Nota sobre modelos: o teste LSTM×baseline (abaixo) mediu o **baseline melhor**,
> mas o **roteiro (Etapa 15) manda LSTM primário + RF fallback** (paridade com a
> produção). Por isso o fluxo usa LSTM; o baseline fica como comparação/fallback.
