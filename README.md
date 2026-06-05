# Classificacao de Chamados

Repositorio experimental para avaliacao da classificacao e reclassificacao automatica de chamados, separado do repositorio operacional Malha IA.

O objetivo e manter um experimento rastreavel, com processamento por turnos, logs, metricas, painel publico e preparacao para validacao humana.

## Estado atual

1. A planilha experimental e lida por conta de servico Google Cloud via `gspread`.
2. O ID da planilha nao e versionado; use `SPREADSHEET_ID` ou `spreadsheet_id.local`.
3. A chave da conta de servico nao e versionada; use `credenciais_sa.json` local ou o secret `GCP_SA_KEY` no GitHub Actions.
4. A aba principal e `CHAMADOS_ESQUELETO_REDUZIDO`, com leitura em `A:M`.
5. Os dados reais gerados em `dados/*.json` e `dados/*.jsonl` ficam ignorados no Git.
6. Os dados publicos do dashboard ficam em `docs/dados`.
7. Nenhum script escreve na planilha sem flag explicita `--aplicar`, exceto workflows ja configurados para a etapa correspondente.
8. A validacao humana ja pode ser preparada, mas a revisao manual fica pausada ate o fortalecimento dos scripts/modelos.

## Colunas da aba principal

```text
A  ID Chamado
B  TITULO
C  CATEGORIA COMPLETA
D  DESCRICAO GLPI
E  TITULO O.S.M.
F  DESCRICAO O.S.M.
G  Classificacao IA
H  Avaliacao (%)
I  Executor
J  Criticidade Atribuida por IA
K  Comparacao
L  Classificado_Confianca_IA
M  CONFERENCIA
```

Saida da IA: `G:J`.

`K` compara a classificacao da IA com a categoria historica: `=SE(G="";"";G=C)`.

`M=TRUE` indica conferencia humana e impede sobrescrita da linha pelos fluxos de exportacao.

## Fluxo principal

1. Etapa 1: classificacao progressiva em turnos de 15.
2. Etapa 2: reclassificacao de casos de baixa confianca.
3. Fortalecimento antes da etapa manual: LSTM configuravel, memoria validada, reclassificacao priorizando menor confianca e modelo robusto local.
4. Etapa 3: validacao humana.
5. Etapas finais: matriz de confusao, metricas por categoria, confianca calibrada e indicadores consolidados.

## Objetivo final do modelo

Arquivo de referencia: `OBJETIVO_FINAL_MODELO_IA.txt`.

A meta e chegar a um modelo treinado e calibrado que indique, para a maioria das categorias, se a categoria historica do chamado esta correta ou nao. A confianca minima alvo e `>=95%`, mas essa confianca precisa ser validada/calibrada: softmax alto sozinho nao comprova acerto.

O reforco automatico antes da revisao manual esta em:

1. `config_experimento.json`: define `objetivo_final`, `modelo_ia` e `memoria_validada`.
2. `src/modelo_lstm.py`: aceita perfil LSTM `robusto`.
3. `src/memoria_validada.py`: le apenas exemplos humanos com `categoria_validada` e `usar_para_treino=SIM`.
4. `src/executar_etapa1.py` e `src/executar_etapa2.py`: usam a memoria validada quando ela existir.
5. `src/executar_etapa2.py`: prioriza menor confianca antes de reclassificar.
6. `src/classificacao_multimodelo.py` e `src/reclassificacao_multimodelo.py`: executam o ciclo completo por modelo em abas separadas, com predicao out-of-fold.

## Comandos locais

Validacao de sintaxe:

```bash
python -m py_compile src/classificar_etapa.py src/exportar_etapa.py src/registrar_snapshot_inicial.py
```

Testes sem rede:

```bash
python tests/test_github_first.py
```

Fluxo GitHub-first com conta de servico:

```bash
python src/registrar_snapshot_inicial.py
python src/classificar_etapa.py --modo incremental --modelo producao
python src/exportar_etapa.py
python src/exportar_etapa.py --aplicar
```

Etapa 1 progressiva:

```bash
python src/executar_etapa1.py --modelo producao --max-turnos 60
python src/executar_etapa1.py --modelo producao --max-turnos 60 --aplicar
```

Etapa 2, reclassificacao:

```bash
python src/executar_etapa2.py --modelo producao --max-turnos 40
python src/executar_etapa2.py --modelo producao --max-turnos 40 --aplicar
```

Multimodelo completo:

```bash
python src/classificacao_multimodelo.py --modelos leves --max-turnos 1
python src/reclassificacao_multimodelo.py --modelos leves --max-turnos 1
```

Preparacao da validacao humana:

```bash
python src/preparar_validacao_humana.py --modo divergentes --limite 0
python src/preparar_validacao_humana.py --modo divergentes --limite 0 --aplicar
```

Reset controlado do experimento:

```bash
python src/resetar_experimento.py
python src/resetar_experimento.py --aplicar --confirmar RESETAR
```

## Workflows

1. `etapa1_turnos.yml`: classificacao progressiva, agendada a cada 15 minutos.
2. `dashboard.yml`: exporta os JSONs publicos do painel para `docs/dados`, agendado a cada 30 minutos.
3. `etapa2_reclassificacao.yml`: reclassificacao, disparo manual.
4. `reclassificacao_robusta.yml`: modelo pesado local, disparo manual.
5. `preparar_validacao.yml`: monta a aba `VALIDACAO_HUMANA`, disparo manual.
6. `resetar.yml`: reset seguro, disparo manual com confirmacao.
7. `classificacao_incremental.yml`: fluxo incremental antigo, mantido manual.
8. `multimodelo_classificacao.yml`: classificacao por modelo em `CLASSIF__<modelo>`, manual, dry-run por padrao.
9. `multimodelo_reclassificacao.yml`: reclassificacao por modelo em `RECLASS__<modelo>`, manual, dry-run por padrao.

## Dashboard publico

O painel esta em:

```text
docs/index.html
```

Ele consome:

```text
docs/dados/log_turnos_classificacao.json
docs/dados/metricas_por_categoria.json
docs/dados/log_turnos_reclassificacao.json
docs/dados/metricas_experimento.json
docs/dados/resumo.json
```

O site publicado pelo GitHub Pages deve identificar o projeto como `Classificacao de Chamados - Painel Experimental`. A referencia a Malha IA deve aparecer apenas como contexto de origem, nao como nome principal do site.

## Documentacao

1. `CONTEXTO.md`: panorama vivo do repositorio, decisoes e proximos passos.
2. `docs/GUIA_TECNICO.md`: explicacao dos scripts, colunas, executores e fluxos.
3. `dados/README.md`: schemas dos artefatos JSON internos.
4. `docs/index.html`: painel publico com graficos, tabelas, metricas e aba de documentacao.

## Apps Script

`apps_script/Code.gs` e legado. O fluxo principal atual usa conta de servico com `gspread`.

Manter Apps Script apenas como referencia historica ou alternativa ate decisao de remocao definitiva.

## Privacidade

Nao versionar credenciais, IDs privados de planilha, tokens, URLs privadas de Web App ou arquivos JSON que contenham texto real de chamados.
