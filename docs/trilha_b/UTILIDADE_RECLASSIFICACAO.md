# Utilidade da reclassificação sob custos assimétricos

> Relatório sanitizado e somente leitura. Não contém títulos, descrições ou IDs de chamados.

**Gerado em:** 30/10/2026 19:48  
**Hash do corpus:** `não informado`

## 1. Função de utilidade

`U = b x corrigidos - c x prejudicados - r x revisados`, dividida por b, o que deixa duas razões adimensionais e dispensa valor monetário:

- **rho** = c / b, custo do prejuízo em unidades de benefício da correção;
- **lambda** = r / b, custo da revisão em unidades de benefício da correção.

Rho = 1 e lambda = 0 reproduzem o ganho líquido simples do artigo, que permanece o resultado principal por ser transparente.

## 2. Política A — aplicação direta

O modelo reescreve a categoria sempre que diverge do histórico. A razão de equilíbrio é o valor de rho acima do qual a utilidade vira negativa.

| Modelo | Corrigidos | Prejudicados | Ganho simples | rho de equilíbrio | U/b (rho=0.25) | U/b (rho=0.5) | U/b (rho=1) | U/b (rho=2) | U/b (rho=4) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tfidf_embedding | 448 | 2294 | -1846 | 0.1953 | -125.5 | -699.0 | -1846.0 | -4140.0 | -8728.0 |
| tfidf_caracteres | 450 | 2334 | -1884 | 0.1928 | -133.5 | -717.0 | -1884.0 | -4218.0 | -8886.0 |
| LinearSVC | 457 | 2397 | -1940 | 0.1907 | -142.2 | -741.5 | -1940.0 | -4337.0 | -9131.0 |
| SGD | 460 | 2609 | -2149 | 0.1763 | -192.2 | -844.5 | -2149.0 | -4758.0 | -9976.0 |
| Regressão Logística | 461 | 2634 | -2173 | 0.175 | -197.5 | -856.0 | -2173.0 | -4807.0 | -10075.0 |
| Extra Trees | 415 | 2624 | -2209 | 0.1582 | -241.0 | -897.0 | -2209.0 | -4833.0 | -10081.0 |
| Random Forest | 406 | 2803 | -2397 | 0.1448 | -294.8 | -995.5 | -2397.0 | -5200.0 | -10806.0 |
| embedding_e5 | 449 | 3376 | -2927 | 0.133 | -395.0 | -1239.0 | -2927.0 | -6303.0 | -13055.0 |
| Naive Bayes | 320 | 3723 | -3403 | 0.086 | -610.8 | -1541.5 | -3403.0 | -7126.0 | -14572.0 |
| LSTM | 376 | 4002 | -3626 | 0.094 | -624.5 | -1625.0 | -3626.0 | -7628.0 | -15632.0 |

Com rho = 1 a utilidade é negativa em todos os sete modelos, que é o resultado já reportado. A reclassificação direta seria somente se estragar um registro valer menos de 0.195 do que vale corrigir outro, condição que nenhuma leitura razoável de custo em manutenção predial satisfaz, já que o registro corrompido propaga para a série da categoria e para a alocação de recurso, ao passo que a correção apenas recupera o valor devido.

## 3. Política B — triagem por divergência

A divergência enfileira o chamado para revisão humana em vez de reescrever o rótulo. Não há prejudicados por construção, e o limite de equilíbrio de lambda coincide com a precisão da fila.

| Modelo | Fila | Histórico errado na fila | Precisão da fila | U/b (lam=0) | U/b (lam=0.05) | U/b (lam=0.1) | U/b (lam=0.2) |
|---|---:|---:|---:|---:|---:|---:|---:|
| tfidf_embedding | 2790 | 496 | 0.1778 | +496.0 | +356.5 | +217.0 | -62.0 |
| tfidf_caracteres | 2832 | 498 | 0.1758 | +498.0 | +356.4 | +214.8 | -68.4 |
| LinearSVC | 2906 | 509 | 0.1752 | +509.0 | +363.7 | +218.4 | -72.2 |
| SGD | 3127 | 518 | 0.1657 | +518.0 | +361.6 | +205.3 | -107.4 |
| Regressão Logística | 3150 | 516 | 0.1638 | +516.0 | +358.5 | +201.0 | -114.0 |
| Extra Trees | 3112 | 488 | 0.1568 | +488.0 | +332.4 | +176.8 | -134.4 |
| Random Forest | 3288 | 485 | 0.1475 | +485.0 | +320.6 | +156.2 | -172.6 |
| embedding_e5 | 3911 | 535 | 0.1368 | +535.0 | +339.4 | +143.9 | -247.2 |
| Naive Bayes | 4188 | 465 | 0.111 | +465.0 | +255.6 | +46.2 | -372.6 |
| LSTM | 4525 | 523 | 0.1156 | +523.0 | +296.8 | +70.5 | -382.0 |

A mesma predição que não sustenta a reescrita sustenta a priorização: a fila de divergências concentra registros com histórico errado em até 17.78%, várias vezes a taxa de alteração do rótulo na base congelada, de modo que a política b tem utilidade positiva sempre que revisar custar menos do que essa fração do benefício de corrigir.

A revisão humana devolve a referência, o que é verdadeiro por construção neste desenho; o valor é portanto um teto da política, não previsão de campo.

A taxa de alteração do rótulo histórico, 4,25%, é apurada sobre as 14.060 linhas da base congelada, ao passo que a precisão da fila é apurada sobre as 13.972 avaliadas; a diferença de 88 linhas não altera a ordem de grandeza da comparação, mas os dois denominadores não devem ser fundidos.

## 4. Proveniência

- Contagens: `docs/dados/comparacao_historica.json`, rodada canônica.
- Script: `src/utilidade_reclassificacao.py`.
- Nenhum valor monetário é atribuído; todas as razões são adimensionais.
