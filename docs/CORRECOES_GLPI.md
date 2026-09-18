# Correções operacionais de categoria no GLPI

A origem é `CHAMADOS_ESQUELETO_REDUZIDO` (A:Q). A rotina seleciona por **ID Chamado** os registros com M = `Errado`, Q preenchida e C diferente de Q. Antes de elegê-los, usa `src/decisao_validada.py` para verificar N/P e a categoria manual. Conflitos ficam na fila para revisão humana e nunca seguem para PUT. A aba `FILA_CORRECOES_GLPI` contém valores fixos; a aprovação fica vinculada ao ID, nunca à posição de uma linha da origem.

## Colunas da fila

| Coluna | Uso |
| --- | --- |
| `id_chamado` | Chave única; ID interno do Ticket no GLPI. |
| `titulo` | Referência privada para revisão humana. |
| `categoria_glpi_planilha` | Categoria C no momento de materialização; origem esperada na API. |
| `categoria_correta` | Categoria Q aprovada como destino. |
| `situacao_validacao` | `ELEGIVEL` ou `CONFLITO`. |
| `aprovado_glpi` | Checkbox; só `TRUE` permite PUT. A rotina não a desmarca. |
| `status_glpi` | Resultado da tentativa, inclusive bloqueios. |
| `categoria_api_antes` | Nome completo lido do GLPI antes da decisão. |
| `categoria_api_depois` | Nome completo lido após PUT ou destino previsto no dry-run. |
| `data_candidato` | Criação do candidato na fila. |
| `data_execucao` | Confirmação ou tentativa na API, em UTC. |
| `erro` | Motivo objetivo de bloqueio ou falha, sem credenciais. |

O upsert preserva aprovação, origem, destino e trilha de auditoria das linhas já aprovadas. Novos candidatos entram com aprovação falsa. A rotina não escreve em M/N/P/Q. Antes de aprovar, confira ID, título, origem, destino e `situacao_validacao=ELEGIVEL` na aba da fila. Marque a checkbox somente para os IDs conferidos. Se uma linha aprovada entrar em `CONFLITO`, revise a fonte; para recalcular o candidato, retire manualmente a aprovação e gere a fila novamente antes de uma nova aprovação.

Registros `APLICADO` ou `JA_APLICADO` permanecem concluídos mesmo quando C passa a ser igual a Q e deixam de aparecer entre os candidatos. Uma correção nova para o mesmo ID exige revisão humana explícita; a rotina não reaproveita a aprovação anterior.

## Log privado append-only

Em modo `--aplicar`, cada tentativa processada acrescenta uma linha em `LOG_CORRECOES_GLPI`, sem título nem descrição. As colunas são `run_id`, `data_hora` (UTC), `id_chamado`, `categoria_api_antes`, `categoria_destino`, `status`, `categoria_api_depois` e `erro`. O log é preparado antes de qualquer PUT, e cada resultado é acrescentado antes de atualizar o estado corrente da fila. A rotina não sobrescreve linhas históricas. Dry-run e `--teste` não escrevem no log. A conta de serviço precisa de permissão para criar e acrescentar linhas nessa aba privada.

## Execução local

Requer Python 3.11, `requirements-leves.txt`, `SPREADSHEET_ID`, `GOOGLE_APPLICATION_CREDENTIALS` (JSON da conta de serviço), `GLPI_URL` (URL HTTPS terminada em `/apirest.php`), `GLPI_USER_TOKEN` e `GLPI_APP_TOKEN`. A conta de serviço precisa ler a aba principal e escrever somente a fila. O usuário da API GLPI deve ter acesso de leitura a Ticket/ITILCategory e direito mínimo para atualizar a categoria dos tickets permitidos. Segredos jamais entram no Git.

```bash
python src/gerar_fila_correcoes_glpi.py
python src/gerar_fila_correcoes_glpi.py --aplicar
python src/aplicar_correcoes_glpi.py --teste --ids 123,456 --limite 2
python src/aplicar_correcoes_glpi.py --aplicar --ids 123,456 --limite 2
```

A geração da fila é dry-run por padrão e requer `--aplicar` para escrever **somente na aba da fila**. O executor também é dry-run por padrão; `--teste` autentica e lê sem PUT. Use IDs previamente aprovados e um limite pequeno no primeiro teste real. Não execute `--aplicar` contra o GLPI antes de confirmar conectividade, permissões e o resultado do preflight.

Antes de PUT, o executor lê Ticket por ID e toda a taxonomia `ITILCategory`. O nome completo da categoria deve corresponder **exatamente** a um único `completename`; não há busca aproximada nem IDs fixos. Se o ticket já aponta ao destino, registra `JA_APLICADO`. Se a categoria atual não corresponde à origem registrada, registra `BLOQUEADO_DIVERGENCIA`. Verifica `is_incident` ou `is_request` conforme `Ticket.type`. Após toda tentativa de PUT, faz novo GET. Registra `APLICADO` quando o GET retorna o ID de destino, mesmo se a resposta PUT for atípica ou trouxer erro; nesse caso, `erro` conserva a ressalva para auditoria. `ERRO` indica que o GET posterior não confirmou o destino ou que a leitura falhou. Aprovações TRUE permanecem na fila. Status `APLICADO` e `JA_APLICADO` são ignorados nas próximas execuções.

## Workflow semanal

`.github/workflows/correcoes_glpi.yml` roda às segundas, 09:00 UTC, ou manualmente. A execução manual com `aplicar=false` permite testar conectividade a partir de um **GitHub-hosted runner** sem definir `GLPI_RUNNER_READY=true`. Informação insuficiente para verificar. O repositório não demonstra que essa instância GLPI é alcançável por tal runner; se a rede for privada, use runner com acesso autorizado e reveja a configuração.

O workflow executa os dois arquivos `test_glpi_*.py`, dry-run da fila, materialização por ID e preflight sem PUT. O passo de aplicação exige **ambas** as variáveis `GLPI_RUNNER_READY=true` e `GLPI_BATCH_ENABLED=true`; execuções manuais exigem ainda a entrada `aplicar=true`. Cada lote é limitado a cinco IDs. No primeiro lote, preencha explicitamente a entrada `ids` com poucos IDs aprovados e confira o readback. O cron não faz PUT sem as duas variáveis. O `workflow_dispatch` no GitHub só ficará disponível depois que o arquivo do workflow entrar na branch padrão; esta implementação não faz merge nem executa o workflow.

Não publique logs privados, títulos, descrições nem planilhas como artifacts públicos. O resumo padrão contém somente contadores por status. Para revisar erros específicos, consulte a aba privada da fila.
