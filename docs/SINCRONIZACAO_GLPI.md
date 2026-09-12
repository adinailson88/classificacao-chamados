# Sincronizacao de categorias com o GLPI 9.1.1

O workflow `sincronizar_correcoes_glpi.yml` usa a API REST V1 do GLPI e a fila
privada `CORRECOES_GLPI_POR_ID`. O modo padrao e `dry-run`; nele, nenhuma celula
e nenhum chamado sao alterados.

## Contrato da fila

Cada registro e persistido pelo `ID Chamado`. As colunas `A:C` nao podem voltar
a ser uma lista dinamica, pois isso deslocaria aprovacao e carimbos. A aba
`FONTE_Q_ATUAL` preserva o `FILTER` da planilha original apenas para conferencia.

Uma escrita no GLPI exige todos os gates abaixo:

1. ID unico na fila e na planilha original;
2. coluna M da planilha original igual a `Errado`;
3. categorias anterior e correta identicas entre fila e fonte atual;
4. `Aprovado para GLPI` igual a `SIM`;
5. `Sincronizado em` vazio;
6. categoria correta encontrada por correspondencia exata e unica no catalogo
   ativo `ITILCategory`;
7. categoria atual do chamado ainda igual a categoria anterior validada;
8. confirmacao literal `APLICAR_GLPI`, secret de habilitacao e ambiente protegido.

Depois do `PUT`, o script rele o chamado. Somente a confirmacao do novo
`itilcategories_id` preenche `Sincronizado em` e marca `ATUALIZADO`.

## Configuracao necessaria no GitHub

Secrets do repositorio:

- `SPREADSHEET_ID`: planilha principal;
- `GLPI_CORRECOES_SPREADSHEET_ID`: planilha privada da fila;
- `GCP_SA_KEY`: conta de servico com acesso as duas planilhas;
- `GLPI_BASE_URL`: URL HTTPS da instalacao, sem token;
- `GLPI_APP_TOKEN`;
- `GLPI_USER_TOKEN`;
- `HABILITAR_ESCRITA_GLPI`: manter ausente durante os testes; definir como `SIM`
  somente quando a escrita for autorizada.

O ambiente `glpi-producao` deve exigir aprovacao humana. A conta da API deve ter
permissiao minima para ler chamados e categorias e alterar apenas a categoria.
O GLPI 9.1.1 tambem exige um cliente de API ativo compativel com o IP do runner.
Se a instancia estiver restrita a rede institucional, use runner `self-hosted`.

## Sequencia operacional

1. Compartilhar a fila com a conta de servico.
2. Cadastrar os secrets, sem habilitar a escrita.
3. Executar `dry-run` com `limite=1` e um ID explicitamente escolhido.
4. Conferir o artefato JSON e o chamado diretamente no GLPI.
5. Marcar `SIM` apenas nesse ID.
6. Configurar a aprovacao do ambiente e habilitar o secret de escrita.
7. Executar `aplicar`, `limite=1` e confirmacao `APLICAR_GLPI`.
8. Conferir o chamado, os carimbos da fila e `LOG_SINCRONIZACAO_GLPI`.

Somente apos esse piloto deve ser considerado um lote maior.
