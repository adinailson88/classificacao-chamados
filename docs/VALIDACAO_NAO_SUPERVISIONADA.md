# Validação não supervisionada — proposta metodológica

> Status: proposta registrada em 2026-06-08.  
> Escopo: documentação e desenho metodológico. Nenhum script, workflow ou dado sensível foi alterado.

## 1. Objetivo

Adicionar ao experimento `classificacao-chamados` uma camada complementar de **validação não supervisionada** para avaliar a coerência semântica das categorias históricas, priorizar revisão humana e identificar chamados potencialmente mal classificados no GLPI.

Esta etapa **não substitui** a validação humana. A função correta é servir como auditoria técnica preliminar, triagem de casos críticos e apoio à análise científica da taxonomia de manutenção predial.

Formulação metodológica recomendada:

> A análise não supervisionada será utilizada para avaliar a estrutura latente dos chamados, a coesão semântica das categorias históricas, a separação entre agrupamentos e a consistência intermodelos. Os resultados serão empregados como critério de priorização da validação humana, sem substituir a verdade de referência produzida pela conferência manual.

## 2. Justificativa

O repositório já possui uma base forte para essa extensão:

- chamados classificados em base experimental própria;
- 7 modelos locais materializados;
- predição out-of-fold (`kfold_5`), reduzindo vazamento direto;
- métricas estatísticas não paramétricas já implementadas;
- Kappa de Fleiss entre IAs já calculado;
- validação humana planejada em conferência dupla: GLPI correto/errado e IA correta/errada.

O limite metodológico atual é que a maior parte das métricas ainda mede concordância contra a categoria histórica, e não acerto validado por humano. A validação não supervisionada ajuda a apontar onde o histórico pode ser frágil, inconsistente ou semanticamente deslocado.

## 3. O que a etapa deve responder

A etapa deve responder, sem usar rótulo humano como entrada obrigatória:

1. As categorias históricas formam grupos semanticamente coerentes?
2. Há categorias muito sobrepostas entre si?
3. Existem chamados distantes do padrão semântico da própria categoria histórica?
4. Há chamados em que a maioria das IAs concorda entre si, mas diverge do GLPI?
5. Há chamados em que todos os modelos discordam entre si, indicando ambiguidade taxonômica?
6. Quais chamados devem ser priorizados na validação humana?
7. Quais categorias precisam de revisão taxonômica, fusão, subdivisão ou melhor definição operacional?

## 4. Técnicas recomendadas

### 4.1 Representação textual leve

Implementação inicial recomendada:

- `TfidfVectorizer` com unigramas e bigramas;
- redução de dimensionalidade com `TruncatedSVD`;
- normalização vetorial;
- uso apenas de dependências leves já existentes no repositório (`numpy` e `scikit-learn`).

Campos textuais sugeridos:

```text
TÍTULO + DESCRIÇÃO GLPI + TÍTULO O.S.M. + DESCRIÇÃO O.S.M.
```

### 4.2 Métricas globais de estrutura

Métricas recomendadas:

- `silhouette_score`: avalia separação média entre categorias históricas;
- `davies_bouldin_score`: avalia sobreposição/compacidade entre agrupamentos;
- `calinski_harabasz_score`: avalia separação entre grupos em relação à dispersão interna.

Essas métricas devem ser interpretadas como coerência estrutural da taxonomia, não como acurácia de classificação.

### 4.3 Coesão por categoria

Para cada categoria histórica:

- calcular centróide vetorial da categoria;
- calcular distância de cada chamado ao centróide da própria categoria;
- identificar percentis extremos de distância;
- calcular categorias semanticamente mais próximas;
- apontar categorias com alta dispersão interna.

Categorias com baixa coesão são candidatas a revisão de nomenclatura, subdivisão ou depuração de chamados inconsistentes.

### 4.4 Outliers semânticos

Identificar chamados que destoam semanticamente da categoria histórica por:

- distância ao centróide da categoria;
- `IsolationForest`;
- `LocalOutlierFactor`;
- combinação por percentil, quando se quiser manter a explicabilidade simples.

O critério por percentil é preferível na primeira versão, por ser mais transparente e mais fácil de justificar no artigo.

### 4.5 Consenso intermodelos

Usar as abas `CLASSIF__<modelo>` já materializadas para calcular, por linha:

- categoria majoritária entre as IAs;
- quantidade de modelos que votaram na categoria majoritária;
- número de categorias diferentes sugeridas;
- entropia dos votos;
- concordância ou divergência da maioria contra o GLPI;
- presença de consenso forte contra o histórico.

Regra interpretativa recomendada:

```text
6 ou 7 modelos concordam entre si e divergem do GLPI -> prioridade alta de revisão.
5 modelos concordam entre si e divergem do GLPI -> prioridade média/alta.
Modelos muito divididos -> caso ambíguo ou taxonomia pouco separável.
Modelos concordam com GLPI e o chamado é semanticamente próximo da categoria -> baixa prioridade.
```

### 4.6 Tópicos por categoria

Usar `NMF` ou análise dos maiores pesos do TF-IDF para extrair termos dominantes por categoria.

Objetivo:

- explicar semanticamente cada categoria;
- detectar categorias genéricas demais;
- identificar termos que aparecem em múltiplas categorias;
- apoiar revisão da taxonomia de manutenção predial.

## 5. Script sugerido

Nome sugerido:

```bash
src/validacao_nao_supervisionada.py
```

Responsabilidades:

1. Ler a planilha principal ou artefatos já exportados, sem alterar dados originais.
2. Montar o corpus textual dos chamados.
3. Vetorizar os textos.
4. Calcular métricas globais de separação e coesão.
5. Calcular métricas por categoria histórica.
6. Detectar outliers semânticos.
7. Integrar consenso entre os modelos já materializados.
8. Gerar JSON público apenas agregado.
9. Gerar aba privada com chamados priorizados para revisão humana.
10. Nunca publicar texto real de chamado no GitHub Pages.

## 6. Saídas sugeridas

### 6.1 JSON público agregado

Arquivo sugerido:

```text
docs/dados/validacao_nao_supervisionada.json
```

Conteúdo permitido:

- métricas globais;
- resumo por categoria;
- estatísticas agregadas de consenso;
- contagem de outliers por categoria;
- nenhuma descrição textual de chamado;
- nenhum ID sensível;
- nenhuma observação livre.

Exemplo de estrutura:

```json
{
  "gerado_em": "2026-06-08 00:00",
  "n_chamados": 13825,
  "n_categorias": 54,
  "representacao": "tfidf_svd_100",
  "metricas_globais": {
    "silhouette_medio": 0.0,
    "davies_bouldin": 0.0,
    "calinski_harabasz": 0.0
  },
  "categorias": [
    {
      "categoria": "Elétrica",
      "n": 0,
      "distancia_media_centroide": 0.0,
      "percentual_outliers": 0.0,
      "categoria_mais_sobreposta": "Climatização"
    }
  ],
  "consenso_modelos": {
    "percentual_consenso_7_de_7": 0.0,
    "percentual_consenso_6_ou_mais": 0.0,
    "percentual_alta_divergencia": 0.0
  }
}
```

### 6.2 Aba privada para revisão

Aba sugerida:

```text
VALIDACAO_NAO_SUPERVISIONADA
```

Colunas sugeridas:

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

Essa aba pode conter identificadores internos porque permanece na planilha privada. Não deve ser exportada integralmente para `docs/dados`.

## 7. Critério de prioridade para validação humana

### Prioridade alta

Chamado deve ser priorizado quando ocorrerem simultaneamente:

- IA majoritária diverge do GLPI;
- 6 ou 7 modelos concordam na mesma categoria;
- categoria majoritária da IA é semanticamente mais próxima do texto do que a categoria histórica;
- chamado é outlier dentro da categoria histórica;
- confiança média dos modelos é alta.

### Prioridade média

Chamado deve ser marcado como prioridade média quando:

- há divergência IA x GLPI;
- existe consenso parcial entre os modelos;
- a distância semântica favorece outra categoria, mas com margem pequena;
- a categoria histórica é uma categoria conhecida por sobreposição.

### Prioridade baixa

Chamado pode ficar em baixa prioridade quando:

- IA e GLPI concordam;
- o chamado está próximo do centróide da categoria histórica;
- os modelos têm consenso forte;
- não há sinal de outlier semântico.

## 8. Integração com a conferência dupla

A etapa deve alimentar a validação humana, não substituí-la.

A interpretação final continua vinculada às colunas de conferência:

```text
M = CONFERÊNCIA GLPI
N = CONFERÊNCIA IA
```

A validação não supervisionada deve apenas indicar quais linhas merecem atenção antes, por exemplo:

```text
prioridade_revisao = Alta
motivo_prioridade = Consenso 7/7 contra GLPI + outlier na categoria histórica
```

Depois que `M` e `N` forem preenchidas, as métricas finais devem ser recalculadas contra a verdade validada.

## 9. Integração futura com dashboard

O painel pode receber uma nova aba chamada `Validação não supervisionada`, exibindo apenas dados agregados:

- cards globais de coesão e separação;
- ranking de categorias mais frágeis;
- ranking de categorias mais sobrepostas;
- percentual de consenso forte entre modelos;
- quantidade de chamados priorizados por nível;
- aviso metodológico explícito: "análise não supervisionada não substitui validação humana".

## 10. Workflow futuro sugerido

Nome sugerido:

```text
validacao_nao_supervisionada.yml
```

Execução recomendada:

- manual inicialmente;
- dry-run por padrão;
- sem escrita na planilha quando `aplicar=false`;
- geração de JSON agregado para `docs/dados` apenas quando não houver dados sensíveis;
- escrita da aba privada `VALIDACAO_NAO_SUPERVISIONADA` apenas com `aplicar=true`.

## 11. Riscos e controles

Riscos:

- interpretar clusterização como verdade de referência;
- publicar texto real de chamados no GitHub Pages;
- reforçar erro histórico se a categoria original estiver contaminada;
- usar consenso entre modelos como substituto indevido da revisão humana.

Controles:

- declarar sempre que a análise é complementar;
- separar saída pública agregada e saída privada por linha;
- manter validação humana como critério final;
- registrar a metodologia no guia técnico e no artigo;
- comparar resultados não supervisionados com a conferência dupla depois que houver amostra validada.

## 12. Próximo passo técnico

Implementar primeiro somente o script local em modo leitura:

```bash
python src/validacao_nao_supervisionada.py
```

Depois testar a geração do JSON agregado e, somente após inspeção, permitir:

```bash
python src/validacao_nao_supervisionada.py --aplicar
```

A implementação deve seguir o padrão operacional do repositório: ler contexto antes, aplicar menor alteração necessária, preservar dados sensíveis e não declarar validação humana antes de ela existir.

## 13. Atualizacao implementada em 2026-06-11

O script `src/validacao_nao_supervisionada.py` passou a calcular `score_prioridade_revisao`, combinando outlier semantico, margem semantica, consenso dos modelos contra o historico, entropia dos votos e distancia a categoria historica.

A prioridade `Alta` deixou de ser ampla por regra booleana e passou a ser seletiva: usa corte no percentil 85 dos scores observados, com expectativa operacional de top 15%, salvo empates e criterios fortes. As faixas `Media` e `Baixa` foram mantidas, e as colunas antigas nao foram removidas.

Se nao houver dados reais disponiveis no ambiente de execucao, a logica fica implementada, mas a distribuicao real na planilha deve ser tratada como: Informação insuficiente para verificar.
