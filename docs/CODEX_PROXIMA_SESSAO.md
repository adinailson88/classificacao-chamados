# CODEX — PRÓXIMA SESSÃO

## Estado congelado antes de tratar o IMPORTRANGE

Branch atual: `feat/glpi-correcoes-seguras`

SHA remoto auditado: `24642fed383c5ddf1a94b4298185f7410605d3e9`

Não fazer merge antes da validação operacional.

### Automação GLPI implementada

A branch contém:

- `src/glpi_client.py`
- `src/gerar_fila_correcoes_glpi.py`
- `src/aplicar_correcoes_glpi.py`
- `tests/test_glpi_fila.py`
- `tests/test_glpi_correcoes.py`
- `.github/workflows/correcoes_glpi.yml`
- `docs/CORRECOES_GLPI.md`

A implementação já contempla:

- fila fixa por `ID Chamado`;
- aprovação por checkbox booleano;
- validação com `decisao_validada.py`;
- conflitos bloqueados;
- dry-run por padrão;
- consulta GET antes do PUT;
- correspondência exata de `ITILCategory.completename`;
- bloqueio quando a categoria atual diverge do snapshot aprovado;
- validação incidente/requisição;
- PUT apenas de `itilcategories_id`;
- GET posterior obrigatório, validando ID do Ticket e categoria de destino;
- suporte à resposta documentada do GLPI 9.1.1 no formato `[{"123": true}]`;
- idempotência para `APLICADO` e `JA_APLICADO`;
- aba append-only `LOG_CORRECOES_GLPI`;
- workflow com preflight manual sem PUT;
- PUT condicionado a `GLPI_RUNNER_READY=true`, `GLPI_BATCH_ENABLED=true` e, em execução manual, `aplicar=true`;
- testes `test_glpi_*.py`.

Último retorno do executor informou 1.086 testes totais e 37 testes GLPI locais aprovados. Ainda não houve PUT real no GLPI.

## Bloqueador operacional atual

A planilha experimental é:

`1lohPUQOgxzt_DMxnNLKMxnieZq1sVmh4uwBLbbgvfiQ`

Aba:

`CHAMADOS_ESQUELETO_REDUZIDO`

As colunas A:D são alimentadas por `IMPORTRANGE` da planilha fonte:

`1VgHY6NmCQLtA3lcfQAzGIRqJFZGHwcGhZ4zaXkqOmz4`

aba `CHAMADOS`.

Verificação ao vivo encontrou em A2:D2 erro:

`#REF!`

com mensagem da API Google Sheets:

`Import Range internal error.`

As fórmulas seguem apontando para:

- A <- `CHAMADOS!A2:A`
- B <- `CHAMADOS!B2:B`
- C <- `CHAMADOS!M2:M`
- D <- `CHAMADOS!W2:W`

A fonte `CHAMADOS` continua existindo e acessível.

As colunas humanas continuam preenchidas; foram observados 571 registros com `CONFERÊNCIA GLPI = Errado`.

Sem a coluna A confiável, não há chave `ID Chamado` segura para criar/aplicar a fila GLPI.

## Decisão atual

Pausar temporariamente a frente GLPI.

Antes de continuar com Codex ou qualquer PUT real, estabilizar a alimentação A:D e retirar o `IMPORTRANGE` do caminho crítico.

Arquitetura alvo:

`GLPI -> CHAMADOS -> sincronização por ID -> CHAMADOS_ESQUELETO_REDUZIDO -> FILA_CORRECOES_GLPI -> GLPI`

A sincronização deve ser feita por `ID Chamado`, nunca por número de linha.

### Regras da futura sincronização A:D

- A = ID Chamado
- B = Título
- C = Categoria completa
- D = Descrição GLPI
- localizar registros na planilha experimental por ID;
- atualizar B:D do mesmo ID;
- acrescentar IDs novos ao final;
- não excluir automaticamente IDs ausentes da fonte;
- não ordenar linhas;
- nunca deslocar ou sobrescrever G:Q;
- nunca usar número de linha como chave;
- abortar em caso de ID vazio ou duplicado;
- manter log das operações;
- idealmente usar Google Apps Script ou rotina equivalente no ecossistema Google, sem `IMPORTRANGE`.

## Retomada da automação GLPI

Somente após A:D estarem estáveis:

1. validar novamente os candidatos `M=Errado`, Q preenchida e C != Q;
2. confirmar todos os IDs;
3. materializar `FILA_CORRECOES_GLPI`;
4. executar preflight somente leitura;
5. validar conectividade e permissões do GLPI;
6. testar no máximo 1–2 IDs aprovados;
7. só depois considerar habilitar lote semanal.

Até lá:

- não definir `GLPI_BATCH_ENABLED=true`;
- não executar `--aplicar` contra o GLPI;
- não fazer merge da branch.
