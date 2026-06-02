# Classificacao de Chamados

Repositorio experimental para avaliacao da evolucao da classificacao e reclassificacao automatica de chamados, separado do repositorio operacional Malha IA.

## Objetivo

Implementar scripts novos para executar um experimento rastreavel com:

1. leitura da planilha experimental;
2. validacao estrutural da aba principal;
3. classificacao inicial por turnos;
4. reclassificacao de chamados abaixo do limiar definido;
5. logs por turno;
6. logs linha a linha;
7. metricas de concordancia IA x classificacao historica;
8. preparacao posterior para validacao humana.

## Premissas atuais

1. A planilha experimental e `CHAMADOS_ESQUELETO_REDUZIDO`.
2. A aba principal vai somente ate a coluna `M`.
3. O restante da planilha esta vazio.
4. Linhas vazias nao entram no experimento.
5. A quantidade de linhas pode aumentar.
6. O script deve mapear colunas por cabecalho.
7. Nenhuma rotina deve sobrescrever dados sem flag explicita.

## Colunas da aba principal

```text
A  ID Chamado
B  TÍTULO
C  CATEGORIA COMPLETA
D  DESCRIÇÃO GLPI
E  TÍTULO O.S.M.
F  DESCRIÇÃO O.S.M.
G  Classificação IA
H  Avaliação (%)
I  Executor
J  Criticidade Atribuída por IA
K  Comparação
L  Classificado_Confiança_IA
M  CONFERÊNCIA
```

## Abas experimentais previstas

```text
EXPERIMENTO_CONFIG
LOG_TURNOS_CLASSIFICACAO
LOG_LINHA_A_LINHA
SNAPSHOT_ETAPA_1
LOG_TURNOS_RECLASSIFICACAO
VALIDACAO_HUMANA
METRICAS_EXPERIMENTO
```

## Primeira validacao local

```bash
python -m py_compile src/validar_planilha_experimento.py
python src/validar_planilha_experimento.py --help
```

## Validacao com Apps Script Web App

Use este modo quando a planilha estiver conectada por Apps Script:

```bash
python src/validar_planilha_experimento.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN"
```

O comando apenas valida estrutura e contabiliza linhas nao vazias. Ele nao altera a planilha.

Nao versionar a URL privada nem o token.

## Preparacao das abas experimentais

Primeiro rode somente em modo seguro:

```bash
python src/preparar_abas_experimento.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN"
```

Para aplicar a criacao/atualizacao das abas, o Apps Script precisa conter o arquivo `apps_script/Code.gs` deste repositorio e estar implantado em nova versao.

Depois disso:

```bash
python src/preparar_abas_experimento.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN" --aplicar
```

O comando cria ou valida as abas experimentais e grava apenas cabecalhos. Ele nao classifica chamados e nao limpa a aba principal.

## Registro da configuracao experimental

Depois de atualizar e implantar o Apps Script com `apps_script/Code.gs`, rode primeiro:

```bash
python src/registrar_config_experimento.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN"
```

Para gravar a ficha tecnica na aba `EXPERIMENTO_CONFIG`:

```bash
python src/registrar_config_experimento.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN" --aplicar
```

Esse comando grava apenas a aba `EXPERIMENTO_CONFIG`.

Os totais de linhas gravados nessa aba sao valores observados no momento da execucao. Eles nao sao limites fixos; a planilha pode crescer e os scripts devem sempre reler a quantidade atual.

Datas e horas do experimento devem usar horario local de Itabuna/Bahia (`America/Bahia`, UTC-03:00), por exemplo `2026-06-01T23:40:37-03:00`.

## Snapshot inicial

Antes de classificar, gere um snapshot do estado atual das linhas nao vazias:

```bash
python src/registrar_snapshot_inicial.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN"
```

Para gravar em `SNAPSHOT_ETAPA_1`:

```bash
python src/registrar_snapshot_inicial.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN" --aplicar
```

Esse comando rele a aba principal no momento da execucao, ignora linhas vazias e nao usa quantidade fixa.

## Classificacao inicial - selecao de lote

A primeira versao do motor apenas seleciona o proximo lote elegivel, sem classificar e sem escrever em `G:J`:

```bash
python src/classificar_lote_inicial.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN"
```

Uma linha e elegivel quando:

1. nao esta vazia;
2. possui texto classificavel em titulo/descricoes;
3. `Classificacao IA` ainda esta vazia.

O tamanho padrao do lote vem de `config_experimento.json`.

## Classificacao inicial - baseline dry-run

Para gerar previsoes sem escrever na planilha:

```bash
python src/classificar_lote_baseline.py --apps-script-url "URL_DO_WEB_APP" --token "TOKEN"
```

O baseline atual usa TF-IDF + LogisticRegression, treinado com categorias historicas da planilha e excluindo o lote selecionado do treino. O resultado e apenas comparacao preliminar com a classificacao historica, nao acuracia validada.

## Validacao com credencial Google Sheets

Depois de liberar a credencial/token:

```bash
python src/validar_planilha_experimento.py --credenciais caminho/credenciais.json
```

O comando acima apenas valida estrutura e contabiliza linhas nao vazias. Ele nao altera a planilha.
