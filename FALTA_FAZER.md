# FALTA FAZER — classificacao-chamados

> Documento único de **pendências/próximos passos**. Substitui o handoff
> `CLAUDE_CONTINUACAO_2026-06-05.md` (removido). O panorama histórico continua em
> `CONTEXTO.md`; aqui fica só o **que ainda falta**, priorizado.
>
> Atualizado: 2026-06-05 (America/Bahia, UTC-03:00).

## Estado atual (resumo)
- Dashboard publicado mostra **Etapa 1 (LSTM single-model)**: ~8.100 classificados,
  ~5.725 pendentes, 49 categorias, `validados=0`, `ece_historico≈0.0537`.
- **Multimodelo**: scripts e abas já existem (`classificacao_multimodelo.py`,
  `reclassificacao_multimodelo.py`, `preparar_abas_multimodelo.py`, workflows
  `multimodelo_*.yml`, abas `CLASSIF__*`/`RECLASS__*`/`MULTIMODELO_*`), mas a
  **classificação multimodelo ainda não foi executada** (as abas estão vazias).
- Comparação multi-modelo: 35 linhas publicadas (5 recortes de 200 × 7 modelos).
  Lineares TF-IDF > LSTM até aqui (concordância vs histórico).

> ⚠️ Todas as métricas atuais são **concordância contra a categoria histórica (C)**,
> **não** acerto validado por humano. `validados=0`.

---

## P0 — Corrigir o DASHBOARD (prioridade do usuário)
O painel não está refletindo o que o experimento já produz. Antes de processar mais
dados, fazer o painel mostrar a verdade.

> ✅ **Status 2026-06-05**: P0.1–P0.7 implementados e publicados (commit `e8df9b2`;
> dashboard run `27025224132` OK). `comparacao_categoria.json` (819) e
> `multimodelo_*` já populados. **Resta**: P0.3-extra (UI de comparação por
> categoria/modelo consumindo `comparacao_categoria.json`, ainda sem tabela no painel).

### P0.1 Filtros (UX e correção)
- [ ] Indicar **claramente** quando um filtro está ativo (chips/lista dos ativos + contador).
- [ ] Botão **Limpar** mais evidente.
- [ ] Corrigir o dropdown que **cobre abas/gráficos**; fechar após seleção (ou melhorar layout).
- [ ] Conferir que `aplicarFiltros()` é chamado a cada checkbox.
- [ ] Conferir que `REG` carrega de `docs/dados/registros.json` e que os campos existem:
      `g` grupo, `f` faixa, `e` executor, `k` concorda/diverge, `v` validação humana.
      Se algum vier vazio, corrigir em `src/exportar_dashboard.py`.
- [ ] Verificar que os filtros **recalculam**: cards superiores, aviso verde, contador
      à direita, gráfico de faixa de confiança, tabelas de `Categorias`, resumo de `Metricas`.
- [ ] Deixar **explícito na interface** quais gráficos **NÃO** são filtráveis por decisão
      (Evolução da concordância por turno, Confiança média por turno, Reclassificação) —
      hoje parece bug. Pôr um rótulo/aviso no topo desses gráficos.

### P0.2 Aba `Modelos` está enganosa
- [ ] Hoje o gráfico usa só a **última execução por modelo** (`const ult={}; rows.forEach(r=>{ult[r.modelo]=r;})`),
      escondendo os 5 recortes. Trocar por:
  - [ ] barras de **média** de acurácia e F1-macro por modelo;
  - [ ] **ranking** dos modelos por média + destaque do melhor;
  - [ ] **evolução por lote** (linha/agrupado);
  - [ ] **tabela com todos os recortes**.

### P0.3 Exportar mais JSONs (`src/exportar_dashboard.py`)
- [ ] Publicar (exportar `[]` se a aba não existir/estiver vazia):
  - [ ] `comparacao_categoria.json`  (de `COMPARACAO_CATEGORIA`)
  - [ ] `comparacao_previsoes.json`  (de `COMPARACAO_PREVISOES`)
  - [ ] `multimodelo_turnos.json`    (de `MULTIMODELO_TURNOS`)
  - [ ] `multimodelo_metricas.json`  (de `MULTIMODELO_METRICAS`)
  - [ ] `multimodelo_reclass_turnos.json` (de `MULTIMODELO_RECLASS_TURNOS`)

### P0.4 Nova aba `Multimodelo` no painel
- [ ] Progresso por modelo (feitos/pendentes), concordância por modelo materializado,
      e dados de reclassificação multimodelo quando existirem.

### P0.5 Aba `Metricas`
- [ ] Separar visualmente: métricas **vs histórico** × **validadas** × **calibração**
      × **pendentes** × **meta 95%**.
- [ ] Aviso grande quando `validados=0` (métricas preliminares, não validadas).

### P0.6 Aba `Reclassificacao`
- [ ] Estado vazio com mensagem objetiva: "Etapa 2 ainda não executada após o reset"
      / "Validação humana não iniciada" / "Próximo passo técnico: dry-run ou aplicação controlada".

### P0.7 Deixar a META 95% honesta
- [ ] Mostrar status claro por faixa: "aprovado **contra histórico**",
      "**não** validado humanamente", "ainda **não** liberado para produção".

---

## P1 — Rodar a MATERIALIZAÇÃO multimodelo (as 7 IAs completas)
> ✅ **6 leves materializados** (run `27026217228`): 13.825 cada, 0 pendentes,
> out-of-fold `kfold_5`. Concordância vs histórico: linear_svc 80,3% > extra_trees
> 78,5% > sgd 77,5% > random_forest 76,8% > regressao_logistica 76,6% > naive_bayes
> 70,1% (922 turnos/modelo). **Falta: o LSTM** (`modelos=pesados`, workflow separado,
> baixa frequência) e a **reclassificação multimodelo** (`multimodelo_reclassificacao.yml`).
- [ ] (Decidido) **Pausar o cron `*/15` da Etapa 1** (`etapa1_turnos.yml`) para o
      multimodelo virar a fonte de verdade e evitar escrita concorrente.
- [ ] Rodar `multimodelo_classificacao.yml` com `aplicar=true`, **6 leves primeiro**
      (`modelos=leves`), progressivo/lote dinâmico, até zerar pendentes.
- [ ] Conferir `CLASSIF__<modelo>` preenchendo + `MULTIMODELO_TURNOS`/`_METRICAS`.
- [ ] Depois, LSTM (`modelos=pesados`) em execução de baixa frequência.
- [ ] Em seguida `multimodelo_reclassificacao.yml` (Etapa 2 por modelo).
- [ ] Validar que a predição é **out-of-fold** (sem vazamento) — a IA não treina na linha que rotula.

---

## P2 — Robustez dos WORKFLOWS (falha de instalação)
Run manual `27001950857` da Etapa 1 falhou no `pip` baixando `tensorflow==2.17.0`
(`IncompleteRead`, exit 2) — não foi erro de lógica.
- [ ] `actions/setup-python` com `cache: pip` + `cache-dependency-path: requirements.txt`.
- [ ] Instalar com retry/timeout: `python -m pip install --retries 5 --timeout 120 -r requirements.txt`.
- [ ] Separar **workflow leve** (baseline/lineares, sem TF) do **workflow LSTM** (com TF),
      para que o download grande não derrube execuções leves.

---

## P3 — CALIBRAÇÃO rumo ao objetivo dos ≥95%
Hoje só se **mede** o ECE vs histórico; falta **calibrar** de fato.
- [ ] Avaliar ajuste de calibrador (Platt/isotônico, ex.: `CalibratedClassifierCV`)
      por modelo, gerando confiança calibrada (não só softmax).
- [ ] Calibração **por modelo** (JSON por IA) + rótulo de decisão por faixa.
- [ ] Confirmar que a faixa ≥95% mantém acerto ~≥95% (primeiro vs histórico; definitivo
      só após validação humana).

---

## P4 — VALIDAÇÃO HUMANA + métricas finais (PAUSADA por decisão do usuário)
A aba `VALIDACAO_HUMANA` já tem **1.654 casos** preparados (divergentes). Não iniciar
agora — só após fortalecer modelo/scripts/painel.
- [ ] Revisar manualmente os 1.654 casos (`categoria_validada`, `decisao`,
      `justificativa`, `avaliador`, `data_validacao`, `usar_para_treino`).
- [ ] Após validação: matriz de confusão, métricas por categoria, **confiança calibrada
      validada** por faixa, indicadores finais, e **re-treino** com a base validada (etapas 41-42).

---

## P5 — ANÁLISES ESTATÍSTICAS (novo, solicitado 2026-06-05)
Além das métricas já existentes (concordância, F1, calibração/ECE, ganho líquido),
adicionar análise estatística formal (detalhe em `ESTADO_DO_ROTEIRO.md`, Extensão B):
- [ ] **Correlação** (Pearson/Spearman): confiança×acerto, volume×concordância, texto×acerto.
- [ ] **Normalidade**: Shapiro–Wilk / D'Agostino / KS + QQ-plots (decide paramétrico vs não).
- [ ] **Análise de resíduos**: resíduos de concordância por turno/categoria; homocedasticidade,
      autocorrelação (Durbin–Watson), tendência.
- [ ] **Significância entre as 7 IAs**: McNemar par a par; Cochran's Q / Friedman + Nemenyi;
      IC 95% por bootstrap de acurácia/F1.
- [ ] **Concordância**: Kappa de Cohen (IA×histórico; IA×validação) e Fleiss entre as IAs.
- [ ] Saída: tabelas/figuras ABNT + JSON agregado (sem texto) para o painel.

## P6 — Comparar TODAS as IAs juntas (incl. LSTM)
- [x] 6 leves materializados.
- [ ] ⏳ **LSTM** (7ª IA) em materialização — quando concluir, a aba Multimodelo terá as 7.
- [ ] Conferir as 7 lado a lado (Multimodelo + Modelos) e rodar P5 sobre elas.

> 📄 **Mapa completo do estado das 50 etapas do roteiro**: ver `ESTADO_DO_ROTEIRO.md`.

## Housekeeping
- [ ] Remover Apps Script legado (`apps_script/Code.gs`) quando não for mais útil.
- [ ] **Atualizar `CONTEXTO.md`** a cada correção (o quê, workflow/run ID, estado dos JSONs, pendências).
- [x] Substituir o handoff `CLAUDE_CONTINUACAO_2026-06-05.md` por este documento (handoff removido).

---

## Comandos úteis
```bash
# estado
gh run list --repo adinailson88/classificacao-chamados --limit 20
python -m py_compile src/exportar_dashboard.py src/classificacao_multimodelo.py src/reclassificacao_multimodelo.py

# painel local
python -m http.server 8000 -d docs        # abre docs/index.html

# multimodelo (após pausar o cron da Etapa 1)
gh workflow run multimodelo_classificacao.yml   --repo adinailson88/classificacao-chamados -f modelos=leves -f aplicar=true
gh workflow run multimodelo_reclassificacao.yml --repo adinailson88/classificacao-chamados -f modelos=leves -f aplicar=true

# dashboard
gh workflow run dashboard.yml --repo adinailson88/classificacao-chamados
```

> Ordem recomendada: **P0 (painel) → P1 (materializar multimodelo) → P2 (workflows)
> → P3 (calibração) → P4 (validação humana)**. O foco imediato é o painel refletir
> corretamente o que já existe, não processar mais registros.
