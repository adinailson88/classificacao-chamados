# Piloto `COPIA` sem IMPORTRANGE

## Objetivo

Retirar toda dependência de fórmulas externas de `COPIA!A:F` sem alterar `G:Q`.

A aba `COPIA` é o ambiente de validação. A aba principal `CHAMADOS_ESQUELETO_REDUZIDO` não deve ser alterada nesta etapa.

## Estado validado em 18/09/2026

Leitura direta da planilha mostrou:

- 14.338 registros no bloco vigente do `SNAPSHOT_ETAPA_1`;
- 14.338 IDs únicos;
- `COPIA!A` coincide integralmente com o snapshot;
- `COPIA!B` coincide integralmente com o título da fonte histórica;
- `COPIA!C` coincide integralmente com a categoria histórica;
- nenhum erro visível em `COPIA!A:F`;
- dois IDs mais recentes no snapshot: `2026090315` e `2026090316`;
- esses dois IDs já estão em `COPIA`, com A:C preenchidas e D:F vazias;
- a aba oculta `COPIA_GLPI_FALLBACK` contém 69 descrições recuperadas diretamente do GLPI para uso na sincronização posterior;
- a migração inicial não depende dessas 69 descrições porque preserva literalmente o que já está visível em A:F.

## Estratégia em duas fases

### Fase 1 — materialização conservadora

Funções:

`preflightCopiaSemImportrange()`

`aplicarCopiaSemImportrange()`

A migração inicial:

1. usa `SNAPSHOT_ETAPA_1` como autoridade para linha -> ID;
2. valida que `COPIA!A` coincide com o snapshot;
3. valida B e C contra a fonte histórica materializada `Pagina1`;
4. bloqueia se houver erro visível em A:F;
5. preserva literalmente os valores atualmente exibidos em B:F;
6. cria backup completo da aba `COPIA`;
7. substitui A:F por valores;
8. remove resíduos/fórmulas A:F abaixo da última linha coberta pelo snapshot, desde que G:Q estejam vazias nessa região;
9. relê A:F e exige igualdade integral com o plano;
10. relê G:Q e exige igualdade integral com o estado anterior;
11. exige zero fórmulas remanescentes em A:F.

A retirada de IMPORTRANGE, portanto, não é combinada com atualização semântica dos dados.

### Fase 2 — sincronização por ID

Depois de materializar A:F:

`simularSincronizacaoCopiaPorId()`

e, somente após revisar o preview:

`sincronizarCopiaPorId()`

A sincronização lê diretamente, sem IMPORTRANGE:

- histórico: `Indicadores - GLPI / Pagina1`;
- GLPI corrente: `GLPI_CHAMADOS_MANUTENCAO_ADINAILSON_TESTE / GLPI`;
- OSM: `Histórico - Planilha de manutenção / Ordens de Serviços`;
- fallback privado: `COPIA_GLPI_FALLBACK`.

Para registros existentes:

- A = chave imutável;
- B:C = fonte GLPI corrente, com histórico como fallback;
- D = GLPI corrente; se ausente, fallback privado; se ainda ausente, preserva D atual;
- E:F = OSM agregada pelo ID.

IDs presentes apenas no GLPI corrente não são inseridos automaticamente enquanto `allowNewIds=false`.

## Aba privada de fallback

Foi criada na planilha experimental a aba oculta:

`COPIA_GLPI_FALLBACK`

Estrutura:

- A = ID Chamado;
- B = DESCRIÇÃO GLPI.

Ela contém 69 registros recuperados do GLPI real. O conteúdo não deve ser copiado para o repositório público.

## Script

`scripts/sincronizar_copia_sem_importrange.gs`

O arquivo pode ser adicionado ao projeto Apps Script vinculado à planilha.

## Execução

1. Adicionar o script ao projeto Apps Script.
2. Executar apenas `preflightCopiaSemImportrange()`.
3. Conferir `PREVIEW_COPIA_A_F`.
4. O status deve ser `APTA`.
5. Não executar a aplicação se houver qualquer bloqueio.
6. Se o preview estiver correto, escrever `APLICAR_COPIA` em `PREVIEW_COPIA_A_F!B1`.
7. Executar `aplicarCopiaSemImportrange()`.
8. Confirmar:
   - zero fórmulas A:F;
   - zero divergências no readback;
   - G:Q inalteradas;
   - backup criado.
9. Só depois executar `simularSincronizacaoCopiaPorId()`.

Não instalar gatilho nesta etapa.
Não alterar a aba principal.
Não executar nenhuma atualização no GLPI.
