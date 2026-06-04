# CONTEXTO — classificacao-chamados (panorama único)

> Arquivo **único** de contexto/continuidade deste repositório. Consolida e
> substitui os antigos `CONTINUIDADE_*.txt` e `PROMPT_CONTINUACAO_OUTRA_IA.txt`
> (removidos; histórico preservado no git). **Atualizar este arquivo** a cada
> etapa importante, em vez de criar arquivos novos.
>
> Última consolidação: 2026-06-03 (America/Bahia, UTC-03:00).

## Objetivo
Experimento controlado de **classificação e reclassificação automática de
chamados**, separado do Malha IA operacional, preservando rastreabilidade, logs,
snapshot inicial, validação humana futura e separação experimento/produção.

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
- ID `1lohPUQOgxzt_DMxnNLKMxnieZq1sVmh4uwBLbbgvfiQ`, aba `CHAMADOS_ESQUELETO_REDUZIDO`, range `A:M`.
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

## Apps Script (ponte)
- `apps_script/Code.gs` exposto como Web App. Token na 1ª linha (`API_TOKEN`),
  igual ao GitHub Secret `APPS_SCRIPT_TOKEN`. Após editar: salvar e **implantar
  nova versão** (Gerenciar implantações > Editar > Nova versão > Implantar).
- Ações GET: `listar_abas`, `validar`, `ler`.
- Ações POST: `preparar_abas_experimento`, `registrar_config_experimento`,
  `registrar_snapshot_inicial`, **`exportar_lote`** (novo, ver abaixo).

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
exportar_etapa.py --aplicar   -> grava G:J na planilha (1 doPost exportar_lote)
                                 dados/manifest_exportacao.json
```
Decisões confirmadas: 6 arquivos JSON em `dados/` (schemas em `dados/README.md`);
exportação grava **G:J**; **pula M=TRUE**; **não sobrescreve célula vazia**
(preserva J/Criticidade, que o baseline não gera). Classificação é **out-of-fold**
(StratifiedKFold) para evitar vazamento. Nenhum script escreve sem `--aplicar`.

## Arquivos do repositório
- `src/validar_planilha_experimento.py` — validação de cabeçalho/linhas (offline e via Web App).
- `src/preparar_abas_experimento.py` — cria abas experimentais (`--aplicar`).
- `src/registrar_config_experimento.py` — grava EXPERIMENTO_CONFIG (`--aplicar`).
- `src/registrar_snapshot_inicial.py` — gera `dados/snapshot_etapa_1.json`; `--aplicar` grava a aba (legado).
- `src/classificar_lote_inicial.py` — seleção de lote em dry-run (legado).
- `src/classificar_lote_baseline.py` — baseline TF-IDF+LogReg em dry-run (legado).
- `src/classificar_etapa.py` — classificação github-first (lê snapshot, grava JSON).
- `src/exportar_etapa.py` — exportação em lote G:J (1 doPost) + manifest.
- `apps_script/Code.gs` — Web App (inclui `exportar_lote`).
- `dados/README.md` — schemas dos 6 arquivos JSON.
- `tests/test_github_first.py` — testes sem rede.
- `config_experimento.json`, `requirements.txt`, `AGENTS.md`, `README.md`.

## Comandos úteis
```bash
# validação de sintaxe
python -m py_compile src/classificar_etapa.py src/exportar_etapa.py src/registrar_snapshot_inicial.py
python tests/test_github_first.py

# fluxo real (com credenciais)
export APPS_SCRIPT_URL=...; export APPS_SCRIPT_TOKEN=...
python src/registrar_snapshot_inicial.py     # snapshot JSON (1 leitura)
python src/classificar_etapa.py              # classifica no repo (0 API)
python src/exportar_etapa.py                 # dry-run do lote
python src/exportar_etapa.py --aplicar       # 1 escrita em lote (G:J)
```

## Pendências
1. Publicar o `Code.gs` atualizado no Web App (deploy) p/ habilitar `exportar_lote`.
2. Rodar o fluxo github-first com credenciais reais.
3. Confirmar timestamps America/Bahia no deploy ativo.
4. Avaliar privacidade antes de versionar `dados/*.json` reais (repo público).
5. Opcional: GitHub Action por etapa (atualiza JSON, commita; exporta sob trigger).
