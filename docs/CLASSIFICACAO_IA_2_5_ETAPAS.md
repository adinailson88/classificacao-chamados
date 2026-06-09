# Classificação IA - 2 em 5 etapas

Implantação inicial da revalidação robusta da classificação de chamados.

## Objetivo

Transformar a coluna `O` (`Classificacao IA - 2`) em uma revalidação robusta, auditável e separada da classificação original da IA (`G`), preservando as conferências humanas:

- `M` = conferência da categoria histórica do GLPI;
- `N` = conferência da Classificação IA original;
- `O` = Classificação IA - 2;
- `P` = conferência humana da Classificação IA - 2.

Nenhum script novo grava na coluna `O` sem flag explícita.

---

## Etapa 1 — Preparação e controle

Abas criadas ou usadas:

- `CONTROLE_CLASSIFICACAO_2`
- `CANDIDATOS_CLASSIFICACAO_2`
- `AUDITORIA_CLASSIFICACAO_2`

Finalidade:

- registrar execuções;
- listar candidatos;
- auditar decisões;
- evitar sobrescrita indevida de `G`, `M`, `N` e `P`.

---

## Etapa 2 — Validação não supervisionada

Script:

```bash
python src/validacao_nao_supervisionada.py
```

Workflow:

```text
.github/workflows/validacao_nao_supervisionada.yml
```

Aba gerada com `--aplicar`:

```text
VALIDACAO_NAO_SUPERVISIONADA
```

O script calcula:

- representação TF-IDF + SVD;
- distância do chamado ao centróide da categoria histórica;
- categoria semanticamente mais próxima;
- margem semântica;
- outlier semântico;
- consenso entre modelos já materializados nas abas `CLASSIF__<modelo>`;
- prioridade de revisão.

Essa etapa não decide categoria final. Apenas prioriza casos.

---

## Etapa 3 — Comitê multimodelo da Classificação IA - 2

Script:

```bash
python src/classificacao_ia_2_comite.py
```

Workflows:

```text
.github/workflows/classificacao_ia_2_dryrun.yml
.github/workflows/classificacao_ia_2_aplicar.yml
```

Abas geradas:

- `COMITE_CLASSIFICACAO_2`
- `CLASSIFICACAO_2_DRYRUN`
- `CANDIDATOS_CLASSIFICACAO_2`

O comitê considera:

- `linear_svc`;
- `extra_trees`;
- `sgd`;
- `random_forest`;
- `regressao_logistica`;
- `naive_bayes`;
- `lstm`;
- MiniLM robusto, quando `--usar-minilm` for acionado.

A decisão usa voto ponderado por desempenho histórico e confiança. O MiniLM entra como voto semântico adicional, não como verdade automática.

---

## Etapa 4 — Aplicação controlada na coluna O

A aplicação real exige simultaneamente:

```bash
--aplicar --gravar-coluna-o
```

O workflow de aplicação exige confirmação textual:

```text
confirmacao = APLICAR_O
```

A coluna `O` só é preenchida quando:

- existe sugestão do comitê;
- o risco não é alto;
- há consenso mínimo;
- há conferência M/N completa, salvo alteração explícita futura;
- a decisão fica registrada em auditoria.

---

## Etapa 5 — Memória validada, métricas e calibração

Script:

```bash
python src/consolidar_memoria_validada_classificacao.py
```

Workflow:

```text
.github/workflows/consolidar_validacao_classificacao_2.yml
```

Abas geradas:

- `MEMORIA_VALIDADA_CLASSIFICACAO`
- `METRICAS_CLASSIFICACAO_2`
- `CALIBRACAO_VALIDADA`

A verdade de referência é derivada assim:

1. Se `P = Correto`, a categoria validada é `O`.
2. Senão, se `N = Correto`, a categoria validada é `G`.
3. Senão, se `M = Correto`, a categoria validada é `C`.
4. Se todas forem erradas ou vazias, não há categoria validada para treino.

Essa memória alimenta o retreino/calibração futura com maior peso para casos revisados humanamente.

---

## Ordem operacional recomendada

```bash
# 1. Gerar prioridades semânticas
python src/validacao_nao_supervisionada.py --aplicar

# 2. Simular comitê, sem gravar O
python src/classificacao_ia_2_comite.py --usar-minilm --limite 200 --aplicar

# 3. Conferir abas COMITE_CLASSIFICACAO_2 e CLASSIFICACAO_2_DRYRUN

# 4. Aplicar apenas se aprovado
python src/classificacao_ia_2_comite.py --usar-minilm --limite 200 --aplicar --gravar-coluna-o

# 5. Depois da conferência P, consolidar memória e métricas
python src/consolidar_memoria_validada_classificacao.py --aplicar
```

## Observações de segurança

- A etapa 2 não grava `O`.
- A etapa 3 em dry-run não grava `O`.
- A etapa 4 só grava `O` com flag explícita.
- A etapa 5 não grava `O`.
- Textos livres dos chamados permanecem na planilha privada; não são exportados para `docs/dados`.
- Não versionar `SPREADSHEET_ID`, `GCP_SA_KEY` ou credenciais.
