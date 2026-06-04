# GUIA TÉCNICO — classificacao-chamados

Explica **o que cada arquivo/script faz, como funciona, com o que se relaciona e
como é executado**, e o **significado das colunas de saída** (Classificação IA,
Avaliação %, Executor, Criticidade) e de **cada executor**.

> Fonte de verdade do método: o "Roteiro Metodológico ... Malha IA" (50 etapas).
> Acesso à planilha: conta de serviço (gspread). Última atualização: 2026-06-04.

---

# PARTE 1 — Arquivos e scripts

## Fluxo principal (Etapa 1 progressiva — o que roda agendado)

### `src/executar_etapa1.py` — orquestrador da Etapa 1
- **O que faz:** classifica a base **progressivamente, em turnos de 15** (roteiro,
  etapas 3,4,6-16). A cada execução pega só os **pendentes** (coluna G vazia, não
  conferidos), até `--max-turnos` turnos, classifica, grava e registra tudo.
- **Como funciona (passo a passo):**
  1. Abre a planilha e lê `A:M` **uma vez** (valores crus, sem formatação).
  2. Monta os **elegíveis** (têm categoria original em C **e** texto) e os
     **pendentes** (elegíveis com G vazio).
  3. Treina o modelo **uma vez** na base rotulada (texto → categoria original).
  4. Seleciona o lote (`max-turnos × 15` pendentes) e prediz.
  5. Para cada linha define: categoria IA (G), confiança (H, fração 0-1),
     **executor** (I, por faixa), **criticidade** (J), e conferência (G==C).
  6. Agrupa em turnos de 15 e calcula **taxa por turno** e **acumulada**.
  7. Grava **G:J** (lote), a **fórmula K** `=SE(G="";"";G=C)` (uma vez), e faz
     **APPEND** em `LOG_TURNOS_CLASSIFICACAO`, `LOG_LINHA_A_LINHA`,
     `SNAPSHOT_ETAPA_1`; atualiza `EXPERIMENTO_CONFIG` e `METRICAS_EXPERIMENTO`.
- **Relaciona-se com:** `planilha.py` (leitura/escrita), `classificador_producao.py`
  (modelo + faixas + criticidade), `config_experimento.json` (parâmetros).
- **Como é executado:**
  - Local: `python src/executar_etapa1.py --modelo producao --max-turnos 60 --aplicar`
    (sem `--aplicar` = dry-run, não escreve).
  - Automático: workflow `etapa1_turnos.yml` (a cada 15 min).
  - Quando não há pendentes: imprime "Etapa 1 concluída" e não faz nada (no-op).

### `src/classificador_producao.py` — camada de modelo (LSTM + RF + faixas)
- **O que faz:** decide qual modelo usar e traduz confiança em executor/criticidade.
- **Funções:**
  - `treinar_classificador(textos, categorias)` → tenta **LSTM** (se TensorFlow
    disponível e base ≥ 200); senão cai para **RandomForest** (TF-IDF). Retorna
    `(modelo, eh_lstm)`.
  - `predizer(clf, eh_lstm, textos)` → `(categorias_previstas, confianças)`.
  - `nome_executor(conf, eh_lstm)` → nome do executor pela faixa (ver Parte 2).
  - `faixa_confianca(conf)` → `abaixo_70 | entre_70_95 | acima_95` (para métricas).
  - `aplicar_faixa(pred, conf, eh_lstm)` → `(categoria, executor)`.
  - `estimar_criticidade(texto)` → `Alta | Média | Baixa` por palavras-chave.
- **Relaciona-se com:** `modelo_lstm.py` (o LSTM).

### `src/modelo_lstm.py` — o classificador LSTM
- **O que faz:** rede **BiLSTM** (Embedding 8000×128 → BiLSTM(64) → Dropout →
  Dense(64) → Softmax), espelhando o motor de produção. Usa `class_weight` balanceado.
- **Funções:** `fit(textos, categorias)`, `predict_com_conf(textos)`,
  `save(dir)` / `load(dir)` (para reusar modelo treinado).
- **Requer:** `tensorflow`. **Relaciona-se com:** `classificador_producao.py`.

### `src/planilha.py` — todo o acesso ao Google Sheets (conta de serviço)
- **O que faz:** abre a planilha e lê/escreve via **gspread + conta de serviço**.
- **Funções principais:**
  - `abrir_planilha(id)` / `abrir_worksheet(id, aba)` — autentica com
    `credenciais_sa.json` (lido com `utf-8-sig`, tolera BOM).
  - `ler_valores(ws, "A:M")` — lê **sem formatação** (números crus; confiança
    vem 0-1, não "88%").
  - `exportar_lote_gj(ws, linhas)` — grava **G:J** em **uma** escrita em bloco
    (read-modify-write): **pula linhas com CONFERÊNCIA=TRUE**, **não sobrescreve
    célula vazia** e **formata H como %**.
  - `append_aba(sh, nome, cabecalho, linhas, colunas_percentuais)` — acrescenta
    linhas ao fim de uma aba (cria + cabeçalho + formato % na 1ª vez).
  - `escrever_aba(...)` — limpa e regrava uma aba inteira.
- **Relaciona-se com:** `gspread`, e é usado por quase todos os scripts.

## Scripts operacionais / alternativos

### `src/classificar_etapa.py` — classificação github-first (modos)
- **O que faz:** lê o `dados/snapshot_etapa_1.json` e classifica em **3 modos**:
  `full` (out-of-fold na base toda — métrica científica), `incremental` (só G
  vazio), `reclassificacao` (reavalia baixa confiança). Modelo `baseline` ou `producao`.
- **Saída:** `dados/classificacao_etapa_1.json` (não escreve direto na planilha).
- **Executado:** `python src/classificar_etapa.py --modo incremental --modelo producao`.

### `src/exportar_etapa.py` — exporta o JSON para a planilha
- **O que faz:** lê `classificacao_etapa_1.json` e grava **G:J** em lote (gspread).
- **Executado:** `python src/exportar_etapa.py --aplicar` (sem isso, dry-run).

### `src/registrar_snapshot_inicial.py` — snapshot da base
- **O que faz:** lê a planilha 1× e grava `dados/snapshot_etapa_1.json` (input das
  etapas de classificação no fluxo `classificar_etapa.py`).

### `src/comparar_modelos.py` — LSTM × baseline
- **O que faz:** holdout estratificado 80/20 comparando baseline TF-IDF e LSTM,
  para medir qual acerta mais. **Requer tensorflow.** Não escreve na planilha.

### `src/resetar_experimento.py` — recomeçar do ZERO (reutilizável)
- **O que faz:** limpa `G:K` na planilha principal (preserva C original, L e M) e o
  conteúdo de **todas as abas do experimento**, para recomeçar a classificação/
  reclassificação do zero.
- **Trava de segurança:** só executa com `--aplicar` **E** `--confirmar RESETAR`.
- **Executado:** `python src/resetar_experimento.py --aplicar --confirmar RESETAR`,
  ou pelo workflow `resetar.yml` (digitando `RESETAR` no campo de confirmação).

### Aba `METRICAS_POR_CATEGORIA` (gerada pelo `executar_etapa1.py`)
- **O que é:** mesma ideia do `LOG_TURNOS_CLASSIFICACAO`, mas **por categoria de
  chamado** (1 linha por categoria original, cumulativa). Colunas: qtd, concordância
  (TRUE/FALSE), taxa de concordância (%), confiança média (%) e distribuição por
  faixa (<70 / 70-95 / >=95). Recalculada a cada execução a partir do SNAPSHOT.
  Base para o dashboard HTML. (Roteiro, Etapa 37.)

### `src/executar_etapa2.py` — Etapa 2 (reclassificação) do roteiro
- **O que faz:** reavalia os chamados de **baixa confiança** (<95% na Etapa 1),
  em **turnos**, comparando **antes** (SNAPSHOT_ETAPA_1) × **depois** e medindo o
  **ganho líquido** (corrigidos − prejudicados). (Roteiro, etapas 17-23.)
- **Candidatos:** SNAPSHOT com confiança < 95%, não conferidos (M≠TRUE) e ainda
  não reclassificados (executor não começa com `Reclass`).
- **Saída:** grava G:J com nova categoria/confiança e executor `Reclass_<tag>`
  (`Reclass_LSTM`, `Reclass_Robusto`...); APPEND em `LOG_TURNOS_RECLASSIFICACAO`
  (antes/depois, corrigidos, prejudicados, mantidos, ganho líquido, variação de
  confiança) e `LOG_LINHA_A_LINHA` (etapa 2).
- **Executado:** `python src/executar_etapa2.py --modelo producao --max-turnos 40 --aplicar`;
  ou workflow `etapa2_reclassificacao.yml` (manual). Sem `--aplicar` = dry-run.

### `src/classificador_robusto.py` — 3º modelo "quase-LLM" local
- **O que faz:** modelo **mais pesado** baseado em **embeddings de transformer
  multilíngue** (`sentence-transformers`, 100% local) + LogisticRegression. Usado
  na reclassificação dos casos difíceis. Se a lib não estiver instalada, faz
  **fallback automático** para LSTM/RF (o fluxo nunca quebra).
- **Executado:** via `executar_etapa2.py --modelo robusto`, no workflow
  `reclassificacao_robusta.yml` (**a cada 6h, poucos chamados por vez** — é pesado).
  Dependência em `requirements-robusto.txt` (instalada só nesse workflow).

### Workflows (`.github/workflows/`)
- `etapa1_turnos.yml` — Etapa 1 progressiva (LSTM), agendado a cada 15 min.
- `etapa2_reclassificacao.yml` — Etapa 2 (reclassificação), disparo manual.
- `reclassificacao_robusta.yml` — modelo robusto, a cada 6h, poucos chamados.
- `resetar.yml` — reset ao zero (manual, exige digitar `RESETAR`).
- `classificacao_incremental.yml` — operacional incremental (manual; agendamento desativado).
- Todos os que escrevem na planilha usam a concorrência `escrita-planilha` (não rodam em paralelo).

## Legados (era do Apps Script — não usados no fluxo atual)
- `src/validar_planilha_experimento.py`, `preparar_abas_experimento.py`,
  `registrar_config_experimento.py`, `classificar_lote_inicial.py`,
  `classificar_lote_baseline.py` — usavam o Web App por token.
- `apps_script/Code.gs` — Web App (token); substituído pela conta de serviço.

## Configuração, dados e infraestrutura
- `config_experimento.json` — `run_id`, `spreadsheet_id`, `aba_principal`,
  `range_leitura`, limiares (`limiar_confianca_baixa` 0.7, `limiar_alta_confianca`
  0.95), `tamanho_lote`, nomes das abas do experimento.
- `requirements.txt` — `gspread`, `google-auth`, `scikit-learn`, `tensorflow`.
- `credenciais_sa.json` — chave da conta de serviço (**gitignored**, nunca versionar).
- `dados/` — artefatos JSON do processamento (**gitignored**, exceto `README.md`).
- `tests/test_github_first.py` — testes locais (sem rede).
- `.github/workflows/etapa1_turnos.yml` — Etapa 1 progressiva, **agendado a cada 15 min**.
- `.github/workflows/classificacao_incremental.yml` — só disparo manual (agendamento desativado).
- `CONTEXTO.md` (foco no experimento) e `docs/contexto_projeto.txt` (panorama geral mascarado).

---

# PARTE 2 — Classificação IA, Avaliação %, Executor e Criticidade

## As quatro colunas de saída (G, H, I, J)

| Col | Nome | O que é |
|-----|------|---------|
| **G** | Classificação IA | a **categoria** que o modelo previu para o chamado |
| **H** | Avaliação (%) | a **confiança** do modelo nessa previsão (0–100%) |
| **I** | Executor | **qual modelo** classificou e em **qual faixa** de confiança |
| **J** | Criticidade | **gravidade** do chamado (Alta/Média/Baixa) |

E a **coluna K (Comparação)** = `=SE(G="";"";G=C)`: TRUE se a IA (G) concordou com
a categoria **original/histórica** (C); FALSE se divergiu.

## Como elas se relacionam
1. O modelo lê o **texto** do chamado (TÍTULO + DESCRIÇÃO GLPI + TÍTULO O.S.M. +
   DESCRIÇÃO O.S.M.) e devolve **duas coisas**: a categoria (→ **G**) e uma
   **probabilidade** de 0 a 1 (→ **H**, a confiança).
2. O **Executor (I)** é derivado de duas informações: **qual modelo** rodou
   (LSTM ou RandomForest) **e** em que **faixa** a confiança (H) caiu. Ou seja,
   **I é um rótulo categórico do par (modelo, confiança)**; **H é o número** dessa confiança.
3. A **Criticidade (J)** é **independente** da classificação: é calculada do
   **texto** por palavras-chave de gravidade — `urgente/incêndio/choque/alagamento`
   → **Alta**; `reparo/quebra/falha/defeito` → **Média**; caso contrário **Baixa**.
   Não depende da categoria nem da confiança.

## Significado de cada executor

| Executor | Modelo | Faixa de H | Significado |
|----------|--------|-----------|-------------|
| **LSTM** | BiLSTM (primário) | **≥ 95%** | classificado pelo LSTM com **alta** confiança |
| **LSTM_BAIXA_CONF** | BiLSTM (primário) | **< 95%** | classificado pelo LSTM, confiança **abaixo do limiar alto** |
| **RF_Fallback** | RandomForest (fallback) | ≥ 95% | só quando o LSTM está indisponível |
| **RF_Fallback_BAIXA_CONF** | RandomForest (fallback) | < 95% | fallback com confiança abaixo do limiar |
| *Reclass_LSTM / Reclass_RF* | (Etapa 2, futuro) | — | resultado da **reclassificação** |
| *SemClassificador / NaoProcessado / Desconhecido* | — | — | nenhum modelo disponível / falha / origem indefinida |

> No fluxo atual o **LSTM é o primário**; o RandomForest só entra como **fallback**
> se o TensorFlow não estiver disponível ou a base for pequena demais. Por isso, na
> prática, você verá quase sempre `LSTM` e `LSTM_BAIXA_CONF`.

## ⭐ A dúvida central: por que existe `LSTM_BAIXA_CONF` com avaliação acima de 90%?

Porque **"baixa confiança" aqui significa "abaixo do limiar de ALTA confiança
(95%)"**, e **não** "confiança ruim em termos absolutos".

- O limiar de alta confiança é **95%** (`limiar_alta_confianca` no
  `config_experimento.json`).
- Tudo **≥ 95%** vira **`LSTM`** (alta).
- Tudo **< 95%** vira **`LSTM_BAIXA_CONF`** — inclusive **90%, 93%, 94%**.

Então um chamado com **94%** é classificado como `LSTM_BAIXA_CONF` **porque 94 < 95**.
Não é erro: é a regra de corte. O sistema reserva o rótulo "alta" só para os casos
em que o modelo está **muito** seguro (≥95%), e trata 90–94% como "bom, mas ainda
não no patamar de confiar automaticamente". **O limiar é ajustável** (basta mudar
`limiar_alta_confianca`); se você achar 95% rígido demais para 52 categorias, dá
para baixar para, por exemplo, 0.90.

## As três faixas de análise (não confundir com o executor)
O roteiro (Etapa 14) analisa a confiança em **três faixas**, registradas nas
métricas por turno:

- **abaixo_70** (H < 70%)
- **entre_70_95** (70% ≤ H < 95%)
- **acima_95** (H ≥ 95%)

Atenção: o **executor** tem só **dois** níveis para o LSTM (`LSTM` para ≥95% e
`LSTM_BAIXA_CONF` para <95%). Ou seja, **`LSTM_BAIXA_CONF` cobre as faixas
`abaixo_70` E `entre_70_95`**. As três faixas servem para a *análise estatística*;
o executor é o *rótulo operacional*.

## O que cada situação significa na prática
Concordância IA × histórico observada por faixa (execução com LSTM):

| Situação | Faixa | Concordância típica | Leitura |
|----------|-------|---------------------|---------|
| `LSTM` | ≥ 95% | ~99% | IA muito segura **e** quase sempre alinhada ao histórico → confiável |
| `LSTM_BAIXA_CONF` | 70–95% | ~86% | IA razoavelmente segura; boa, mas vale revisar; **candidata à reclassificação** |
| `LSTM_BAIXA_CONF` | < 70% | ~44% | IA insegura; muita divergência → **prioridade de revisão humana / reclassificação** |

Isso confirma o esperado do roteiro: **quanto maior a confiança, maior o acerto**.
Por isso a **Etapa 2 (reclassificação)** mira justamente os chamados com confiança
**< 95%** (os `*_BAIXA_CONF`), tentando melhorar os de menor certeza, e a
**validação humana** prioriza os de baixa confiança e as divergências (K = FALSE).
