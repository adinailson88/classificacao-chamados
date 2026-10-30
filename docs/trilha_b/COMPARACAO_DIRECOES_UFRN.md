# Os mesmos modelos em quatro condições

Acurácia (ou concordância) por modelo. Em cada coluna, a taxonomia e a base mudam; os scripts de treino são os mesmos.

| Modelo | Nossa para nossa (OOF, 41 categorias) | Nossa para UFRN (concordância com `divisao`) | Nossa para UFRN, sem Viário (4 divisões) | UFRN para UFRN (teste 2025+, 6 divisões) | UFRN para nossa (6 divisões, correspondência proposta) |
|---|---:|---:|---:|---:|---:|
| tfidf_embedding | 0,8307 | 0,6737 | 0,8174 | n/d | n/d |
| tfidf_caracteres | 0,8280 | 0,6780 | 0,8263 | 0,9274 | 0,8274 |
| linear_svc | 0,8241 | 0,6706 | 0,8207 | 0,9198 | 0,8363 |
| sgd | 0,8096 | 0,6655 | 0,7986 | 0,8959 | 0,8327 |
| regressao_logistica | 0,8079 | 0,6586 | 0,7983 | 0,8955 | 0,8226 |
| extra_trees | 0,8054 | 0,6119 | 0,7603 | 0,9002 | 0,8300 |
| random_forest | 0,7923 | 0,5984 | 0,7398 | 0,8846 | 0,8077 |
| embedding_e5 | 0,7554 | n/d | n/d | n/d | n/d |
| naive_bayes | 0,7222 | 0,6404 | 0,7992 | 0,8964 | 0,7287 |
| lstm | 0,7067 | n/d | n/d | n/d | n/d |

## Correlação de postos entre condições (Spearman)

| Condições | Modelos em comum | Spearman |
|---|---:|---:|
| Nossa para nossa (OOF, 41 categorias) × Nossa para UFRN (concordância com `divisao`) | 8 | 0,905 |
| Nossa para nossa (OOF, 41 categorias) × Nossa para UFRN, sem Viário (4 divisões) | 8 | 0,691 |
| Nossa para nossa (OOF, 41 categorias) × UFRN para UFRN (teste 2025+, 6 divisões) | 7 | 0,607 |
| Nossa para nossa (OOF, 41 categorias) × UFRN para nossa (6 divisões, correspondência proposta) | 7 | 0,714 |
| Nossa para UFRN (concordância com `divisao`) × Nossa para UFRN, sem Viário (4 divisões) | 8 | 0,905 |
| Nossa para UFRN (concordância com `divisao`) × UFRN para UFRN (teste 2025+, 6 divisões) | 7 | 0,679 |
| Nossa para UFRN (concordância com `divisao`) × UFRN para nossa (6 divisões, correspondência proposta) | 7 | 0,536 |
| Nossa para UFRN, sem Viário (4 divisões) × UFRN para UFRN (teste 2025+, 6 divisões) | 7 | 0,786 |
| Nossa para UFRN, sem Viário (4 divisões) × UFRN para nossa (6 divisões, correspondência proposta) | 7 | 0,286 |
| UFRN para UFRN (teste 2025+, 6 divisões) × UFRN para nossa (6 divisões, correspondência proposta) | 7 | 0,464 |
