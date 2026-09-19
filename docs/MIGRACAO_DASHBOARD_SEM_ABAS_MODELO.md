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

## Fase 2 — preferência pelos artefatos

As atualizações regulares do dashboard usam primeiro os JSONs sanitizados já
validados em `docs/dados`, sem reler as abas `CLASSIF__*`. A planilha permanece
como contingência automática quando o conjunto de artefatos estiver ausente ou
inconsistente.

Os artefatos são renovados diretamente das abas nas seguintes situações:

- execuções programadas realizadas durante a faixa das 03h UTC;
- conclusão dos workflows já conectados ao dashboard;
- execução manual com `atualizar_modelos=true`;
- fallback automático quando a validação dos artefatos falhar.

Essa etapa reduz as leituras repetidas das abas de modelos, mas ainda não
interrompe sua atualização nem autoriza sua remoção.

## Próximas fases

1. Fazer o produtor dos modelos alimentar diretamente o pacote sanitizado.
2. Observar uma execução completa sem divergências.
3. Só então interromper a escrita em `CLASSIF__*`.
4. Repetir o processo para `RECLASS__*`, snapshot e logs detalhados.

Nenhuma exclusão de aba faz parte desta alteração.
