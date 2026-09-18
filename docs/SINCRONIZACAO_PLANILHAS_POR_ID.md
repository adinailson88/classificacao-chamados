# Sincronização A:F por ID — substituição do IMPORTRANGE

## Motivo

A aba `CHAMADOS_ESQUELETO_REDUZIDO` depende de importações externas nas colunas A:F.

A:D usam quatro `IMPORTRANGE` de colunas inteiras da planilha `CHAMADOS`. Em 17/09/2026, a API do Google Sheets retornou `#REF!` / `Import Range internal error.` em A2:D2.

E:F são ainda mais custosas: cada linha contém fórmulas `FILTER(IMPORTRANGE(...))` contra a planilha de Ordens de Serviço. Isso repete as mesmas importações externas milhares de vezes. A auditoria ao vivo confirmou fórmulas E:F inclusive abaixo da última linha válida do snapshot, reforçando a necessidade de retirar toda a dependência A:F.

O risco não é apenas indisponibilidade. A:D variáveis combinadas com G:Q materializadas permitem deslocamento lógico entre ID e conferências humanas.

## Auditoria antes da implementação

Foi verificado ao vivo:

- planilha destino: `1lohPUQOgxzt_DMxnNLKMxnieZq1sVmh4uwBLbbgvfiQ`;
- fonte CHAMADOS: `1VgHY6NmCQLtA3lcfQAzGIRqJFZGHwcGhZ4zaXkqOmz4`;
- fonte Ordens de Serviços: `1zTSo5oTFDyo3espWmYl1WjpFU57PwHDeZqnxUkrGQ2Y`;
- `SNAPSHOT_ETAPA_1` possui bloco final completo de 14.336 registros;
- esse bloco cobre continuamente `linha_planilha=2` até `14337`;
- há 14.336 IDs não vazios e 14.336 IDs únicos;
- não foi encontrada duplicidade nesse bloco final;
- a aba `Ordens de Serviços` possui 8.789 linhas de grade e usa:
  - B = chamado vinculado;
  - C = resumo;
  - E = descrição.

## Estratégia

A migração inicial usa o snapshot como autoridade para `linha atual -> ID Chamado`.

Para cada linha 2..N:

1. recuperar o ID pelo snapshot mais recente;
2. localizar o ID na fonte `CHAMADOS`;
3. materializar:
   - A = ID;
   - B = título da fonte;
   - C = categoria da fonte;
   - D = descrição GLPI;
4. agregar as Ordens de Serviço pelo mesmo ID e materializar:
   - E = títulos unidos por `; `;
   - F = descrições unidas por `; `;
5. não escrever em G:Q.

A sincronização posterior abandona o número da linha como chave. A coluna A passa a ser fixa; B:F são atualizadas apenas pelo ID e IDs novos são acrescentados ao final.

## Arquivo

Use `scripts/sincronizar_planilhas_por_id.gs` em um projeto Google Apps Script com acesso às três planilhas.

## Execução segura

### 1. Preflight

Execute:

`preflightMigracaoImportrange()`

O script cria/atualiza apenas a aba `PREVIEW_SINCRONIZACAO_A_F`.

Nenhuma célula A:Q da aba principal é alterada.

O status deve ser `APTA`. Se houver qualquer bloqueio, não prossiga.

### 2. Autorizar migração

Somente depois de revisar o preview, digite exatamente:

`APLICAR_MIGRACAO`

em:

`PREVIEW_SINCRONIZACAO_A_F!B1`

### 3. Aplicar migração

Execute:

`aplicarMigracaoImportrange()`

Antes da escrita, o script recalcula todo o preflight.

Em seguida:

- duplica a aba principal como `BACKUP_PRE_MIGRACAO_AF_YYYYMMDD_HHMMSS`;
- materializa somente A:F;
- não escreve em G:Q;
- relê A:F integralmente;
- exige igualdade com o plano;
- verifica que G:Q não possuem dados além da última linha coberta pelo snapshot;
- remove resíduos A:F abaixo dessa última linha, inclusive fórmulas E:F antigas que tenham sido preenchidas além do conjunto válido;
- registra resumo em `LOG_SINCRONIZACAO_A_F`.

### 4. Simular sincronização normal

Depois da migração, execute:

`simularSincronizacaoPorId()`

Ela identifica alterações B:F e IDs novos, sem alterar a aba principal.

### 5. Sincronizar manualmente

Se a simulação estiver correta:

`sincronizarChamadosPorId()`

Regras:

- A nunca é alterada para IDs já existentes;
- B:F são atualizadas pelo ID;
- IDs novos entram ao final;
- G:Q nunca são escritos;
- IDs ausentes da fonte bloqueiam a execução;
- IDs duplicados bloqueiam a execução;
- mais de 100 novos IDs em uma execução bloqueiam;
- mais de 500 registros existentes alterados em uma execução bloqueiam;
- qualquer `IMPORTRANGE` remanescente em A:F bloqueia a sincronização normal.

### 6. Automação

Somente após ciclos manuais validados, execute:

`instalarGatilhoSincronizacao()`

O padrão atual é a cada 2 horas.

Para remover:

`removerGatilhosSincronizacao()`

## Relação com a automação GLPI

A automação de correções GLPI permanece pausada.

Seu estado está preservado na branch `feat/glpi-correcoes-seguras`, em `docs/CODEX_PROXIMA_SESSAO.md`.

Não habilitar `GLPI_BATCH_ENABLED=true` nem executar PUT no GLPI até A:F estarem materializadas, sincronizadas por ID e validadas.
