# Guia técnico — validação não supervisionada

> Este arquivo funciona como adendo ao `docs/GUIA_TECNICO.md`.  
> Status: proposta técnica registrada em 2026-06-08.  
> Não altera scripts existentes, workflows, planilha ou dashboard.

## 1. Finalidade da etapa

A etapa de validação não supervisionada deve funcionar como uma camada intermediária entre a classificação automática e a validação humana.

Ela não responde definitivamente se a IA acertou. Ela responde se o chamado, a categoria histórica, a predição da IA e o consenso entre modelos são semanticamente coerentes entre si.

Uso correto:

```text
classificação automática -> análise não supervisionada -> priorização de revisão humana -> conferência M/N -> métricas validadas
```

Uso incorreto:

```text
clusterização -> declarar acerto final da IA
```

## 2. Onde ela entra no fluxo atual

Fluxo atual resumido:

1. Etapa 1 classifica chamados e grava `G:J`.
2. Coluna `K` compara IA x categoria histórica.
3. Multimodelo materializa predições por IA em `CLASSIF__<modelo>`.
4. Estatística atual mede concordância contra histórico.
5. Validação humana será registrada nas colunas `M` e `N`.

A validação não supervisionada entra depois da materialização multimodelo e antes da revisão humana em massa:

```text
CLASSIF__<modelo> + CHAMADOS_ESQUELETO_REDUZIDO
        ↓
validacao_nao_supervisionada.py
        ↓
VALIDACAO_NAO_SUPERVISIONADA + docs/dados/validacao_nao_supervisionada.json
        ↓
priorização da conferência humana M/N
```

## 3. Script proposto

Nome sugerido:

```bash
src/validacao_nao_supervisionada.py
```

Execução inicial, somente leitura:

```bash
python src/validacao_nao_supervisionada.py
```

Execução com escrita controlada:

```bash
python src/validacao_nao_supervisionada.py --aplicar
```

Parâmetros futuros recomendados:

```bash
python src/validacao_nao_supervisionada.py --saida-json docs/dados/validacao_nao_supervisionada.json
python src/validacao_nao_supervisionada.py --min-consenso 6
python src/validacao_nao_supervisionada.py --percentil-outlier 95
python src/validacao_nao_supervisionada.py --aplicar
```

## 4. Entradas do script

### 4.1 Aba principal

Aba:

```text
CHAMADOS_ESQUELETO_REDUZIDO
```

Campos usados:

```text
A  ID Chamado
B  TÍTULO
C  CATEGORIA COMPLETA
D  DESCRIÇÃO GLPI
E  TÍTULO O.S.M.
F  DESCRIÇÃO O.S.M.
G  Classificação IA
H  Avaliação (%)
I  Executor
J  Criticidade Atribuída por IA
K  Comparação
M  CONFERÊNCIA GLPI
N  CONFERÊNCIA IA
O  Classificação IA - 2
P  CONFERÊNCIA IA - 2
```

Campos textuais que formam o corpus:

```text
B + D + E + F
```

Rótulo histórico usado apenas como agrupamento de referência:

```text
C = CATEGORIA COMPLETA
```

Predição IA da etapa 1:

```text
G = Classificação IA
```

### 4.2 Abas multimodelo

Abas esperadas:

```text
CLASSIF__naive_bayes
CLASSIF__regressao_logistica
CLASSIF__linear_svc
CLASSIF__sgd
CLASSIF__extra_trees
CLASSIF__random_forest
CLASSIF__lstm
```

Essas abas permitem calcular consenso intermodelos por linha.

## 5. Processamento interno

### 5.1 Montagem do texto

Para cada chamado elegível:

```python
texto = " ".join([
    titulo,
    descricao_glpi,
    titulo_osm,
    descricao_osm,
])
```

Regras:

- converter `None` para string vazia;
- remover excesso de espaços;
- não publicar o texto em JSON público;
- usar texto apenas para cálculo vetorial local.

### 5.2 Vetorização

Implementação leve recomendada:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import make_pipeline

vectorizer = TfidfVectorizer(
    strip_accents="unicode",
    lowercase=True,
    ngram_range=(1, 2),
    min_df=2,
    max_features=30000,
)

X_tfidf = vectorizer.fit_transform(textos)
svd = TruncatedSVD(n_components=100, random_state=42)
normalizer = Normalizer(copy=False)
X = make_pipeline(svd, normalizer).fit_transform(X_tfidf)
```

Justificativa:

- TF-IDF mantém explicabilidade;
- SVD reduz ruído e dimensionalidade;
- normalização melhora comparação por cosseno;
- usa dependências já disponíveis em `requirements-leves.txt`.

### 5.3 Métricas globais

Usar as categorias históricas como grupos de referência:

```python
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

silhouette = silhouette_score(X, categorias_historicas, metric="cosine")
davies = davies_bouldin_score(X, categorias_historicas)
calinski = calinski_harabasz_score(X, categorias_historicas)
```

Interpretação:

- `silhouette` maior indica melhor separação média;
- `davies_bouldin` menor indica menor sobreposição;
- `calinski_harabasz` maior indica melhor separação relativa.

Essas métricas avaliam a qualidade estrutural da taxonomia histórica, não o acerto do modelo.

### 5.4 Centróide por categoria

Para cada categoria histórica:

1. filtrar os chamados daquela categoria;
2. calcular o centróide vetorial;
3. medir distância de cada chamado ao centróide;
4. marcar outliers por percentil.

Exemplo conceitual:

```python
centroide_categoria = X[idx_categoria].mean(axis=0)
distancia = 1 - cosine_similarity(X_linha, centroide_categoria)
```

Campos derivados:

```text
distancia_categoria_historica
percentil_distancia_categoria
score_outlier
```

### 5.5 Categoria semanticamente mais próxima

Para cada chamado:

1. calcular distância do chamado ao centróide de cada categoria;
2. identificar a categoria mais próxima;
3. comparar com a categoria histórica;
4. calcular margem entre categoria histórica e categoria alternativa.

Campos derivados:

```text
categoria_semantica_mais_proxima
distancia_categoria_mais_proxima
margem_semantica
```

Interpretação:

```text
categoria_semantica_mais_proxima != categoria_historica
margem_semantica alta
```

indica possível inconsistência da classificação histórica.

### 5.6 Consenso intermodelos

Para cada linha comum nas abas `CLASSIF__<modelo>`:

1. coletar as categorias previstas pelos modelos;
2. contar votos por categoria;
3. identificar categoria majoritária;
4. calcular quantidade de modelos concordantes;
5. calcular entropia dos votos;
6. verificar se a maioria diverge da categoria histórica.

Campos derivados:

```text
categoria_ia_majoritaria
qtd_modelos_concordantes
n_categorias_sugeridas
entropia_votos
maioria_diverge_glpi
```

Interpretação operacional:

```text
qtd_modelos_concordantes >= 6 e maioria_diverge_glpi = TRUE
```

significa prioridade alta de revisão humana.

## 6. Regra de priorização

### 6.1 Prioridade alta

Marcar `prioridade_revisao = Alta` quando houver combinação forte de evidências:

```text
maioria_diverge_glpi = TRUE
qtd_modelos_concordantes >= 6
categoria_semantica_mais_proxima != categoria_historica
score_outlier >= percentil 95 da categoria
```

Motivo sugerido:

```text
Consenso forte das IAs contra GLPI + outlier semântico na categoria histórica.
```

### 6.2 Prioridade média

Marcar `prioridade_revisao = Média` quando:

```text
maioria_diverge_glpi = TRUE
qtd_modelos_concordantes entre 4 e 5
ou
categoria_semantica_mais_proxima != categoria_historica com margem moderada
```

Motivo sugerido:

```text
Divergência parcial entre IA e GLPI com indício semântico de categoria alternativa.
```

### 6.3 Prioridade baixa

Marcar `prioridade_revisao = Baixa` quando:

```text
maioria_diverge_glpi = FALSE
qtd_modelos_concordantes >= 6
score_outlier baixo
categoria_semantica_mais_proxima = categoria_historica
```

Motivo sugerido:

```text
Convergência entre GLPI, modelos e estrutura semântica.
```

### 6.4 Caso ambíguo

Marcar como `Ambíguo` quando:

```text
n_categorias_sugeridas alto
entropia_votos alta
qtd_modelos_concordantes baixo
```

Motivo sugerido:

```text
Baixa estabilidade intermodelos; possível sobreposição taxonômica ou descrição insuficiente.
```

## 7. Saídas técnicas

### 7.1 JSON público agregado

Arquivo:

```text
docs/dados/validacao_nao_supervisionada.json
```

Conteúdo permitido:

```text
métricas globais
métricas por categoria
contagens por prioridade
percentuais de consenso
ranking de categorias frágeis
ranking de categorias sobrepostas
```

Conteúdo proibido:

```text
ID Chamado
título do chamado
descrição GLPI
descrição O.S.M.
observação livre do avaliador
qualquer texto real do chamado
```

### 7.2 Aba privada

Aba:

```text
VALIDACAO_NAO_SUPERVISIONADA
```

Colunas:

```text
linha
id_chamado
categoria_historica
categoria_ia_majoritaria
qtd_modelos_concordantes
n_categorias_sugeridas
entropia_votos
distancia_categoria_historica
categoria_semantica_mais_proxima
distancia_categoria_mais_proxima
margem_semantica
score_outlier
prioridade_revisao
motivo_prioridade
```

Essa aba serve para ordenar a revisão humana. Ela não deve ser publicada integralmente.

## 8. Relação com as colunas M e N

A validação não supervisionada apenas prioriza.

A decisão final continua sendo humana:

```text
M = CONFERÊNCIA GLPI
N = CONFERÊNCIA IA
```

Exemplo de fluxo por linha:

```text
1. Script marca prioridade Alta.
2. Avaliador abre o chamado na planilha.
3. Avaliador verifica se o GLPI está correto e preenche M.
4. Avaliador verifica se a IA está correta e preenche N.
5. Estatística final recalcula acerto validado.
```

## 9. Integração com `analise_estatistica.py`

A etapa pode gerar métricas que depois serão consumidas por `src/analise_estatistica.py`, por exemplo:

```text
acerto_validado_por_prioridade
percentual_erro_glpi_em_prioridade_alta
percentual_ia_corrige_glpi_em_prioridade_alta
calibracao_por_prioridade_revisao
```

Isso permitirá verificar empiricamente se a validação não supervisionada realmente seleciona casos mais problemáticos.

## 10. Integração com dashboard

A aba futura do dashboard deve exibir apenas agregados:

1. total de chamados analisados;
2. distribuição por prioridade;
3. categorias com maior percentual de outliers;
4. categorias mais sobrepostas;
5. percentual de consenso 7/7, 6/7, 5/7;
6. aviso metodológico fixo.

Aviso recomendado:

```text
A validação não supervisionada mede coerência semântica, sobreposição e consenso entre modelos. Ela não substitui a validação humana registrada nas colunas M e N.
```

## 11. Workflow futuro

Nome sugerido:

```text
.github/workflows/validacao_nao_supervisionada.yml
```

Comportamento recomendado:

```text
workflow_dispatch
input aplicar: false por padrão
input publicar_json: true por padrão
input escrever_aba_privada: false por padrão
```

Regra de segurança:

```text
se aplicar=false -> não escreve na planilha
se escrever_aba_privada=false -> não cria/atualiza VALIDACAO_NAO_SUPERVISIONADA
sempre sanitizar JSON público
```

## 12. Dependências

Primeira versão deve usar apenas dependências leves:

```text
numpy
scikit-learn
```

Etapa pesada opcional:

```text
sentence-transformers
```

A etapa pesada deve ser separada do fluxo leve para não aumentar o tempo dos workflows principais.

## 13. Critérios de aceite da implementação futura

A implementação só deve ser considerada pronta quando:

1. rodar localmente sem alterar a planilha por padrão;
2. gerar JSON agregado sem texto sensível;
3. gerar ranking de categorias frágeis;
4. gerar ranking de chamados priorizados apenas na aba privada;
5. não substituir validação humana;
6. registrar no dashboard que os resultados são complementares;
7. permitir comparação futura com M/N preenchidos;
8. passar por `python -m py_compile`.

Comando de validação mínimo:

```bash
python -m py_compile src/validacao_nao_supervisionada.py
```

## 14. Leitura metodológica para artigo

No artigo, a etapa deve ser descrita como:

```text
Análise não supervisionada de coerência semântica e priorização de auditoria humana.
```

Não usar como:

```text
Validação automática definitiva do acerto da IA.
```

A redação técnica recomendada é:

> A análise não supervisionada foi utilizada para identificar padrões latentes, sobreposição semântica entre categorias e chamados atípicos em relação à categoria histórica. Os resultados orientaram a priorização da validação humana, sem substituir a conferência manual utilizada como verdade de referência.
