# Recortes por tipo de manutenção e por volume

> Relatório sanitizado e somente leitura. Não contém títulos, descrições ou IDs de chamados.

**Gerado em:** 30/10/2026 19:48  
**Hash do corpus:** `67812136fc0868862717280daeb85590d48d56779f4f5e4e28651920be6a57cb`

## Critérios

- Tipo: familia da categoria, conforme src/tipo_manutencao.py; Preventiva, Corretiva e Nao manutencao.
- ABC: percentual acumulado de volume, corte A em 0.8 e B em 0.95; a categoria que cruza o corte pertence a classe que ela fecha.
- F1 de recorte: o F1 de um recorte usa apenas os rotulos daquele recorte, mas todos os pares, para que falsos positivos vindos de fora continuem contando.

## Tarefa de tipo

Verdade e predição projetadas para os três tipos. Responde se o modelo distingue a natureza do serviço, independentemente de acertar a folha.

| Modelo | Acurácia | Macro-F1 | Preventiva | Corretiva | Não manutenção |
|---|---:|---:|---:|---:|---:|
| extra_trees | 0.9533 | 0.8402 | 0.9775 | 0.9626 | 0.5805 |
| random_forest | 0.9517 | 0.8344 | 0.9766 | 0.9614 | 0.5651 |
| tfidf_embedding | 0.9482 | 0.836 | 0.9758 | 0.958 | 0.5741 |
| tfidf_caracteres | 0.9481 | 0.8374 | 0.9756 | 0.9579 | 0.5786 |
| linear_svc | 0.9459 | 0.833 | 0.9748 | 0.9563 | 0.568 |
| sgd | 0.9396 | 0.8335 | 0.971 | 0.9507 | 0.5788 |
| regressao_logistica | 0.9391 | 0.8325 | 0.9716 | 0.9503 | 0.5757 |
| naive_bayes | 0.9381 | 0.8006 | 0.9627 | 0.9511 | 0.4881 |
| embedding_e5 | 0.9027 | 0.7901 | 0.9432 | 0.9181 | 0.5091 |
| lstm | 0.8859 | 0.7286 | 0.9511 | 0.9057 | 0.3292 |

## Recorte por tipo, na tarefa de categoria

| Modelo | Tipo | Categorias | Chamados | Acurácia | Macro-F1 |
|---|---|---:|---:|---:|---:|
| embedding_e5 | Preventiva | 12 | 4954 | 0.9596 | 0.7612 |
| embedding_e5 | Corretiva | 21 | 8787 | 0.654 | 0.5865 |
| embedding_e5 | Não manutenção | 6 | 616 | 0.5584 | 0.3397 |
| extra_trees | Preventiva | 12 | 4954 | 0.9635 | 0.7797 |
| extra_trees | Corretiva | 21 | 8787 | 0.7386 | 0.635 |
| extra_trees | Não manutenção | 6 | 616 | 0.487 | 0.3848 |
| linear_svc | Preventiva | 12 | 4954 | 0.9705 | 0.8054 |
| linear_svc | Corretiva | 21 | 8787 | 0.7625 | 0.7 |
| linear_svc | Não manutenção | 6 | 616 | 0.526 | 0.3974 |
| lstm | Preventiva | 12 | 4954 | 0.957 | 0.7386 |
| lstm | Corretiva | 21 | 8787 | 0.5892 | 0.4681 |
| lstm | Não manutenção | 6 | 616 | 0.3701 | 0.2469 |
| naive_bayes | Preventiva | 12 | 4954 | 0.9475 | 0.678 |
| naive_bayes | Corretiva | 21 | 8787 | 0.6177 | 0.2175 |
| naive_bayes | Não manutenção | 6 | 616 | 0.401 | 0.2345 |
| random_forest | Preventiva | 12 | 4954 | 0.9616 | 0.7627 |
| random_forest | Corretiva | 21 | 8787 | 0.7196 | 0.6122 |
| random_forest | Não manutenção | 6 | 616 | 0.4675 | 0.3546 |
| regressao_logistica | Preventiva | 12 | 4954 | 0.9645 | 0.7992 |
| regressao_logistica | Corretiva | 21 | 8787 | 0.7356 | 0.6851 |
| regressao_logistica | Não manutenção | 6 | 616 | 0.5795 | 0.3869 |
| sgd | Preventiva | 12 | 4954 | 0.9651 | 0.7855 |
| sgd | Corretiva | 21 | 8787 | 0.7387 | 0.6768 |
| sgd | Não manutenção | 6 | 616 | 0.5698 | 0.3884 |
| tfidf_caracteres | Preventiva | 12 | 4954 | 0.9709 | 0.8081 |
| tfidf_caracteres | Corretiva | 21 | 8787 | 0.7684 | 0.7081 |
| tfidf_caracteres | Não manutenção | 6 | 616 | 0.5292 | 0.4162 |
| tfidf_embedding | Preventiva | 12 | 4954 | 0.9707 | 0.8073 |
| tfidf_embedding | Corretiva | 21 | 8787 | 0.7731 | 0.7056 |
| tfidf_embedding | Não manutenção | 6 | 616 | 0.526 | 0.4095 |

## Curva ABC global

| Modelo | Classe | Categorias | Chamados | % do volume | Acurácia | Macro-F1 |
|---|---|---:|---:|---:|---:|---:|
| embedding_e5 | A | 12 | 11753 | 0.8186 | 0.7643 | 0.7514 |
| embedding_e5 | B | 11 | 1955 | 0.1362 | 0.7238 | 0.6894 |
| embedding_e5 | C | 16 | 649 | 0.0452 | 0.6888 | 0.4305 |
| extra_trees | A | 12 | 11753 | 0.8186 | 0.8428 | 0.7943 |
| extra_trees | B | 11 | 1955 | 0.1362 | 0.6987 | 0.7412 |
| extra_trees | C | 16 | 649 | 0.0452 | 0.4499 | 0.4573 |
| linear_svc | A | 12 | 11753 | 0.8186 | 0.8482 | 0.8163 |
| linear_svc | B | 11 | 1955 | 0.1362 | 0.7591 | 0.7505 |
| linear_svc | C | 16 | 649 | 0.0452 | 0.584 | 0.5437 |
| lstm | A | 12 | 11753 | 0.8186 | 0.7355 | 0.7243 |
| lstm | B | 11 | 1955 | 0.1362 | 0.6159 | 0.5741 |
| lstm | C | 16 | 649 | 0.0452 | 0.4592 | 0.323 |
| naive_bayes | A | 12 | 11753 | 0.8186 | 0.8106 | 0.6903 |
| naive_bayes | B | 11 | 1955 | 0.1362 | 0.4046 | 0.3965 |
| naive_bayes | C | 16 | 649 | 0.0452 | 0.0786 | 0.0915 |
| random_forest | A | 12 | 11753 | 0.8186 | 0.8297 | 0.7785 |
| random_forest | B | 11 | 1955 | 0.1362 | 0.691 | 0.7334 |
| random_forest | C | 16 | 649 | 0.0452 | 0.4191 | 0.4203 |
| regressao_logistica | A | 12 | 11753 | 0.8186 | 0.8239 | 0.8045 |
| regressao_logistica | B | 11 | 1955 | 0.1362 | 0.7729 | 0.748 |
| regressao_logistica | C | 16 | 649 | 0.0452 | 0.624 | 0.526 |
| sgd | A | 12 | 11753 | 0.8186 | 0.8275 | 0.8055 |
| sgd | B | 11 | 1955 | 0.1362 | 0.7652 | 0.7502 |
| sgd | C | 16 | 649 | 0.0452 | 0.6179 | 0.5032 |
| tfidf_caracteres | A | 12 | 11753 | 0.8186 | 0.8544 | 0.8209 |
| tfidf_caracteres | B | 11 | 1955 | 0.1362 | 0.7514 | 0.7536 |
| tfidf_caracteres | C | 16 | 649 | 0.0452 | 0.5809 | 0.5577 |
| tfidf_embedding | A | 12 | 11753 | 0.8186 | 0.8579 | 0.8243 |
| tfidf_embedding | B | 11 | 1955 | 0.1362 | 0.7535 | 0.7562 |
| tfidf_embedding | C | 16 | 649 | 0.0452 | 0.5701 | 0.5471 |

## Proveniência

- Origem: `docs/dados/retreino_canonico_predicoes.csv`.
- Script: `src/recortes_canonicos.py`.
- Nenhum modelo foi retreinado e nenhuma escrita foi feita na planilha.
