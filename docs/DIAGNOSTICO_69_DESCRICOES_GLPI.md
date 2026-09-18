# Diagnóstico read-only — 69 Tickets históricos do GLPI

Objetivo: recuperar `content` (descrição) e `solution` dos 69 Tickets históricos que existem no snapshot do experimento, mas não no espelho GLPI usado pela planilha atual.

## Segurança

Este diagnóstico:

- usa somente `GET Ticket/{id}`;
- não executa PUT;
- não altera Ticket;
- não altera categoria;
- não altera Google Sheets;
- não imprime descrição/solução no terminal;
- grava o conteúdo somente em arquivos locais ignorados pelo Git.

O GLPI alvo é 9.1.1. Nessa versão, a tabela `glpi_tickets` contém diretamente os campos `content` e `solution`; portanto não é usada a entidade `ITILSolution`, introduzida posteriormente.

## Arquivo

`src/diagnosticar_descricoes_glpi.py`

A lista de 69 IDs está congelada dentro do script e é validada como 69 IDs únicos antes de abrir a sessão.

## Variáveis de ambiente

São as mesmas da automação GLPI:

- `GLPI_URL` — URL HTTPS terminada em `/apirest.php`;
- `GLPI_USER_TOKEN`;
- `GLPI_APP_TOKEN`.

Não coloque tokens no Git nem em arquivos versionados.

## Execução

No PowerShell, a partir da raiz do repositório:

```powershell
python .\src\diagnosticar_descricoes_glpi.py
```

O terminal mostra somente contagens.

Saídas privadas locais:

- `diagnostico_descricoes_glpi.local.json`;
- `diagnostico_descricoes_glpi.local.csv`.

Ambas estão no `.gitignore`.

## Campos do CSV

- `id_chamado`
- `existe`
- `status`
- `descricao`
- `solucao`
- `descricao_composta`
- `erro`

`descricao_composta` segue o formato usado anteriormente pela planilha:

```text
Descrição - <content>

Solução - <solution>
```

## Interpretação

- `RECUPERADO`: Ticket existe e tem descrição; pode ser avaliado para recompor D.
- `SEM_DESCRICAO`: Ticket existe, mas `content` está vazio.
- `NAO_ENCONTRADO`: GET retornou 404.
- `RESPOSTA_TICKET_INVALIDA`: o ID devolvido pelo servidor não coincide com o solicitado.
- `ERRO_API`: falha de comunicação/permissão; o script continua nos demais IDs e retorna código 2 ao final.

Não incorporar os resultados à planilha automaticamente. Primeiro auditar os totais e os conteúdos recuperados.
