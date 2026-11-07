# Inferência pareada no nível do grupo textual

> Relatório sanitizado e somente leitura. Não contém títulos, descrições ou IDs de chamados.

**Gerado em:** 30/10/2026 01:36  
**Hash do corpus:** `67812136fc0868862717280daeb85590d48d56779f4f5e4e28651920be6a57cb`

## 1. Auditoria da unidade estatística

- Unidade anterior: linha (chamado individual).
- Unidade adotada: grupo de texto normalizado idêntico.
- 14357 linhas em 10596 grupos; tamanho médio 1.3549, maior grupo 190.
- 4152 linhas (28.92%) pertencem a grupos com mais de um membro e não são independentes entre si.

| Modelo | Acurácia | EP por linha | EP por grupo | Efeito de desenho |
|---|---:|---:|---:|---:|
| Extra Trees | 0.8054 | 0.003304 | 0.006401 | 3.754 |
| LinearSVC | 0.8241 | 0.003177 | 0.005932 | 3.485 |
| LSTM | 0.7067 | 0.0038 | 0.009198 | 5.86 |
| Naive Bayes | 0.7222 | 0.003738 | 0.008784 | 5.522 |
| Random Forest | 0.7923 | 0.003386 | 0.006699 | 3.915 |
| Regressão Logística | 0.8079 | 0.003288 | 0.006361 | 3.743 |
| SGD | 0.8096 | 0.003277 | 0.006311 | 3.709 |

Efeito de desenho entre 3.485 e 5.86. efeito de desenho acima de 1 indica que a suposição de independência entre linhas estreita artificialmente a precisão; os valores de p do McNemar por linha herdam esse estreitamento.

## 2. Teste global

Q de Cochran = 2875.1751, 6 graus de liberdade. Referência empírica com 2000 permutações do rótulo de modelo por grupo textual: p ≤ 0.0005. O p da distribuição qui-quadrado por linha seria 0.

a estatística Q permanece adequada por ser pareada e binária, mas a distribuição qui-quadrado tabelada pressupõe independência entre registros, violada aqui; a referência passa a ser empírica, obtida por permutação do rótulo de modelo dentro de cada grupo textual.

## 3. Comparações pareadas

Cada par é orientado pelo modelo de maior acurácia, de modo que a diferença relatada é sempre positiva. O valor de p vem da permutação por troca de sinal da diferença por grupo e é corrigido por Holm sobre os 21 pares. A última coluna traz o p do McNemar por linha, corrigido pela mesma família, apenas para dimensionar o estreitamento que a suposição de independência produzia.

| Par | Δ acurácia (p.p.) | IC95% da diferença | Grupos a favor do 1º | a favor do 2º | Empates | d pareado | p ajustado (grupo) | p ajustado (linha) |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| LinearSVC × LSTM | 11.74 | [+0.1084; +0.1269] | 2035 | 355 | 8206 | 0.3539 | 0.0021 | 0 |
| SGD × LSTM | 10.29 | [+0.0944; +0.1116] | 1884 | 409 | 8303 | 0.3108 | 0.0021 | 0 |
| LinearSVC × Naive Bayes | 10.19 | [+0.0927; +0.1111] | 2028 | 575 | 7993 | 0.2874 | 0.0021 | 0 |
| Regressão Logística × LSTM | 10.12 | [+0.0926; +0.1098] | 1868 | 417 | 8311 | 0.3059 | 0.0021 | 0 |
| Extra Trees × LSTM | 9.87 | [+0.0901; +0.1077] | 2003 | 585 | 8008 | 0.2792 | 0.0021 | 0 |
| SGD × Naive Bayes | 8.73 | [+0.0788; +0.0963] | 1963 | 715 | 7918 | 0.2413 | 0.0021 | 0 |
| Regressão Logística × Naive Bayes | 8.57 | [+0.0769; +0.0946] | 2030 | 806 | 7760 | 0.2294 | 0.0021 | 0 |
| Random Forest × LSTM | 8.56 | [+0.0774; +0.0940] | 1915 | 685 | 7996 | 0.2392 | 0.0021 | 0 |
| Extra Trees × Naive Bayes | 8.32 | [+0.0752; +0.0912] | 1710 | 519 | 8367 | 0.2529 | 0.0021 | 0 |
| Random Forest × Naive Bayes | 7.01 | [+0.0626; +0.0773] | 1629 | 626 | 8341 | 0.2099 | 0.0021 | 0 |
| LinearSVC × Random Forest | 3.18 | [+0.0264; +0.0374] | 974 | 524 | 9098 | 0.1141 | 0.0021 | 0 |
| LinearSVC × Extra Trees | 1.87 | [+0.0137; +0.0238] | 788 | 526 | 9282 | 0.0713 | 0.0021 | 0 |
| SGD × Random Forest | 1.73 | [+0.0123; +0.0229] | 872 | 627 | 9097 | 0.0621 | 0.0021 | 0 |
| LinearSVC × Regressão Logística | 1.62 | [+0.0120; +0.0207] | 561 | 332 | 9703 | 0.075 | 0.0021 | 0 |
| Regressão Logística × Random Forest | 1.56 | [+0.0104; +0.0212] | 909 | 688 | 8999 | 0.0543 | 0.0021 | 0 |
| Naive Bayes × LSTM | 1.55 | [+0.0080; +0.0231] | 1678 | 1451 | 7467 | 0.0386 | 0.0021 | 0.000294 |
| LinearSVC × SGD | 1.46 | [+0.0104; +0.0188] | 526 | 321 | 9749 | 0.069 | 0.0021 | 0 |
| Extra Trees × Random Forest | 1.31 | [+0.0099; +0.0166] | 391 | 203 | 10002 | 0.0751 | 0.0021 | 0 |
| SGD × Extra Trees | 0.42 | [-0.0006; +0.0090] | 723 | 666 | 9207 | 0.0156 | 0.352 | 0.342 |
| SGD × Regressão Logística | 0.17 | [-0.0006; +0.0040] | 159 | 135 | 10302 | 0.0136 | 0.366 | 0.36 |
| Regressão Logística × Extra Trees | 0.25 | [-0.0026; +0.0076] | 766 | 733 | 9097 | 0.009 | 0.37 | 0.367 |

Pares cujo veredito muda ao corrigir a unidade: 0. a inferência por linha e a por grupo concordam no veredito de cada par nesta rodada; o que muda é a magnitude do valor de p, que por linha é anticonservador.

## 4. Proveniência

- Predições: `docs/dados/retreino_canonico_predicoes.csv`.
- Grupos textuais: `docs/dados/grupos_textuais_mapa.csv`, Passo 2.
- Script: `src/inferencia_agrupada.py`.
- Permutações pareadas: 10000; globais: 2000; reamostragens: 2000; semente: 42.
- Nenhum modelo foi retreinado e nenhuma escrita foi feita na planilha.
