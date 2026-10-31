# Inferência pareada no nível do grupo textual

> Relatório sanitizado e somente leitura. Não contém títulos, descrições ou IDs de chamados.

**Gerado em:** 30/10/2026 12:21  
**Hash do corpus:** `67812136fc0868862717280daeb85590d48d56779f4f5e4e28651920be6a57cb`

## 1. Auditoria da unidade estatística

- Unidade anterior: linha (chamado individual).
- Unidade adotada: grupo de texto normalizado idêntico.
- 14357 linhas em 10596 grupos; tamanho médio 1.3549, maior grupo 190.
- 4152 linhas (28.92%) pertencem a grupos com mais de um membro e não são independentes entre si.

| Modelo | Acurácia | EP por linha | EP por grupo | Efeito de desenho |
|---|---:|---:|---:|---:|
| embedding_e5 | 0.7554 | 0.003588 | 0.00807 | 5.06 |
| Extra Trees | 0.8054 | 0.003304 | 0.006521 | 3.895 |
| LinearSVC | 0.8241 | 0.003177 | 0.006146 | 3.742 |
| LSTM | 0.7067 | 0.0038 | 0.009458 | 6.195 |
| Naive Bayes | 0.7222 | 0.003738 | 0.009042 | 5.852 |
| Random Forest | 0.7923 | 0.003386 | 0.006845 | 4.088 |
| Regressão Logística | 0.8079 | 0.003288 | 0.006488 | 3.893 |
| SGD | 0.8096 | 0.003277 | 0.006471 | 3.9 |
| tfidf_caracteres | 0.828 | 0.003149 | 0.006028 | 3.664 |
| tfidf_embedding | 0.8307 | 0.00313 | 0.005955 | 3.62 |

Efeito de desenho entre 3.62 e 6.195. efeito de desenho acima de 1 indica que a suposição de independência entre linhas estreita artificialmente a precisão; os valores de p do McNemar por linha herdam esse estreitamento.

## 2. Teste global

Q de Cochran = 4188.0599, 9 graus de liberdade. Referência empírica com 1000 permutações do rótulo de modelo por grupo textual: p ≤ 0.000999. O p da distribuição qui-quadrado por linha seria 0.

a estatística Q permanece adequada por ser pareada e binária, mas a distribuição qui-quadrado tabelada pressupõe independência entre registros, violada aqui; a referência passa a ser empírica, obtida por permutação do rótulo de modelo dentro de cada grupo textual.

## 3. Comparações pareadas

Cada par é orientado pelo modelo de maior acurácia, de modo que a diferença relatada é sempre positiva. O valor de p vem da permutação por troca de sinal da diferença por grupo e é corrigido por Holm sobre os 21 pares. A última coluna traz o p do McNemar por linha, corrigido pela mesma família, apenas para dimensionar o estreitamento que a suposição de independência produzia.

| Par | Δ acurácia (p.p.) | IC95% da diferença | Grupos a favor do 1º | a favor do 2º | Empates | d pareado | p ajustado (grupo) | p ajustado (linha) |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| tfidf_embedding × LSTM | 12.4 | [+0.1140; +0.1340] | 2139 | 364 | 8093 | 0.3669 | 0.009 | 0 |
| tfidf_caracteres × LSTM | 12.13 | [+0.1118; +0.1314] | 2113 | 376 | 8107 | 0.3592 | 0.009 | 0 |
| LinearSVC × LSTM | 11.74 | [+0.1078; +0.1265] | 2035 | 355 | 8206 | 0.3539 | 0.009 | 0 |
| tfidf_embedding × Naive Bayes | 10.84 | [+0.0992; +0.1178] | 2077 | 529 | 7990 | 0.3076 | 0.009 | 0 |
| tfidf_caracteres × Naive Bayes | 10.58 | [+0.0966; +0.1153] | 2061 | 551 | 7984 | 0.299 | 0.009 | 0 |
| SGD × LSTM | 10.29 | [+0.0940; +0.1119] | 1884 | 409 | 8303 | 0.3108 | 0.009 | 0 |
| LinearSVC × Naive Bayes | 10.19 | [+0.0930; +0.1112] | 2028 | 575 | 7993 | 0.2874 | 0.009 | 0 |
| Regressão Logística × LSTM | 10.12 | [+0.0924; +0.1100] | 1868 | 417 | 8311 | 0.3059 | 0.009 | 0 |
| Extra Trees × LSTM | 9.87 | [+0.0897; +0.1077] | 2003 | 585 | 8008 | 0.2792 | 0.009 | 0 |
| SGD × Naive Bayes | 8.73 | [+0.0784; +0.0955] | 1963 | 715 | 7918 | 0.2413 | 0.009 | 0 |
| Regressão Logística × Naive Bayes | 8.57 | [+0.0767; +0.0943] | 2030 | 806 | 7760 | 0.2294 | 0.009 | 0 |
| Random Forest × LSTM | 8.56 | [+0.0771; +0.0943] | 1915 | 685 | 7996 | 0.2392 | 0.009 | 0 |
| Extra Trees × Naive Bayes | 8.32 | [+0.0753; +0.0910] | 1710 | 519 | 8367 | 0.2529 | 0.009 | 0 |
| tfidf_embedding × embedding_e5 | 7.53 | [+0.0681; +0.0828] | 1466 | 393 | 8737 | 0.2484 | 0.009 | 0 |
| tfidf_caracteres × embedding_e5 | 7.26 | [+0.0655; +0.0802] | 1456 | 421 | 8719 | 0.238 | 0.009 | 0 |
| Random Forest × Naive Bayes | 7.01 | [+0.0626; +0.0779] | 1629 | 626 | 8341 | 0.2099 | 0.009 | 0 |
| LinearSVC × embedding_e5 | 6.87 | [+0.0619; +0.0764] | 1396 | 418 | 8782 | 0.2283 | 0.009 | 0 |
| SGD × embedding_e5 | 5.42 | [+0.0484; +0.0603] | 1121 | 348 | 9127 | 0.1999 | 0.009 | 0 |
| Regressão Logística × embedding_e5 | 5.25 | [+0.0467; +0.0586] | 1106 | 357 | 9133 | 0.1939 | 0.009 | 0 |
| Extra Trees × embedding_e5 | 5.0 | [+0.0431; +0.0571] | 1489 | 773 | 8334 | 0.1475 | 0.009 | 0 |
| embedding_e5 × LSTM | 4.87 | [+0.0416; +0.0557] | 1425 | 723 | 8448 | 0.1464 | 0.009 | 0 |
| tfidf_embedding × Random Forest | 3.84 | [+0.0326; +0.0444] | 1055 | 510 | 9031 | 0.1352 | 0.009 | 0 |
| Random Forest × embedding_e5 | 3.69 | [+0.0302; +0.0436] | 1407 | 879 | 8310 | 0.1078 | 0.009 | 0 |
| tfidf_caracteres × Random Forest | 3.57 | [+0.0302; +0.0418] | 1026 | 519 | 9051 | 0.1265 | 0.009 | 0 |
| embedding_e5 × Naive Bayes | 3.32 | [+0.0246; +0.0414] | 1884 | 1409 | 7303 | 0.0805 | 0.009 | 0 |
| LinearSVC × Random Forest | 3.18 | [+0.0262; +0.0374] | 974 | 524 | 9098 | 0.1141 | 0.009 | 0 |
| tfidf_embedding × Extra Trees | 2.53 | [+0.0200; +0.0309] | 870 | 513 | 9213 | 0.0942 | 0.009 | 0 |
| tfidf_embedding × Regressão Logística | 2.28 | [+0.0183; +0.0278] | 704 | 380 | 9512 | 0.0957 | 0.009 | 0 |
| tfidf_caracteres × Extra Trees | 2.26 | [+0.0173; +0.0281] | 842 | 523 | 9231 | 0.0848 | 0.009 | 0 |
| tfidf_embedding × SGD | 2.11 | [+0.0165; +0.0260] | 663 | 363 | 9570 | 0.0911 | 0.009 | 0 |
| tfidf_caracteres × Regressão Logística | 2.01 | [+0.0158; +0.0251] | 670 | 384 | 9542 | 0.0857 | 0.009 | 0 |
| LinearSVC × Extra Trees | 1.87 | [+0.0137; +0.0238] | 788 | 526 | 9282 | 0.0713 | 0.009 | 0 |
| tfidf_caracteres × SGD | 1.85 | [+0.0141; +0.0233] | 629 | 367 | 9600 | 0.0807 | 0.009 | 0 |
| SGD × Random Forest | 1.73 | [+0.0118; +0.0229] | 872 | 627 | 9097 | 0.0621 | 0.009 | 0 |
| LinearSVC × Regressão Logística | 1.62 | [+0.0123; +0.0206] | 561 | 332 | 9703 | 0.075 | 0.009 | 0 |
| Regressão Logística × Random Forest | 1.56 | [+0.0099; +0.0214] | 909 | 688 | 8999 | 0.0543 | 0.009 | 0 |
| Naive Bayes × LSTM | 1.55 | [+0.0082; +0.0235] | 1678 | 1451 | 7467 | 0.0386 | 0.009 | 0.000441 |
| LinearSVC × SGD | 1.46 | [+0.0107; +0.0188] | 526 | 321 | 9749 | 0.069 | 0.009 | 0 |
| Extra Trees × Random Forest | 1.31 | [+0.0098; +0.0164] | 391 | 203 | 10002 | 0.0751 | 0.009 | 0 |
| tfidf_embedding × LinearSVC | 0.65 | [+0.0035; +0.0094] | 278 | 183 | 10135 | 0.0424 | 0.009 | 0.000106 |
| tfidf_embedding × tfidf_caracteres | 0.26 | [+0.0011; +0.0043] | 97 | 59 | 10440 | 0.0296 | 0.017 | 0.0153 |
| tfidf_caracteres × LinearSVC | 0.39 | [+0.0011; +0.0065] | 245 | 188 | 10163 | 0.0261 | 0.0368 | 0.0332 |
| SGD × Extra Trees | 0.42 | [-0.0012; +0.0093] | 723 | 666 | 9207 | 0.0156 | 0.344 | 0.342 |
| SGD × Regressão Logística | 0.17 | [-0.0007; +0.0040] | 159 | 135 | 10302 | 0.0136 | 0.354 | 0.36 |
| Regressão Logística × Extra Trees | 0.25 | [-0.0031; +0.0078] | 766 | 733 | 9097 | 0.009 | 0.374 | 0.367 |

Pares cujo veredito muda ao corrigir a unidade: 0. a inferência por linha e a por grupo concordam no veredito de cada par nesta rodada; o que muda é a magnitude do valor de p, que por linha é anticonservador.

## 4. Proveniência

- Predições: `docs/dados/retreino_canonico_predicoes.csv`.
- Grupos textuais: `docs/dados/grupos_textuais_mapa.csv`, Passo 2.
- Script: `src/inferencia_agrupada.py`.
- Permutações pareadas: 5000; globais: 1000; reamostragens: 1000; semente: 42.
- Nenhum modelo foi retreinado e nenhuma escrita foi feita na planilha.
