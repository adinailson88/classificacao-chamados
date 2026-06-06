# FALTA FAZER — classificacao-chamados

> Documento único de **pendências/próximos passos**. Substitui o handoff
> `CLAUDE_CONTINUACAO_2026-06-05.md` (removido). O panorama histórico continua em
> `CONTEXTO.md`; aqui fica só o **que ainda falta**, priorizado.
>
> Atualizado: 2026-06-06 (America/Bahia, UTC-03:00).

## Estado atual (resumo)
- **Etapa 1 (LSTM single-model)** na aba `Classificacao`: base elegível de **13.825**
  chamados, classificação progressiva em turnos de 15 concluída (0 pendentes),
  54 categorias, `validados=0`, `ece_historico≈0.0399`. Fonte do painel: `registros.json`.
- **Multimodelo materializado** — as **7 IAs completas**, 13.825 chamados por modelo,
  0 pendentes, predição **out-of-fold** (`kfold_5`). Concordância vs categoria histórica:
  `linear_svc` 80,26% > `extra_trees` 78,47% > `sgd` 77,51% > `random_forest` 76,80% >
  `regressao_logistica` 76,59% > `naive_bayes` 70,07% > `lstm` 67,57%. A comparação das
  7 IAs vive nas abas `Modelos`, `Multimodelo` e `Estatistica` (não em `Classificacao`).
- `multimodelo_registros.json` foi **removido** de propósito: multiplicava chamados por 7
  e exibia ~96.775 predições como se fossem chamados. **Não recriar.**
- Análise estatística assume **pressupostos não paramétricos** (Shapiro rejeitou
  normalidade nos 7 modelos): Spearman, Friedman/Nemenyi, Cochran Q, McNemar e bootstrap.
  Resultados são **contra o histórico**, não contra validação humana.

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

## P1 — MATERIALIZAÇÃO multimodelo (as 7 IAs completas) ✅ CONCLUÍDA
> ✅ **7 IAs materializadas** (6 leves run `27026217228` + LSTM run `27026916670`):
> 13.825 cada, 0 pendentes, out-of-fold `kfold_5`. Concordância vs histórico:
> linear_svc 80,26% > extra_trees 78,47% > sgd 77,51% > random_forest 76,80% >
> regressao_logistica 76,59% > naive_bayes 70,07% > lstm 67,57%.
- [x] Materializar os 6 modelos leves (`modelos=leves`) até zerar pendentes.
- [x] Materializar o LSTM (`modelos=pesados`) — 7ª IA concluída.
- [x] `CLASSIF__<modelo>` preenchidos + `MULTIMODELO_TURNOS`/`_METRICAS` publicados.
- [x] Predição confirmada **out-of-fold** (`kfold_5`, sem vazamento).
- [ ] **Reclassificação multimodelo** (`multimodelo_reclassificacao.yml`): só após
      Etapa 1 finalizada e dashboard/estatística atualizados — começar por **dry-run**
      (`-f aplicar=false`), sem aplicar em massa antes de medir ganho líquido.

---

## P2 — Robustez dos WORKFLOWS (falha de instalação)
Run manual `27001950857` da Etapa 1 falhou no `pip` baixando `tensorflow==2.17.0`
(`IncompleteRead`, exit 2) — não foi erro de lógica.
- [x] `etapa1_turnos.yml` já usa `cache: pip` + `cache-dependency-path: requirements.txt`
      e `pip install --retries 5 --timeout 120`.
- [ ] Aplicar o mesmo padrão (cache + retry/timeout) nos demais workflows que ainda usam
      `pip install -r requirements.txt` simples — em especial `multimodelo_reclassificacao.yml`.
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

## P5 — ANÁLISES ESTATÍSTICAS (solicitado 2026-06-05) ✅ implementado
`src/analise_estatistica.py` roda sobre as 7 IAs (13.825 linhas comuns) e gera
`docs/dados/estatistica.json`, consumido pela aba `Estatistica`. **Normalidade foi
rejeitada** (Shapiro nos 7 modelos) → a análise assume **pressupostos não paramétricos**.
Resultados são **contra o histórico**, não contra validação humana.
- [x] **Correlação** Spearman (confiança×acerto) por modelo.
- [x] **Normalidade**: Shapiro–Wilk (rejeitou nos 7 → não paramétrico).
- [x] **Análise de resíduos** de concordância por turno.
- [x] **Significância entre as 7 IAs**: McNemar par a par; Cochran's Q; Friedman + Nemenyi;
      IC 95% por bootstrap.
- [x] **Concordância**: Kappa (IA×histórico).
- [ ] Kappa de Fleiss entre as IAs e refinamento das figuras ABNT (quando houver validação).

## P6 — Comparar TODAS as IAs juntas (incl. LSTM) ✅
- [x] 6 leves materializados.
- [x] **LSTM** (7ª IA) materializado — a aba `Multimodelo` já mostra as 7.
- [x] As 7 IAs lado a lado (`Multimodelo` + `Modelos`) e P5 (estatística) rodado sobre elas.

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

# multimodelo em dry-run (padrao seguro; nao grava)
gh workflow run multimodelo_classificacao.yml   --repo adinailson88/classificacao-chamados -f modelos=leves
gh workflow run multimodelo_reclassificacao.yml --repo adinailson88/classificacao-chamados -f modelos=leves

# gravacao manual: usar -f aplicar=true so depois de revisar o dry-run

# dashboard
gh workflow run dashboard.yml --repo adinailson88/classificacao-chamados
```

> Ordem recomendada: **P0 (painel) → P1 (materializar multimodelo) → P2 (workflows)
> → P3 (calibração) → P4 (validação humana)**. O foco imediato é o painel refletir
> corretamente o que já existe, não processar mais registros.

---

## Atualizacao executada pelo Codex - 2026-06-05 13:48

- O LSTM da materializacao multimodelo concluiu com sucesso no run `27026916670`.
- As 7 IAs estao materializadas com 13.825 registros por modelo e 0 pendentes: `naive_bayes`, `regressao_logistica`, `linear_svc`, `sgd`, `extra_trees`, `random_forest`, `lstm`.
- Ranking atual vs categoria historica: `linear_svc` 80,26% > `extra_trees` 78,47% > `sgd` 77,51% > `random_forest` 76,80% > `regressao_logistica` 76,59% > `naive_bayes` 70,07% > `lstm` 67,57%.
- `src/analise_estatistica.py` foi executado com sucesso e gerou `docs/dados/estatistica.json` com 13.825 linhas comuns e 7 modelos.
- Foi criada a aba `Estatistica` em `docs/index.html`, consumindo `estatistica.json` com bootstrap, correlacao confianca x acerto, Kappa, normalidade, residuos, Cochran Q, McNemar e Friedman/Nemenyi.
- O grafico de evolucao em `Modelos` ganhou seletor para acuracia do lote, acuracia acumulada, F1-macro do lote, F1-macro acumulado e balanced accuracy.
- Foram criados PDFs em `docs/ESTADO_DO_ROTEIRO.pdf` e `docs/DOCUMENTACAO_MODELOS_E_ESTATISTICA.pdf`.
- Reclassificacao continua sem prioridade, conforme decisao do usuario: so depois de concluir toda Etapa 1/multimodelo, estatistica e documentacao.

## Atualizacao - dashboard Classificacao, Modelos e normalidade (2026-06-05)

- [x] Remover `docs/dados/multimodelo_registros.json`, porque multiplicava chamados por 7 e gerava leitura incorreta de 96.775 "chamados".
- [x] Manter `Classificacao` como painel da Etapa 1/LSTM, usando `registros.json`.
- [x] Usar `multimodelo_metricas` e `multimodelo_turnos` como fonte principal da aba `Modelos`, com 13.825 chamados por IA.
- [x] Rebaixar `COMPARACAO_MODELOS` de 1.000 registros para tabela piloto/amostral, nao resultado principal.
- [x] Mostrar na aba `Estatistica` quando a normalidade for rejeitada e orientar pressupostos nao parametricos/bootstrap.
- [x] Regenerar e publicar o dashboard pelo workflow `dashboard.yml` (run `27052859362`, sucesso; commit de dados `0c1be12`). Conferencia final do Pages: aguardar cache/build.

## Atualizacao Codex - diagnostico de calibracao por IA (2026-06-06 01:37)

- [x] Criado `src/calibracao_modelos.py`.
- [x] Gerado `docs/dados/calibracao_modelos.json` com 7 modelos x 13.825 registros por IA.
- [x] `src/exportar_dashboard.py` passa a gerar `calibracao_modelos.json` automaticamente apos exportar `registros_<modelo>.json`.
- [x] `docs/index.html` ganhou tabela "Diagnostico de calibracao por IA" na aba `Metricas`.
- [x] Dashboard regenerado pelo workflow `27052859362` e dados atualizados no commit `0c1be12`.
- Resultado local preliminar contra historico:
  - menor ECE: `lstm` (`ece=0,0102`, mas acerto historico global menor: `67,57%`);
  - melhor faixa `>=95%` com suporte minimo de 138 casos: `regressao_logistica`
    (`n=1.467`, acerto historico `99,80%`);
  - `linear_svc` segue melhor em concordancia global (`80,26%`), mas a confianca bruta
    esta inutil para decisao direta (`ece=0,7101`, `>=95% n=0`), reforcando a necessidade
    de Platt/CalibratedClassifierCV antes de qualquer reclassificacao baseada em confianca.

## Atualizacao Codex - trava de seguranca da reclassificacao robusta (2026-06-06 01:54)

- [x] Removido o agendamento automatico de `.github/workflows/reclassificacao_robusta.yml`.
- [x] Workflow robusto agora e manual e roda em dry-run por padrao (`aplicar=false`).
- [x] Escrita na planilha so ocorre quando `aplicar=true` for escolhido explicitamente.
- Motivo: o dry-run anterior da reclassificacao multimodelo teve ganho liquido negativo
  (`corrigidos=5`, `prejudicados=9`, liquido `-4`); portanto nao deve haver escrita
  automatica antes da calibracao por modelo.

## Atualizacao Codex - Etapa 2 manual em dry-run por padrao (2026-06-06 02:13)

- [x] `.github/workflows/etapa2_reclassificacao.yml` deixou de gravar sempre.
- [x] Adicionado input `aplicar` com default `false`.
- [x] O workflow executa `src/executar_etapa2.py` sem `--aplicar` por padrao; so grava
  quando `aplicar=true` for escolhido manualmente.

## Atualizacao Codex - comandos seguros por padrao (2026-06-06 03:34)

- [x] Exemplos de `multimodelo_classificacao.yml` e `multimodelo_reclassificacao.yml`
  em `FALTA_FAZER.md` foram alterados para dry-run.
- [x] `aplicar=true` ficou documentado apenas como acao manual posterior a revisao do dry-run.

## Atualizacao Codex - guia tecnico sem reclassificacao automatica (2026-06-06 03:54)

- [x] `docs/GUIA_TECNICO.md` deixou de orientar Etapa 2/robusto como gravacao padrao.
- [x] Guia agora registra `etapa2_reclassificacao.yml` e `reclassificacao_robusta.yml`
  como manuais e dry-run por padrao.
- [x] `dados/README.md` trocou referencia legada a `doPost` por escrita `gspread`.

## Atualizacao Codex - calibracao escalar ajustada (2026-06-06 02:35)

- [x] Criado `src/calibracao_confianca.py`: calibra `P(previsao correta | confianca_bruta)`
  por modelo, out-of-fold, usando sigmoid/isotonica e apenas `registros_<modelo>.json`.
- [x] Gerado `docs/dados/calibracao_ajustada_modelos.json` sem texto de chamado.
- [x] `src/exportar_dashboard.py` passa a gerar a calibracao ajustada automaticamente.
- [x] `docs/index.html` ganhou tabela "Calibracao ajustada preliminar" na aba `Metricas`.
- [x] `dashboard.yml` passou a instalar `numpy` e `scikit-learn`, necessarios para a nova rotina.
- Resultado local preliminar contra historico: melhor ECE ajustado `sgd`; `linear_svc`
  caiu de `ECE=0,7101` para `ECE=0,0019` e passou a ter faixa ajustada `>=95%` com
  `n=5.125` e acerto historico `98,36%`. Definitivo ainda depende de validacao humana.

## Atualizacao Codex - documentacao alinhada a calibracao (2026-06-06 02:54)

- [x] `PLANO_CALIBRACAO.md` atualizado para diferenciar diagnostico bruto, calibracao
  escalar ajustada ja publicada e calibracao definitiva pos-validacao humana.
- [x] `README.md` passou a listar `calibracao_modelos.json` e
  `calibracao_ajustada_modelos.json`.
- [x] `DOCUMENTACAO_MODELOS_E_ESTATISTICA.md` ganhou secao de calibracao preliminar com
  exemplo operacional e leitura do `linear_svc`.

## Atualizacao Codex - robustez do workflow estatistico (2026-06-06 03:14)

- [x] `.github/workflows/estatistica.yml` passou a usar `git pull --rebase --autostash`
  com 5 tentativas antes do `git push`, igual ao dashboard.
- Motivo: evitar falha por corrida de push quando `dashboard.yml`, Pages ou outro workflow
  commitar dados enquanto a estatistica esta terminando.
