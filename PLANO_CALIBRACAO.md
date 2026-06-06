# Plano de Calibração por Modelo

> Atualizado: 2026-06-06 (America/Bahia, UTC-03:00).
> Objetivo final (`OBJETIVO_FINAL_MODELO_IA.txt`): confiança **calibrada** ≥95% que
> indique, por categoria, se a categoria histórica do chamado está correta.

## Princípio (o que NÃO fazer)

**Softmax alto não é confiança calibrada.** Hoje a coluna de confiança das 7 IAs é:

- `linear_svc` / `sgd`: `decision_function` normalizada (margem), **não** probabilidade;
- `regressao_logistica`: `predict_proba` (já probabilístico, mas não necessariamente calibrado);
- `naive_bayes`: `predict_proba` notoriamente mal calibrado (tende a 0/1);
- `extra_trees` / `random_forest`: fração de votos das árvores (enviesado para o centro);
- `lstm`: softmax da última camada (tipicamente **superconfiante**).

Nenhuma dessas saídas pode ser vendida como "confiança de 95%". A calibração ajusta um
mapeamento `confiança_bruta → probabilidade_empírica de acerto` e só então a faixa ≥95%
tem significado operacional.

`src/calibracao.py` hoje **mede** calibração (ECE vs histórico, acerto por faixa) sobre o
`SNAPSHOT_ETAPA_1` — é diagnóstico, **não** ajusta calibrador. Este plano cobre o ajuste.

## Estado atual (medido, contra histórico)

- ECE vs histórico (Etapa 1/LSTM): ≈0,0399 (`docs/dados/calibracao.json`, `validados=0`).
- 7 IAs materializadas (out-of-fold `kfold_5`, 13.825 cada). Concordância vs histórico:
  linear_svc 80,26% > extra_trees 78,47% > sgd 77,51% > random_forest 76,80% >
  regressao_logistica 76,59% > naive_bayes 70,07% > lstm 67,57%.
- Correlação confiança × acerto (Spearman) positiva em todos (de 0,46 a 0,63): há sinal
  útil na confiança, mas a escala precisa ser calibrada.

## Estratégia por modelo

| Modelo | Saída atual | Calibrador proposto | Observação |
|---|---|---|---|
| `linear_svc` | `decision_function` | **`CalibratedClassifierCV` (sigmoid/Platt)** | **candidato principal**; SVC linear não tem `predict_proba`, Platt é o caminho natural |
| `sgd` (hinge) | `decision_function` | `CalibratedClassifierCV` (sigmoid) | mesmo caso do SVC |
| `regressao_logistica` | `predict_proba` | `CalibratedClassifierCV` (sigmoid ou isotonic) | comparar; já probabilístico |
| `extra_trees` | votos | `CalibratedClassifierCV` (isotonic) | isotônica costuma vencer em árvores, exige n suficiente |
| `random_forest` | votos | `CalibratedClassifierCV` (isotonic) | idem |
| `naive_bayes` | `predict_proba` | `CalibratedClassifierCV` (isotonic) | prob. bruta péssima; calibração é essencial |
| `lstm` | softmax | **calibrador separado**: temperature scaling (ou isotônica) sobre logits | não passa por `CalibratedClassifierCV`; exige guardar logits/validação posterior |

## Metodologia (sem vazamento)

1. **Calibração out-of-fold**, espelhando a materialização (`kfold_5`): o calibrador de
   cada fold é ajustado em folds que **não** contêm a linha calibrada. `CalibratedClassifierCV`
   com `cv=5` já faz isso para os modelos sklearn.
2. **Alvo de calibração provisório = categoria histórica** (`acerto = IA == C`). Deixar
   explícito que é provisório: a calibração **definitiva** usa `categoria_validada` da
   validação humana (ainda pausada).
3. **Métricas de calibração por modelo**: ECE, MCE, Brier, e diagrama de confiabilidade
   (bins) — antes e depois do calibrador. Guardar em `docs/dados/calibracao_<modelo>.json`
   (agregado, sem texto de chamado).
4. **Faixa ≥95%**: após calibrar, reportar a fração real de acerto na faixa ≥95% calibrada.
   Só declarar "aprovado para produção" quando essa fração se sustentar **contra validação
   humana** — não contra histórico.

## LSTM (caso à parte)

- `CalibratedClassifierCV` é para estimadores sklearn; o LSTM (Keras/TF) fica de fora.
- Plano: persistir os **logits** da última camada e aplicar **temperature scaling** (1
  parâmetro T, otimizado por NLL num conjunto de calibração out-of-fold) ou isotônica sobre
  a probabilidade máxima.
- Enquanto não houver logits persistidos nem validação humana, **registrar** que o LSTM
  está sem calibrador e que sua confiança (softmax) é apenas bruta.

## Priorização

- **linear_svc** é o candidato principal atual (maior concordância e melhor Kappa vs
  histórico). Calibrar primeiro com Platt e medir ECE/Brier antes/depois.
- **Não liberar produção sem validação humana**, mesmo que a faixa ≥95% calibrada pareça boa
  contra o histórico.

## Implementação incremental sugerida

- [ ] `src/calibracao_modelos.py`: para cada modelo sklearn, treinar `CalibratedClassifierCV`
      out-of-fold sobre a mesma base/TF-IDF da materialização; exportar curva de confiabilidade
      + ECE/MCE/Brier (antes/depois) em `docs/dados/calibracao_<modelo>.json`.
- [ ] Reaproveitar `src/modelos_zoo.py` (definição dos estimadores) e o split `kfold_5`.
- [ ] LSTM: salvar logits na materialização e adicionar temperature scaling separado.
- [ ] Aba/painel: rótulo de decisão por faixa **calibrada** (não softmax cru), com aviso de
      que a calibração definitiva depende da validação humana.
- [ ] Workflow leve dedicado (sem TF para os 6 lineares/árvores; TF só no passo do LSTM),
      seguindo o padrão de robustez (`cache: pip`, `--retries 5 --timeout 120`).

> Regra de ouro: enquanto `validados=0`, toda calibração é **preliminar contra histórico**.
> A confiança calibrada só vira critério de produção após a validação humana.

## Atualizacao executada - calibracao escalar preliminar (2026-06-06)

Depois da primeira versao deste plano, foram publicadas duas camadas adicionais:

- `src/calibracao_modelos.py` / `docs/dados/calibracao_modelos.json`: diagnostico bruto por IA
  com ECE, MCE, Brier e faixas de confianca, sem texto de chamado.
- `src/calibracao_confianca.py` / `docs/dados/calibracao_ajustada_modelos.json`: calibracao
  escalar out-of-fold da pergunta `P(previsao correta | confianca_bruta)`, comparando sigmoid
  e isotonica contra o historico.

Resultado preliminar relevante: `linear_svc` continua sendo o melhor em concordancia global
contra historico (`80,26%`). Antes da calibracao, sua confianca bruta era inadequada para
decisao (`ECE=0,7101`, faixa `>=95%` vazia). Apos calibracao escalar, ficou com
`ECE=0,0019` e faixa ajustada `>=95%` com `5.125` casos e `98,36%` de acerto contra historico.

Isso **nao** libera producao. O alvo ainda e a categoria historica. A versao definitiva deve
usar `categoria_validada` depois da validacao humana.
