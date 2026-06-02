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

## Validacao com credencial Google Sheets

Depois de liberar a credencial/token:

```bash
python src/validar_planilha_experimento.py --credenciais caminho/credenciais.json
```

O comando acima apenas valida estrutura e contabiliza linhas nao vazias. Ele nao altera a planilha.
