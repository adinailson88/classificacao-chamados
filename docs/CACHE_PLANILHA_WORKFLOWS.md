# Cache operacional da planilha nos workflows

## Decisao tecnica

Para reduzir estouro de cota do Google Sheets, o workflow `Lote noturno com cache da planilha` concentra a leitura da planilha em uma etapa unica:

1. `src/atualizar_cache_planilha.py` le todas as abas da planilha via conta de servico.
2. O conteudo completo e gravado em `dados/cache_planilha.json`.
3. `dados/cache_planilha.json` e ignorado pelo Git e removido no fim do job, porque pode conter texto livre de chamados.
4. Os scripts de auditoria, dashboard, taxonomia, avaliacao final, analise de erros e estatistica rodam com `PLANILHA_CACHE_JSON=dados/cache_planilha.json`.
5. Somente os agregados sanitizados de `docs/dados/*.json` sao commitados.

## Agendamento

O lote principal roda por GitHub Actions as 02:30 no horario de Bahia (`30 5 * * *` em UTC).

Uma automacao de acompanhamento no Codex deve verificar as 09:00 se o lote terminou. Se estiver falho, cancelado ou incompleto, ela pode disparar o workflow manualmente e continuar o acompanhamento.

## Arquivos envolvidos

- `src/planilha.py`: adiciona modo read-only por cache local via variavel `PLANILHA_CACHE_JSON`.
- `src/atualizar_cache_planilha.py`: materializa o snapshot operacional e o manifesto sanitizado.
- `.github/workflows/lote_noturno_cache.yml`: executa o lote consolidado.
- `docs/dados/cache_planilha_manifest.json`: manifesto publico com contagem de linhas/colunas por aba, sem texto bruto.

## Regra de seguranca

Nao versionar o snapshot bruto da planilha. O repositorio publica dashboard em GitHub Pages, entao texto livre de chamados, IDs e descricoes devem permanecer fora dos commits.
