# AGENTS.md - classificacao-chamados

## Regime de trabalho

Atuar em modo tecnico, objetivo e verificavel. Nao presumir dados da planilha sem leitura direta.

Quando houver insuficiencia de dados, declarar exatamente: `Informação insuficiente para verificar.`

## Escopo do repositorio

Este repositorio implementa um experimento independente de classificacao e reclassificacao automatica de chamados, conforme roteiro metodologico do Malha IA.

O projeto nao deve alterar o repositorio operacional `malha-ia` nem seus workflows. Scripts aqui devem ser novos, ainda que possam consultar padroes tecnicos ja existentes.

## Regras da planilha experimental

1. A planilha principal vai de `A:M`.
2. As colunas devem ser localizadas por cabecalho, nao por posicao fixa herdada.
3. Linhas totalmente vazias devem ser ignoradas.
4. O total de linhas deve ser dinamico; o script nao deve assumir quantidade fixa.
5. A leitura deve considerar crescimento futuro da planilha.
6. Escritas na planilha so podem ocorrer quando o comando tiver flag explicita de aplicacao.

## Colunas esperadas

```text
ID Chamado
TÍTULO
CATEGORIA COMPLETA
DESCRIÇÃO GLPI
TÍTULO O.S.M.
DESCRIÇÃO O.S.M.
Classificação IA
Avaliação (%)
Executor
Criticidade Atribuída por IA
Comparação
Classificado_Confiança_IA
CONFERÊNCIA
```

## Validacao

Validar sintaxe Python com:

```bash
python -m py_compile src/validar_planilha_experimento.py
```

Nao declarar acesso a Google Sheets como validado sem execucao real com credenciais.
