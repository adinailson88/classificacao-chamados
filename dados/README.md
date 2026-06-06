# dados/ — estado do experimento (GitHub-first, export em lote)

Esta pasta guarda o estado intermediário do experimento de classificação **no
repositório** (não na planilha). A planilha do Google só é tocada para:

1. **ler a fonte UMA vez** por execução (gera o snapshot);
2. **exportar o resultado de cada etapa UMA vez**, em gravação em bloco.

Assim o número de chamadas de API cai de "uma por linha/turno" para
"uma leitura + uma escrita por etapa".

## Fluxo

```
registrar_snapshot_inicial.py  -> dados/snapshot_etapa_1.json   (lê a planilha 1x)
classificar_etapa.py           -> dados/classificacao_etapa_1.json
                                  dados/log_turnos.jsonl
                                  dados/log_linha_a_linha.jsonl
                                  dados/metricas_experimento.json
exportar_etapa.py --aplicar    -> grava G:J na planilha (1 escrita gspread em lote)
                                  dados/manifest_exportacao.json
```

Nenhum script escreve na planilha sem a flag explícita `--aplicar`.

## Arquivos

### `snapshot_etapa_1.json`
INPUT congelado, lido da aba principal (`CHAMADOS_ESQUELETO_REDUZIDO`, `A:M`).

```json
{
  "run_id": "EXP_...",
  "gerado_em": "2026-06-03T10:00:00-03:00",
  "aba_origem": "CHAMADOS_ESQUELETO_REDUZIDO",
  "range_leitura": "A:M",
  "colunas": ["ID Chamado", "...", "CONFERÊNCIA"],
  "total_linhas_lidas": 0,
  "total_nao_vazias": 0,
  "linhas": [
    {
      "linha_planilha": 2,
      "valores": ["...13 células..."],
      "id_chamado": "...",
      "categoria_original": "...",
      "classificacao_ia": "",
      "conferencia": "",
      "texto_classificacao": "TÍTULO + DESCRIÇÃO GLPI + TÍTULO O.S.M. + DESCRIÇÃO O.S.M."
    }
  ]
}
```

### `classificacao_etapa_1.json`
Resultado por linha. As 4 primeiras saídas (`classificacao_ia`, `avaliacao_pct`,
`executor`, `criticidade`) correspondem às colunas **G, H, I, J** exportadas.

```json
{
  "run_id": "EXP_...",
  "gerado_em": "2026-06-03T10:05:00-03:00",
  "modelo": "Baseline_TFIDF_LogReg",
  "estrategia": "out_of_fold_stratified_kfold",
  "total_classificadas": 0,
  "linhas": [
    {
      "linha_planilha": 2,
      "id_chamado": "...",
      "categoria_original": "...",
      "classificacao_ia": "...",
      "avaliacao": 0.8734,
      "executor": "Baseline_TFIDF_LogReg",
      "criticidade": "",
      "comparacao": true,
      "confianca_label": "alta"
    }
  ]
}
```

> `criticidade` (coluna J) fica vazia no baseline; a exportação **não sobrescreve
> célula com valor vazio**, então o J existente na planilha é preservado.

### `log_turnos.jsonl`
Um registro JSON por turno/lote (substitui a aba `LOG_TURNOS_CLASSIFICACAO`).

### `log_linha_a_linha.jsonl`
Um registro JSON por linha processada (substitui a aba `LOG_LINHA_A_LINHA`).

### `metricas_experimento.json`
Métricas agregadas (concordância IA × histórico, acurácia, F1 macro etc.).

### `manifest_exportacao.json`
Controle do que já foi exportado para a planilha e quando.

```json
{
  "exportacoes": [
    {
      "etapa": "classificacao_etapa_1",
      "aba": "CHAMADOS_ESQUELETO_REDUZIDO",
      "colunas": "G:J",
      "linhas_enviadas": 0,
      "linhas_gravadas": 0,
      "linhas_puladas_conferencia": 0,
      "gerado_em": "2026-06-03T10:10:00-03:00",
      "run_id": "EXP_..."
    }
  ]
}
```

## Privacidade
Estes arquivos podem conter o texto dos chamados (descrição GLPI / O.S.M.).
Avalie antes de versionar dados reais em repositório público.
