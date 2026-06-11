# FALTA FAZER — classificacao-chamados

> Documento único de **pendências/próximos passos**. Substitui o handoff
> `CLAUDE_CONTINUACAO_2026-06-05.md` (removido). O panorama histórico continua em
> `CONTEXTO.md`; aqui fica só o **que ainda falta**, priorizado.
>
> Atualizado: 2026-06-11 (America/Bahia, UTC-03:00).

## BRIEFING PARA O CODEX — estado em 2026-06-11 e o que vem a seguir

### Onde o projeto está
1. **Pipeline completo e no ar.** 7 IAs materializadas out-of-fold (13.825 chamados
   cada), estatística não paramétrica, calibração preliminar, taxonomia (termos +
   correlação + cruzamento) com dados reais, dashboard publicado no Pages.
2. **Validação humana COMEÇOU** (não está mais em `validados=0`): **354 conferências**
   nas colunas M/N da `CHAMADOS_ESQUELETO_REDUZIDO` → 305 decisões travadas,
   49 restritos, **2 conflitos pendentes de revisão** (M=Correto e N=Correto com
   C≠G — impossível; filtrar e corrigir na planilha).
3. **Memória de decisão implementada** (`src/decisao_validada.py` + `predict_dist` no
   zoo + `prever_out_of_fold(vetos=)`): categoria conferida como ERRADA fica vetada
   por chamado; conferida como CERTA trava e é reusada sem reprocessar. Regra do
   pesquisador — **não relaxar**.
4. **Reclassificação dos validados executada** (`--so-validados`): 6 leves aplicados
   (354 cada = 305 reuso `decidido_humano` + 49 re-preditos com veto, todos
   `sem_referencia`); LSTM com legado etapa-2 (+14 de ganho) e run so-validados na
   fila. Resumo em `docs/dados/reclass_resumo.json`, exibido na aba `Reclassificacao`.
5. **Resposta final parcial publicada** (`avaliacao_final.json`, n=305): ranking
   VALIDADO `linear_svc` 67,9% [62,6–73,1] > reg_log 66,9% > sgd 66,6% > rf 61,3% >
   et 58,7% > lstm 56,4% > nb 54,1%; melhor vs 2ª NÃO significativo (McNemar p=0,73);
   **nenhum ensemble supera a melhor IA** (melhor delta +0,33 p.p., p=1,0) → por ora
   não vale combinar. Análise de erros (n=354, 91 erros): erros têm títulos MAIS
   LONGOS (p=0,008) — hipótese "texto pobre → erro" NÃO confirmada nesta amostra
   parcial; cobertura de termos discriminativos ainda sem significância (p=0,17).
   Tudo na aba `Decisao`.
6. **Exportação**: botão ⬇PNG em todos os gráficos; `docs/exportar_analises.py`
   (download na Documentação) reproduz os cálculos de todas as abas direto da
   planilha, comentado, somente leitura.
7. **Taxonomia**: visão POR CATEGORIA (seletor + barras + "Outros" abaixo do limiar);
   heatmap 44×44 completo recolhido em `<details>`.

### O que executar a seguir (prioridade)
1. **Aguardar o pesquisador terminar a conferência manual (M/N)** — pendência humana,
   não técnica. Quando terminar: `gh workflow run avaliacao_final.yml` (a aba
   `Decisao` substitui a resposta parcial pela final) e re-rodar
   `multimodelo_reclassificacao.yml` com `so_validados=true` + `aplicar=true`
   (novos conferidos entram no reuso/veto).
2. **Conferir os 2 conflitos** (item humano; ver §1.2).
3. **Confirmar o run LSTM so-validados** (`27352686850`, estava na fila do grupo
   `escrita-planilha`) e, depois dele, rodar `dashboard.yml` para atualizar
   `reclass_resumo.json`.
4. **Recalibrar os limiares de prioridade da validação não supervisionada**
   (62% da base caiu em "Alta" — não tria; propor score contínuo; decisão do
   pesquisador antes de implementar).
5. **Revisão humana da taxonomia** (etapa 46) com `cruzamento_taxonomia.json`
   (duplicações estruturais: Ar condicionado, Hidráulica, Telhados, Extintor).
6. Reavaliar a análise de erros quando a conferência terminar (a amostra parcial
   priorizou divergentes; o achado "títulos longos erram mais" pode inverter).

### Regras inegociáveis (manter)
- Concordância com histórico ≠ acurácia validada; rotular sempre.
- Dry-run por padrão; `aplicar=true` só manual e justificado.
- Não tocar em C (histórico) nem M/N/P (conferências); reclassificação grava em
  RECLASS__/coluna O.
- Não publicar texto de chamado nos JSON do Pages (só agregados/termos).
- Memória de decisão: errado conferido nunca volta; certo conferido nunca reprocessa.

## Estado atual (resumo)
- **Etapa 1 (LSTM single-model)** na aba `Classificacao`: base elegível de **13.825**
  chamados, classificação progressiva em turnos de 15 concluída (0 pendentes),
  54 categorias, `ece_historico=0.0379`. Fonte do painel: `registros.json`.
- **Multimodelo materializado** — as **7 IAs completas**, 13.825 chamados por modelo,
  0 pendentes, predição **out-of-fold** (`kfold_5`). Concordância vs categoria histórica:
  `linear_svc` 80,26% > `extra_trees` 78,47% > `sgd` 77,51% > `random_forest` 76,80% >
  `regressao_logistica` 76,59% > `naive_bayes` 70,07% > `lstm` 67,57%. A comparação das
  7 IAs vive nas abas `Modelos`, `Multimodelo` e `Estatistica` (não em `Classificacao`).
- `multimodelo_registros.json` foi **removido** de propósito: multiplicava chamados por 7
  e exibia ~96.775 predições como se fossem chamados. **Não recriar.**
- Análise estatística assume **pressupostos não paramétricos** (Shapiro rejeitou
  normalidade nos 7 modelos): Spearman, Friedman/Nemenyi, Cochran Q, McNemar e bootstrap.
  Resultados contra o histórico são preliminares; os validados estão na aba `Decisao`.

> ⚠️ As métricas das abas históricas são **concordância contra a categoria
> histórica (C)**. O acerto **validado** (conferência humana M/N/P) existe desde
> 2026-06-10 e vive na aba `Decisao` — parcial até a conferência terminar.

---

## P0 — Corrigir o DASHBOARD (prioridade do usuário)
O painel não está refletindo o que o experimento já produz. Antes de processar mais
dados, fazer o painel mostrar a verdade.

> ✅ **Status 2026-06-05**: P0.1–P0.7 implementados e publicados (commit `e8df9b2`;
> dashboard run `27025224132` OK). `comparacao_categoria.json` (3.114 no resumo atual) e
> `multimodelo_*` já populados. P0.3-extra também foi concluído em 2026-06-06:
> a aba `Categorias` agora tem tabela de comparação por categoria/modelo consumindo
> `comparacao_categoria.json`.
>
> ✅ **Status 2026-06-06**: revisão estática do `docs/index.html` confirmou P0.1–P0.7
> alinhados ao painel publicado. `comparacao_previsoes.json` agora tambem e publicado
> em versao sanitizada, sem ID, titulo ou observacao livre.

### P0.1 Filtros (UX e correção)
- [x] Indicar **claramente** quando um filtro está ativo (chips/lista dos ativos + contador).
- [x] Botão **Limpar** mais evidente.
- [x] Corrigir o dropdown que **cobre abas/gráficos**; fechar após seleção (ou melhorar layout).
- [x] Conferir que `aplicarFiltros()` é chamado a cada checkbox.
- [x] Conferir que `REG` carrega de `docs/dados/registros.json` e que os campos existem:
      `g` grupo, `f` faixa, `e` executor, `k` concorda/diverge, `v` validação humana.
      Se algum vier vazio, corrigir em `src/exportar_dashboard.py`.
- [x] Verificar que os filtros **recalculam**: cards superiores, aviso verde, contador
      à direita, gráfico de faixa de confiança, tabelas de `Categorias`, resumo de `Metricas`.
- [x] Deixar **explícito na interface** quais gráficos **NÃO** são filtráveis por decisão
      (Evolução da concordância por turno, Confiança média por turno, Reclassificação) —
      hoje parece bug. Pôr um rótulo/aviso no topo desses gráficos.

### P0.2 Aba `Modelos` está enganosa
- [x] Remover lógica antiga de **última execução por modelo**.
- [x] Usar a comparação principal das 7 IAs na base completa (`multimodelo_metricas`).
- [x] Mostrar **ranking** dos modelos por concordância na base completa.
- [x] Mostrar **evolução por turno/lote** com seletor de métrica.
- [x] Mostrar **tabela com todos os recortes** held-out de 1.000 até 13.825.

### P0.3 Exportar mais JSONs (`src/exportar_dashboard.py`)
- [x] Publicar `comparacao_categoria.json` (de `COMPARACAO_CATEGORIA`).
- [x] Publicar `multimodelo_turnos.json` (de `MULTIMODELO_TURNOS`).
- [x] Publicar `multimodelo_metricas.json` (de `MULTIMODELO_METRICAS`).
- [x] Publicar `multimodelo_reclass_turnos.json` (de `MULTIMODELO_RECLASS_TURNOS`).
- [x] Mostrar no painel a comparação por categoria/modelo consumindo
      `comparacao_categoria.json`.
- [x] Publicar `comparacao_previsoes.json` em versao sanitizada, removendo `id_chamado`,
      `titulo` e `observacao_avaliador` antes de ir para o GitHub Pages.

### P0.4 Nova aba `Multimodelo` no painel
- [x] Progresso por modelo (feitos/pendentes), concordância por modelo materializado,
      e dados de reclassificação multimodelo quando existirem.

### P0.5 Aba `Metricas`
- [x] Separar visualmente: métricas **vs histórico** × **validadas** × **calibração**
      × **pendentes** × **meta 95%**.
- [x] Aviso grande quando `validados=0` (métricas preliminares, não validadas).

### P0.6 Aba `Reclassificacao`
- [x] Estado vazio com mensagem objetiva: "Etapa 2 ainda não executada após o reset"
      / "Validação humana não iniciada" / "Próximo passo técnico: dry-run ou aplicação controlada".

### P0.7 Deixar a META 95% honesta
- [x] Mostrar status claro por faixa: "aprovado **contra histórico**",
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
      Primeiro dry-run controlado executado em 06/06/2026, run `27059977070`,
      `modelos=leves`, `max_turnos=1`, `aplicar=false`: 90 simulações, 0 escrita na
      planilha; ganho líquido fraco (`extra_trees=+1`, `linear_svc=-2`,
      `regressao_logistica=-1`, demais `0`). Não aplicar em massa ainda.
      Dry-run complementar do LSTM executado no run `27060370440`, `modelos=pesados`,
      `max_turnos=1`, `aplicar=false`: 15 simulações, ganho `0`
      (`corrigidos=2`, `prejudicados=2`). A conclusão permanece: não aplicar em massa.
      Dry-runs ampliados em 06/06/2026, ainda sem escrita: run `27067150023`
      (`modelos=leves`, `max_turnos=10`) simulou 900 reclassificações e teve ganho
      líquido total `+16` (`random_forest=+9`, `linear_svc=+6`, `naive_bayes=+2`,
      `regressao_logistica=+1`, `extra_trees=0`, `sgd=-2`); run `27067201945`
      (`modelos=pesados`, `max_turnos=10`) simulou 150 casos LSTM e teve ganho `+19`.
      Dry-runs maiores com `max_turnos=30`: run `27067681539` (`modelos=leves`) simulou
      2.700 casos e teve ganho consolidado `-1` (`random_forest=+23`,
      `extra_trees=+2`, `naive_bayes=0`, `regressao_logistica=-5`,
      `linear_svc=-10`, `sgd=-11`); run `27067734826` (`modelos=pesados`) simulou
      450 casos LSTM e teve ganho `+33`.
      Por decisao explicita do usuario em 06/06/2026, iniciou-se aplicacao real controlada
      **somente do LSTM**, um turno de 15 por execucao, para nao pesar a API:
      runs `27067922061`, `27068022450` e `27068138920`, todos publicados no dashboard.
      Acumulado publicado: 45 reclassificacoes, `corrigidos=7`, `prejudicados=6`,
      ganho liquido `+1`. Rodadas seguintes tambem aplicadas e publicadas:
      `27068325982` (`+2`) e `27068433347` (`+1`). Acumulado apos 5 turnos:
      75 reclassificacoes, `corrigidos=11`, `prejudicados=7`, ganho liquido `+4`.
      **6o turno**: run `27068597005`, `GANHO=0` &rarr; acumulado 90 reclassificacoes,
      ganho liquido `+4`. **7o turno**: run `27068688359`,
      `corrigidos=4 | prejudicados=2 | GANHO=+2` (metodo topup) &rarr; acumulado
      105 reclassificacoes, ganho liquido +6. **8o turno**: run `27069146071`,
      `corrigidos=2 | prejudicados=2 | GANHO=0` &rarr; acumulado
      **120 reclassificacoes, ganho liquido +6** (validado em
      `docs/dados/multimodelo_reclass_turnos.json`: ganhos por turno
      `0,+2,-1,+2,+1,0,+2,0`). Cadeia dashboard/Pages OK
      (`27069206479`/`27069219526`).
      **9o turno**: run `27069502066`, `GANHO=+3` &rarr; acumulado
      **135 reclassificacoes, ganho liquido +9** (json `0,+2,-1,+2,+1,0,+2,0,+3`).
      **10o turno**: run `27069599870` calculou `GANHO=+2` mas **FALHOU na gravacao**
      (`ConnectionError`/RemoteDisconnected no append) &rarr; NAO registrado (json segue
      com 9 turnos). Corrigido em `05bb196` (`_append_resiliente` com retry nas duas
      gravacoes). Possivel residuo: ate 15 linhas por-chamado orfas em `RECLASS__lstm`.
      Lote seguinte (codigo resiliente) runs `27069889301`/`27069951087`/`27070030886`:
      ganhos `+0,+4,+1`, todos gravados. **Acumulado publicado: 12 turnos = +14, 180
      reclassificacoes** (`0,+2,-1,+2,+1,0,+2,0,+3,0,+4,+1`; dashboard `27070103104`).
      Continuar apenas turno a turno enquanto o ganho acumulado permanecer nao
      negativo; **avaliar calibracao por modelo**; nao iniciar validacao humana.

---

## P2 — Robustez dos WORKFLOWS (falha de instalação)
Run manual `27001950857` da Etapa 1 falhou no `pip` baixando `tensorflow==2.17.0`
(`IncompleteRead`, exit 2) — não foi erro de lógica.
- [x] `etapa1_turnos.yml` já usa `cache: pip`, `requirements-leves.txt` +
      `requirements.txt` no cache e `pip install --retries 5 --timeout 120`.
- [x] `multimodelo_classificacao.yml` e `multimodelo_reclassificacao.yml` ja usam cache,
      retry/timeout e separam dependencias leves de TensorFlow.
- [x] `dashboard.yml`, `estatistica.yml`, `etapa2_reclassificacao.yml`,
      `reclassificacao_robusta.yml`, `reclassificacao_dry_run.yml`,
      `preparar_validacao.yml`, `resetar.yml` e `comparar_modelos.yml` usam retry/timeout.
- [x] Separar **workflow leve** (baseline/lineares, sem TF) do **workflow LSTM** (com TF)
      tambem nos fluxos legados que ainda instalam `requirements.txt` completo,
      para que o download grande não derrube execuções leves.

---

## P3 — CALIBRAÇÃO rumo ao objetivo dos ≥95%
Diagnostico bruto e calibracao escalar preliminar ja foram publicados. Ainda falta a
calibracao definitiva, treinada/avaliada contra validacao humana.
- [x] Diagnostico bruto por IA: `docs/dados/calibracao_modelos.json`.
- [x] Calibracao escalar preliminar out-of-fold por IA:
      `docs/dados/calibracao_ajustada_modelos.json`.
- [ ] Implementar calibradores definitivos por modelo quando houver rotulos humanos
      (`CalibratedClassifierCV`/Platt para lineares, isotonico para arvores/NB,
      temperature scaling ou equivalente para LSTM).
- [ ] Confirmar que a faixa ≥95% mantém acerto ~≥95% (preliminar vs histórico; definitivo
      só após validação humana).

---

## P4 — VALIDAÇÃO HUMANA + métricas finais (PAUSADA por decisão do usuário)

> **Novo modo de validação (2026-06-06): conferência dupla na aba principal.** O veredito
> humano deixa de depender da aba `VALIDACAO_HUMANA`/`categoria_validada` e passa a ser
> registrado em duas colunas da `CHAMADOS_ESQUELETO_REDUZIDO`:
> `M` = **CONFERÊNCIA GLPI** (a classificação histórica, coluna `C`, está `Correto`/`Errado`) e
> `N` = **CONFERÊNCIA IA** (a classificação da IA, coluna `G`, está `Correto`/`Errado`).
> Isso permite a matriz 2x2 IA×GLPI e a identificação de falsos positivos/negativos
> (inclusive casos em que a IA corrige o histórico). Leitura: `Correto` = acerto; qualquer
> outro valor não vazio = `Errado`; vazio = não validado. Código adaptado em
> `planilha.ler_conferencias`, `calibracao.py` e `exportar_dashboard.py`.

A revisão manual permanece **pausada** por decisão do usuário (será feita por ele depois).
- [ ] Preencher `M`/`N` para os casos a validar (prioridade: divergentes IA×histórico).
- [ ] Após validação: matriz de confusão IA×GLPI, métricas por categoria, **confiança
      calibrada validada** por faixa, indicadores finais, e **re-treino** com a base validada.

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
- [x] Kappa de Fleiss entre as IAs (`fleiss_kappa_entre_ias=0,7721` em
      `docs/dados/estatistica.json`, exibido na aba `Estatistica`).
- [ ] Refinamento das figuras ABNT quando houver validação humana.

## P6 — Comparar TODAS as IAs juntas (incl. LSTM) ✅
- [x] 6 leves materializados.
- [x] **LSTM** (7ª IA) materializado — a aba `Multimodelo` já mostra as 7.
- [x] As 7 IAs lado a lado (`Multimodelo` + `Modelos`) e P5 (estatística) rodado sobre elas.

> 📄 **Mapa completo do estado das 50 etapas do roteiro**: ver `ESTADO_DO_ROTEIRO.md`.

## P7 — RELEVÂNCIA DE TERMOS + MAPA DE CORRELAÇÃO (solicitado 2026-06-10) ✅ implementado
Ideia do usuário: clusters de palavras-chave por categoria (ex.: água/torneira/sanitário →
hidráulica) + "mapa de correlação" entre categorias (analogia geoprocessamento: célula
quente quando correlação → 1).
- [x] `src/relevancia_termos.py`: log-odds (prior Dirichlet) + peso TF-IDF por categoria;
      cosseno entre centróides → matriz de correlação + pares mais próximos. Dry-run padrão.
- [x] `docs/mapa_correlacao.html`: mapa de calor + termos por categoria (clicável).
- [x] `.github/workflows/relevancia_termos.yml` (manual, `aplicar=false`).
- [x] `docs/RELEVANCIA_TERMOS.md` + `docs/RELATORIO_ESTADO_ATUAL.md`.
- [x] Lógica testada em corpus sintético (par HIDRAULICA×HIDROSSANITARIO destacado).
- [x] **Cruzamento confusão IA×histórico × correlação** (`src/cruzamento_taxonomia.py`):
      ranqueia candidatos a revisão de taxonomia; viewer ganhou a tabela; workflow roda os
      dois; testado em sintético (par sobreposto no topo, ruído zerado).
- [x] **Documentação do dashboard atualizada** (`docs/index.html`, aba Documentação):
      card metodológico (registro impessoal/acadêmico) com todos os procedimentos.
- [x] **Reestruturação do painel** (`docs/index.html`): (a) abas `Modelos`+`Multimodelo`
      fundidas em `Modelos` (reclassificação multimodelo movida para lá; removidos cartões
      duplicados de progresso/evolução por modelo); (b) mapa de correlação embutido como aba
      `Taxonomia` (heatmap + termos + pares + candidatos a revisão), não mais só página avulsa;
      (c) 1ª aba (`Classificação`) reformada com gráficos que recalculam com os filtros
      (concordância por categoria com volume; rosca concorda×diverge; faixa de confiança),
      evolução por turno movida para o rodapé rotulada. Verificado no preview.
- [x] **Rodar com credenciais** (workflow `relevancia_termos.yml`) para gerar os JSON reais
      e popular a aba `Taxonomia` contra a planilha viva. ✅ Executado em 10/06/2026,
      run `27298524010` (dry-run, `top_n=25`, `min_df=5`, `min_chamados_categoria=10`),
      sucesso em 36s; commit de dados `6065597` com os 4 JSON
      (`termos_relevantes` 44 categorias, `correlacao_categorias`,
      `confusao_historico_ia`, `cruzamento_taxonomia`). Pages publicado
      (run `27298562277`). Aba `Taxonomia` verificada no preview local com os dados
      reais (heatmap 44×44, 15 pares, 30 candidatos, termos por categoria; sem erro
      de console). Conferência de conteúdo: termos coerentes (ex.: Ar condicionado →
      "gelando", "split", "gás", "parou funcionar") e topo dos candidatos a revisão
      aponta duplicações reais da taxonomia — `Climatização > Ar condicionado` ×
      `Manutenção Preventiva > Ar condicionado split` (confusão 22,7%, correlação
      vocabular 0,647), `Hidráulica` duplicada em Hidrossanitária × Manutenção
      Preventiva, `Telhados/calhas/rufos` duplicado em Estrutura Predial × Manutenção
      Preventiva. Decisão de fusão/desambiguação segue sendo **humana**.

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

## Atualizacao - memoria de decisao + resposta final pronta (2026-06-10, noite)

Pedido do pesquisador: (a) a reclassificacao deve ELIMINAR categorias ja conferidas
como erradas (nao repetir o erro) e REUSAR categorias conferidas como certas (nao
reprocessar o decidido); (b) deixar tudo pronto para que, ao fim da conferencia
manual, dashboard e scripts respondam: qual IA usar, com que peso, o quanto e melhor,
se vale combinar, e por que a IA erra (que informacoes pedir ao solicitante).

- [x] **`src/decisao_validada.py`** (novo): memoria de decisao por chamado a partir de
  M/N/P + C/G/O — `decidida` (trava), `eliminadas` (veto), `conflito` (duas conferencias
  'Correto' contraditorias devolvidas a revisao), status decidido/restrito/sem_validacao.
- [x] **`predict_dist`** em todos os modelos do zoo (proba, margem softmax, LSTM,
  transformer) + `prever_out_of_fold(..., vetos=)`: a predicao escolhe a melhor
  categoria FORA do conjunto vetado, com confianca renormalizada.
- [x] **`reclassificacao_multimodelo.py`** integrado a memoria: linhas decididas sao
  reaproveitadas sem reprocessar (res=`decidido_humano`), categorias vetadas nao se
  repetem, o treino usa a verdade validada quando travada, e a comparacao passa a ser
  contra a verdade validada (campo novo `base_comparacao`; historico conferido como
  errado vira `sem_referencia` e nao conta em corrigidos/prejudicados).
- [x] **`src/avaliacao_final.py`** (novo): acerto VALIDADO por IA (+IC95 bootstrap),
  pesos (log-odds/normalizado), ensembles maioria simples/ponderada/confianca calibrada
  maxima com pesos aprendidos OUT-OF-FOLD, McNemar vs melhor IA, veredicto
  vale-combinar. Gera `docs/dados/avaliacao_final.json`; com validados < minimo, sai
  `status=aguardando_validacao` (sem inventar numero).
- [x] **`src/analise_erros.py`** (novo): erros x acertos da IA (conferencia N) por
  caracteristica do texto (comprimentos, tokens, campos preenchidos, cobertura dos
  termos discriminativos da categoria verdadeira), Mann-Whitney + delta de Cliff;
  por categoria, termos que faltaram nos erros -> "informacao a solicitar" na abertura
  (sem nunca pedir a categoria ao solicitante). Gera `docs/dados/analise_erros.json`.
- [x] **`.github/workflows/avaliacao_final.yml`** (novo, manual): roda os dois scripts
  e commita os JSON.
- [x] **Aba `Decisao`** no dashboard: ranking validado com pesos, vale-combinar com
  McNemar, erros x acertos, checklist por categoria e campos de formulario sugeridos.
  Estado vazio honesto enquanto `validados=0`. Verificado no preview (vazio + simulado).
- [x] Testes offline novos: `tests/test_decisao_memoria.py` (18 testes, todos passando)
  cobrindo regras de decisao, veto na predicao OOF, ensembles e analise de erros.
- [x] **Primeira execucao real** do `avaliacao_final.yml` (run `27300506477`, sucesso;
  commit de dados `3ca6cdb`): a planilha JA TEM **354 conferencias** (305 decisoes
  travadas, 49 restritos, **2 conflitos** — duas conferencias 'Correto' com categorias
  diferentes, a localizar filtrando M=Correto e N=Correto com C<>G). Resultado PARCIAL
  (~2,2% da base, amostra possivelmente nao aleatoria):
  ranking validado `linear_svc` 67,9% [62,6–73,1] > `regressao_logistica` 66,9% >
  `sgd` 66,6% > `random_forest` 61,3% > `extra_trees` 58,7% > `lstm` 56,4% >
  `naive_bayes` 54,1%; melhor vs segunda +0,98 p.p. (McNemar p=0,73, NAO
  significativo); nenhum ensemble supera a melhor IA com significancia
  (maioria_ponderada +0,33 p.p., p=1,0) -> por ora **nao vale combinar**.
  Analise de erros (91 erros / 263 acertos): erros tem titulos MAIS LONGOS
  (mediana 69 vs 46, p=0,008, delta=0,18) e mais tokens (p=0,029) — a hipotese
  "texto curto -> erro" NAO se confirma nesta amostra parcial; cobertura de termos
  discriminativos ainda sem significancia (p=0,17). Reavaliar ao fim da conferencia.
- [ ] **Ao terminar a conferencia manual (M/N)**: rodar de novo
  `gh workflow run avaliacao_final.yml --repo adinailson88/classificacao-chamados`
  e ler a aba `Decisao` (a resposta final substitui a parcial). Antes disso, conferir
  os **2 conflitos** apontados acima. Opcional: dry-run da reclassificacao para ver
  o reuso/veto em acao.

## Atualizacao - execucao com credenciais reais (2026-06-10, tarde)

- [x] `relevancia_termos.yml` executado com sucesso (run `27298524010`, dry-run, 36s).
  Os 4 JSON reais foram publicados em `docs/dados/` (commit `6065597`) e o Pages
  atualizou (run `27298562277`). Aba `Taxonomia` verificada em preview local com os
  dados reais: heatmap 44x44, 15 pares, 30 candidatos, termos por categoria, sem erro
  de console. Conteudo coerente; topo dos candidatos aponta duplicacoes estruturais da
  taxonomia (Ar condicionado em Climatizacao x Manutencao Preventiva; Hidraulica em
  dois grupos; Telhados/calhas/rufos duplicado; Extintor x Combate a incendio).
- [x] **Diagnostico dos cancelamentos** de `validacao_nao_supervisionada.yml`: os 5 runs
  de 09/06 (incluindo o de "1h34m") **nunca executaram** — ficaram presos na fila do
  grupo de concorrencia `escrita-planilha` e foram cancelados ainda na fila (0 jobs).
  Nao ha defeito no script.
- [x] Primeira execucao real da **validacao nao supervisionada** (run `27298888472`,
  dry-run, ~35s, nada gravado): 13.825 chamados, 53 categorias, `tfidf_svd_100`,
  silhouette `0,0972`, Davies-Bouldin `3,99`, Calinski-Harabasz `128,2`. Prioridades:
  Alta=8.589, Media=1.719, Baixa=3.517.
- [ ] **Recalibrar os limiares de prioridade** da validacao nao supervisionada antes de
  usa-la como fila de revisao humana: 62% da base em "Alta" nao tria nada. Opcoes:
  exigir consenso forte E margem semantica simultaneamente, ou substituir as 3 faixas
  por um score continuo ordenavel. Decisao do pesquisador.
- [ ] (segue) Revisao humana da taxonomia a partir de `cruzamento_taxonomia.json`
  (fusao/desambiguacao dos pares duplicados) — etapa 46, decisao do pesquisador.

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

## Atualizacao Codex - revisao tecnica final para conferencia humana (2026-06-11 11:50)

- [x] Criado `src/auditar_conferencias.py`: auditoria read-only por padrao, JSON publico sanitizado em `docs/dados/auditoria_conferencias.json`, e escrita opcional da aba privada `AUDITORIA_CONFERENCIAS` apenas com `--aplicar`.
- [x] Criado workflow manual `auditar_conferencias.yml`, com `aplicar=false` por padrao e commit apenas do JSON sanitizado.
- [x] Criado `src/check_final_ready.py` e workflow manual `check_final_ready.yml`; o verificador nao acessa a planilha, compila scripts e confere JSONs publicos essenciais.
- [x] `planilha.ler_conferencias` e `decisao_validada.carregar_decisoes` passaram a localizar C/G/O/M/N/P por cabecalho normalizado, com fallback para as posicoes atuais.
- [x] `reclassificar_validados.yml` ficou manual, dry-run por padrao, com input `modelo` (`robusto`, `transformer_ft`, `producao`, `baseline`) e confirmacao literal `APLICAR_O` para gravar coluna O.
- [x] `classificacao_ia_2_dryrun.yml` passou a imprimir explicitamente que NAO grava coluna O e que `aplicar_abas=true` grava somente abas auxiliares.
- [x] `validacao_nao_supervisionada.py` ganhou `score_prioridade_revisao` continuo e prioridade `Alta` seletiva por percentil 85/top 15%, preservando as colunas antigas.
- [x] Testes offline de conferencia por cabecalho/fallback/veto adicionados em `tests/test_decisao_memoria.py`.

Validacoes executadas: `git pull --rebase` retornou `Already up to date`; `python -m py_compile` dos arquivos alterados OK; `python -m py_compile` de todo `src` OK via `src/check_final_ready.py`; `python -m unittest discover -s tests -v` OK com `PYTHONPATH` apontando para `.codex_deps` do clone anterior (23 testes); `python src/check_final_ready.py` OK.

Workflows verificados por `gh run list`: `avaliacao_final.yml` teve ultimo sucesso `27300506477` e falha posterior `27301142348`; `dashboard.yml` teve sucessos recentes e skips por `workflow_run`; `multimodelo_reclassificacao.yml` tem run atual pendente `27353706958` e run cancelado `27352686850`; `reclassificar_validados.yml` teve ultimos runs antigos com sucesso em 06/06/2026. `gh run view 27352686850 --log` nao retornou log; o run existe e esta cancelado.

Estado humano: `docs/dados/avaliacao_final.json` registra `validados=305`, `conflitos=2`, `melhor_ia=linear_svc`, `status=ok`. Proximo passo humano: concluir/revisar M/N/P, especialmente os conflitos, antes de qualquer gravacao controlada em O.
