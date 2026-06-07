# Análise estatística em R — classificacao-chamados

Script R **autossuficiente** que refaz toda a estatística comparativa das IAs a partir de
um arquivo de dados pronto, com gráficos, tabelas e saídas estruturadas.

## Arquivos desta pasta

| Arquivo | O que é |
|---|---|
| `analise_estatistica.R` | O script (bem comentado, usa `=` para atribuição). |
| `dados_modelos.txt` | Base **pronta**, separada por TAB: uma linha por chamado com `linha`, `categoria_historica` e, por modelo, `pred_<modelo>`, `conf_<modelo>`, `acerto_<modelo>` (0/1). 13.825 chamados × 7 IAs. Sem texto de chamado. |
| `saidas/` | Criada ao rodar: PNGs dos gráficos e CSVs das tabelas. |

## O que baixar

Baixe os **dois** arquivos da pasta `analise_R/` do repositório e coloque-os na **mesma
pasta**:

1. `analise_estatistica.R`
2. `dados_modelos.txt`

## Como rodar

- **RStudio:** abra `analise_estatistica.R`, faça *Session → Set Working Directory → To
  Source File Location* (assim `getwd()` aponta para a pasta dos dados) e rode (*Source*).
- **Terminal:** entre na pasta e execute:
  ```bash
  Rscript analise_estatistica.R
  ```

O script lê `dados_modelos.txt` via `getwd()` + `read.delim`, instala os pacotes que
faltarem (`ggplot2`, `knitr`, `irr`) e grava os resultados em `analise_R/saidas/`.

## O que ele calcula

- Acurácia (concordância vs histórico) por modelo + **IC95 por bootstrap**;
- **Cochran's Q** (as k IAs têm a mesma taxa de acerto?);
- **McNemar par a par + Holm-Bonferroni** (controle do erro familiar);
- **Kappa de Cohen** (IA × histórico) e **Kappa de Fleiss** (entre as IAs);
- **Friedman + diferença crítica de Nemenyi** (blocos = janelas de 1.000 chamados);
- **Shapiro-Wilk** (apenas diagnóstico da não-normalidade);
- **Spearman** (confiança × acerto) e **Macro-F1** por modelo.

## Saídas geradas em `saidas/`

- `01_acuracia_ic95.png`, `02_macro_f1.png`, `03_acuracia_por_janela.png`, `04_mcnemar_holm.png`;
- `tab_acuracia.csv`, `tab_mcnemar_holm.csv`, `tab_kappa_cohen.csv`,
  `tab_spearman_macrof1.csv`, `tab_normalidade.csv`.

## Observação metodológica

Enquanto a validação humana não for ampla, **"acerto" = IA × categoria histórica**
(concordância preliminar, não verdade validada). A normalidade **não** é o eixo central —
serve apenas como diagnóstico que justifica a abordagem não paramétrica. A verdade
definitiva depende das conferências humanas (colunas M/N/P da planilha).

> Para regenerar `dados_modelos.txt` a partir dos JSON publicados
> (`docs/dados/registros_<modelo>.json`), veja o gerador no histórico de commits; o arquivo
> já vem versionado aqui para rodar direto.
