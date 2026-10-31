# Inferência estatística da rodada canônica

> Relatório sanitizado e somente leitura. Não contém títulos, descrições ou IDs de chamados.

**Gerado em:** 30/10/2026 01:35  
**Hash do corpus:** `67812136fc0868862717280daeb85590d48d56779f4f5e4e28651920be6a57cb`

## Protocolo

- Bootstrap: reamostragem de grupos textuais com reposicao, bootstrap de conglomerados; a linha nao e a unidade de reamostragem porque registros do mesmo grupo nao sao independentes.
- Repetições: 1000; semente: 42; nível de significância 0.05.
- Ordem dos testes: Cochran Q global primeiro; McNemar pareado apenas se o Q rejeitar, com Holm sobre os 21 pares.
- Observações: 14357 registros em 10596 grupos textuais, 39 categorias e 7 modelos pareados.

## Intervalos de confiança por bootstrap de grupo

Três grandezas distintas, e a coluna de cada uma é declarada: a estimativa **observada** na amostra inteira, a **média** das mil reamostragens e o **intervalo** de percentil. O artigo reporta a estimativa observada ao lado do intervalo; a média das reamostragens não deve substituí-la.

| Modelo | Acurácia obs. | Média boot. | IC 95% | Macro-F1 obs. | Média boot. | IC 95% |
|---|---:|---:|---|---:|---:|---|
| linear_svc | 0.8241 | 0.824 | [0.8116; 0.8366] | 0.6859 | 0.684 | [0.6693; 0.6989] |
| sgd | 0.8096 | 0.8095 | [0.7975; 0.8222] | 0.6659 | 0.6648 | [0.6513; 0.678] |
| regressao_logistica | 0.8079 | 0.8079 | [0.7957; 0.8214] | 0.6743 | 0.6735 | [0.6599; 0.6863] |
| extra_trees | 0.8054 | 0.8053 | [0.7925; 0.8189] | 0.6411 | 0.6396 | [0.6255; 0.6542] |
| random_forest | 0.7923 | 0.7921 | [0.7793; 0.8065] | 0.6189 | 0.6173 | [0.6036; 0.6312] |
| naive_bayes | 0.7222 | 0.722 | [0.7041; 0.7403] | 0.3618 | 0.3612 | [0.3543; 0.3675] |
| lstm | 0.7067 | 0.7064 | [0.6889; 0.7253] | 0.5173 | 0.5158 | [0.5034; 0.5287] |

## Contagem de grupos textuais

| Contagem | Valor |
|---|---:|
| Grupos congelados no recorte avaliado (unidade do bootstrap) | 10596 |
| Grupos no mapa de partições, recalculados sobre o texto vivo | 10596 |
| Registros cujo grupo vivo diverge do congelado | 0 |

as contagens divergem quando o texto de um chamado e editado na aba viva depois do congelamento; a contagem congelada e a reproduzivel e e a usada como unidade de reamostragem

## Consenso entre os modelos

- Unanimidade (os sete modelos preveem a mesma categoria): 8653 registros, 0.6027.
- Desacordo estrutural (tres ou mais categorias distintas entre as sete predicoes): 2486 registros, 0.1732.
- Entropia média normalizada dos votos: 0.1449.

## Confiança bruta contra acerto

| Modelo | n | Spearman | Ponto-bisserial |
|---|---:|---:|---:|
| extra_trees | 14357 | 0.5143 | 0.5359 |
| linear_svc | 14357 | 0.4831 | 0.4546 |
| lstm | 14357 | 0.6393 | 0.6741 |
| naive_bayes | 14357 | 0.6059 | 0.6308 |
| random_forest | 14357 | 0.5354 | 0.5506 |
| regressao_logistica | 14357 | 0.4583 | 0.4619 |
| sgd | 14357 | 0.4743 | 0.4686 |

Spearman entre 0.4583 e 0.6393; ponto-bisserial entre 0.4546 e 0.6741. Todos positivos e significativos: sim.

## Pressupostos

Shapiro-Wilk sobre subamostra de 5000 observações, semente 42. Fator de Inflação de Variância entre as confianças dos modelos, limiar convencional de 10.0.

| Modelo | Shapiro W | Rejeita normalidade | Variância | VIF |
|---|---:|---|---:|---:|
| extra_trees | 0.8589 | sim | 0.07321 | 22.442 |
| linear_svc | 0.9315 | sim | 0.00557 | 5.116 |
| lstm | 0.8164 | sim | 0.09435 | 3.103 |
| naive_bayes | 0.8314 | sim | 0.07843 | 3.68 |
| random_forest | 0.8621 | sim | 0.07955 | 26.474 |
| regressao_logistica | 0.8733 | sim | 0.10481 | 22.991 |
| sgd | 0.9074 | sim | 0.08843 | 28.344 |

Normalidade rejeitada em 7 dos 7 modelos. Levene = 4186.61, p = 0: homogeneidade de variância rejeitada. VIF acima do limiar em 4 modelos: extra_trees, random_forest, regressao_logistica, sgd.

## Teste global

Cochran Q = 2875.1751, 6 graus de liberdade, p = 0. Hipótese nula: todos os modelos tem a mesma taxa de acerto. Rejeitada, o que autoriza as comparações pareadas.

## McNemar pareado, com correção de Holm

| Par | Discordantes | Só o 1º acerta | Só o 2º acerta | p bruto | p ajustado | Significativo |
|---|---:|---:|---:|---:|---:|---|
| extra_trees × linear_svc | 1323 | 527 | 796 | 1.73e-13 | 0 | sim |
| extra_trees × lstm | 2597 | 2007 | 590 | 6.39e-170 | 0 | sim |
| extra_trees × naive_bayes | 2234 | 1714 | 520 | 1.44e-140 | 0 | sim |
| extra_trees × random_forest | 594 | 391 | 203 | 1.68e-14 | 0 | sim |
| linear_svc × lstm | 2396 | 2041 | 355 | 1.12e-259 | 0 | sim |
| linear_svc × naive_bayes | 2613 | 2038 | 575 | 6.57e-180 | 0 | sim |
| linear_svc × random_forest | 1507 | 982 | 525 | 7.36e-32 | 0 | sim |
| linear_svc × regressao_logistica | 897 | 565 | 332 | 9.46e-15 | 0 | sim |
| linear_svc × sgd | 851 | 530 | 321 | 1e-12 | 0 | sim |
| lstm × random_forest | 2609 | 690 | 1919 | 1.02e-127 | 0 | sim |
| lstm × regressao_logistica | 2295 | 421 | 1874 | 8.66e-202 | 0 | sim |
| lstm × sgd | 2303 | 413 | 1890 | 9.96e-208 | 0 | sim |
| naive_bayes × random_forest | 2260 | 627 | 1633 | 3.39e-99 | 0 | sim |
| naive_bayes × regressao_logistica | 2842 | 806 | 2036 | 1.35e-117 | 0 | sim |
| naive_bayes × sgd | 2684 | 715 | 1969 | 3.14e-129 | 0 | sim |
| random_forest × regressao_logistica | 1602 | 689 | 913 | 2.53e-08 | 0 | sim |
| random_forest × sgd | 1504 | 628 | 876 | 1.9e-10 | 0 | sim |
| lstm × naive_bayes | 3135 | 1456 | 1679 | 7.34e-05 | 0.000294 | sim |
| extra_trees × sgd | 1394 | 667 | 727 | 0.114 | 0.342 | não |
| regressao_logistica × sgd | 294 | 135 | 159 | 0.18 | 0.36 | não |
| extra_trees × regressao_logistica | 1504 | 734 | 770 | 0.367 | 0.367 | não |

Dos 21 pares, 18 são significativos após Holm e 3 não são. Pares não significativos indicam modelos empatados dentro do poder do teste, e o artigo não deve apresentá-los como ordenados.

## Proveniência

- Predições: `docs/dados/retreino_canonico_predicoes.csv`.
- Grupos textuais: `docs/dados/grupos_textuais_mapa.csv`, Passo 2.
- Script: `src/inferencia_canonica.py`.
- Nenhum modelo foi retreinado e nenhuma escrita foi feita na planilha.
