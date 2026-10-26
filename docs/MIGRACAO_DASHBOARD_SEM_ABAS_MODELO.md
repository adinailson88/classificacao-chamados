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

## Fase 3 — publicação pelo produtor

Depois de uma classificação aplicada, o próprio workflow multimodelo renova e
publica os JSONs sanitizados. A publicação usa um worktree isolado baseado no
`main` remoto mais recente, limita o commit aos arquivos `registros_<modelo>.json`
e à auditoria e repete a tentativa se outro workflow avançar o repositório.

As abas `CLASSIF__*` continuam sendo escritas nesta fase porque ainda existem
consumidores científicos e operacionais que não foram migrados. O produtor passa
a alimentar os artefatos diretamente, mas a retirada das abas permanece proibida
até que esses consumidores sejam inventariados e substituídos.

## Próximas fases

1. Observar uma execução aplicada completa sem divergências.
2. Migrar, individualmente, os consumidores operacionais de `CLASSIF__*`.
3. Manter as rotinas científicas congeladas separadas dos artefatos operacionais.
4. Só então interromper a escrita e avaliar a remoção de `CLASSIF__*`.
5. Repetir o processo para `RECLASS__*`, snapshot e logs detalhados.

Nenhuma exclusão de aba faz parte desta alteração.
