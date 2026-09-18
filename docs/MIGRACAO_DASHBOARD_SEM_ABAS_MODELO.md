# Migração do dashboard para artefatos

## Limite de escopo

Esta migração não altera `CHAMADOS_ESQUELETO_REDUZIDO`, `COPIA`, suas fórmulas,
gatilhos, sincronizações ou rotinas. Também não remove nem modifica abas da
planilha durante a fase de validação.

## Fase 1 — classificação

Depois da exportação normal do dashboard, o workflow cria um pacote com os
arquivos sanitizados `registros_<modelo>.json`. O pacote:

- não contém ID nem texto de chamado;
- possui manifesto com SHA-256, tamanho e quantidade de registros;
- é armazenado como artefato da execução por 30 dias;
- mantém as abas `CLASSIF__*` e o fluxo atual como contingência;
- não muda a fonte lida pelo dashboard nesta fase.

Critério para avançar: observar ao menos uma execução completa e confirmar, para
cada modelo, igualdade de arquivo e hash entre `docs/dados` e o pacote.

## Próximas fases

1. Fazer o produtor dos modelos alimentar diretamente o pacote sanitizado.
2. Fazer o dashboard preferir os artefatos e usar as abas como fallback.
3. Observar uma execução completa sem divergências.
4. Só então interromper a escrita em `CLASSIF__*`.
5. Repetir o processo para `RECLASS__*`, snapshot e logs detalhados.

Nenhuma exclusão de aba faz parte desta alteração.
