# Estado do Roteiro Metodológico (50 etapas) + atualizações

> Avaliação de onde o experimento está em relação ao **Roteiro Metodológico para
> Avaliação da Evolução da Classificação e Reclassificação Automática de Chamados no
> Malha IA** (50 etapas), **atualizada** com as decisões dos últimos dias.
> Legenda: ✅ feito · 🟡 parcial/pronto-não-executado · ⬜ pendente · ⏸️ pausado por decisão do usuário.
> Atualizado: 2026-06-05 (America/Bahia). Base observada: ~13.825 chamados elegíveis (cresce).

## Etapa 1 — Classificação inicial (etapas 1–16)
| # | Etapa | Estado | Evidência |
|---|---|---|---|
| 1 | Isolamento do ambiente | ✅ | repo `classificacao-chamados` + aba `CHAMADOS_ESQUELETO_REDUZIDO`, separados do Malha IA |
| 2 | Base inicial congelada | ✅ | ~13.825 elegíveis (categoria C + texto); recontada por execução (dados dinâmicos) |
| 3 | Limpeza dos resultados anteriores | ✅ | `resetar_experimento.py` limpa G:K (preserva C, L, M) |
| 4 | Fórmula de conferência IA×original | ✅ | `K = =SE(G="";"";G=C)` (no layout reduzido o original é C, não M) |
| 5 | run_id único | ✅ | `EXP_CLASSIFICACAO_CHAMADOS_2026_06_001` |
| 6 | Registro da configuração | ✅ | `config_experimento.json` + aba `EXPERIMENTO_CONFIG` |
| 7 | Aba EXPERIMENTO_CONFIG | ✅ | criada |
| 8 | Aba LOG_TURNOS_CLASSIFICACAO | ✅ | turnos de 15, taxa + acumulada |
| 9 | Aba LOG_LINHA_A_LINHA | ✅ | criada |
| 10 | Execução Etapa 1 em turnos de 15 | ✅ | `executar_etapa1.py` (LSTM+RF) progressivo |
| 11 | Registro imediato por turno | ✅ | append por turno |
| 12 | Concordância por turno | ✅ | gráfico no painel |
| 13 | Concordância acumulada | ✅ | gráfico no painel |
| 14 | Análise de confiança por faixa | ✅ | faixas <70 / 70–95 / ≥95 |
| 15 | Análise por executor/método | ✅→**estendida** | LSTM/RF na Etapa 1; **ampliada para 7 IAs** (ver Extensão A) |
| 16 | Congelamento da Etapa 1 | ✅ | `SNAPSHOT_ETAPA_1` |

## Etapa 2 — Reclassificação (etapas 17–23)
| # | Etapa | Estado | Evidência |
|---|---|---|---|
| 17 | Candidatos < 95% | ✅ | `executar_etapa2.py` + `reclassificacao_multimodelo.py` |
| 18 | Aba LOG_TURNOS_RECLASSIFICACAO | ✅ | criada |
| 19 | Estado anterior à reclassificação | ✅ | lido do snapshot |
| 20 | Execução da Etapa 2 | 🟡 | scripts prontos; dry-run validado; **não aplicada após o reset** |
| 21 | Estado posterior | 🟡 | estrutura pronta (antes/depois) |
| 22 | Ganho líquido | ✅ | calculado (corrigidos − prejudicados) |
| 23 | Comparação etapa1×etapa2 vs original | 🟡 | depende de rodar a Etapa 2 |

## Validação humana (etapas 24–35) — ⏸️ PAUSADA por decisão do usuário
| # | Etapa | Estado |
|---|---|---|
| 24 | Preparação da validação humana | ✅ (aba `VALIDACAO_HUMANA` com 1.654 casos divergentes + dropdowns) |
| 25–33 | Validação divergentes/todos; IA_CERTA/GLPI_CERTO/AMBOS_ERRADOS/AMBOS_CORRETOS/CASO_AMBIGUO/NAO_AVALIADO | ⏸️ não iniciar agora (fortalecer modelo/scripts antes) |
| 34 | Campo "usar para treino" (SIM/NAO/REVISAR) | 🟡 estrutura pronta (`memoria_validada.py`) |
| 35 | Versão da taxonomia | ⬜ |

## Métricas e comparações (etapas 36–43)
| # | Etapa | Estado | Observação |
|---|---|---|---|
| 36 | Matriz de confusão | ⬜ | definitiva precisa de validação humana; **dá para gerar vs histórico já** |
| 37 | Métricas por categoria | ✅ | `METRICAS_POR_CATEGORIA` (vs histórico) |
| 38 | Confiança × acerto (calibração) | ✅ | `calibracao.json` (ECE); **definitiva após validação**. OOF tornou honesta |
| 39 | Avaliação real da reclassificação | ⬜ | precisa de validação humana |
| 40 | Comparação histórico/etapa1/etapa2 | 🟡 | |
| 41 | Base validada para retreino | ⬜ | `memoria_validada` pronto, sem dados ainda |
| 42 | Modelo treinado em histórico × validado | ⬜ | |
| 43 | Indicadores consolidados | 🟡 | parte no painel |

## Gráficos e diagnóstico (etapas 44–45)
| # | Etapa | Estado |
|---|---|---|
| 44 | Gráficos de evolução por turno | ✅ (painel: concordância/turno, acumulada, confiança/turno, faixas, evolução por IA) |
| 45 | Análise dos erros mais relevantes | 🟡 (categorias de menor concordância no painel; falta o resto) |

## Taxonomia, governança e síntese (etapas 46–50)
| # | Etapa | Estado |
|---|---|---|
| 46 | Revisão da taxonomia | ⬜ |
| 47 | Regras de revisão humana contínua | ⬜ |
| 48 | Matriz de evidências | ⬜ |
| 49 | Síntese metodológica | 🟡 (`CONTEXTO.md`) |
| 50 | Apresentação ao orientador | ⬜ |

---

# Atualizações solicitadas nos últimos dias (além do roteiro)

## Extensão A — Comparação MULTIMODELO das 7 IAs (out-of-fold)
Amplia a Etapa 15 (análise por executor/método) de LSTM/RF para **7 algoritmos**:
`naive_bayes, regressao_logistica, linear_svc, sgd, extra_trees, random_forest, lstm`.
- **Cada IA classifica TODA a base** na sua própria aba `CLASSIF__<modelo>`, com sua
  confiança, faixa, executor, calibração e reclassificação próprias.
- **Out-of-fold (sem vazamento)**: a IA que rotula a linha *i* nunca treinou na linha *i*
  (k-fold na materialização; top-up incremental depois). Essencial para a calibração
  honesta da Etapa 38 (critério dos ≥95%).
- **Lote dinâmico**: processa o que estiver pendente, mesmo < lote, até 1 chamado.
- **Estado**: ✅ 6 modelos leves materializados (13.825 cada, 0 pendentes, `kfold_5`);
  concordância vs histórico: linear_svc 80,3% > extra_trees 78,5% > sgd 77,5% >
  random_forest 76,8% > regressao_logistica 76,6% > naive_bayes 70,1%.
  ⏳ **LSTM** em materialização (7ª IA, para comparar TODOS juntos).
- **Painel**: aba **Multimodelo** com tabela de progresso + curva de evolução por IA.

## Extensão B — ANÁLISES ESTATÍSTICAS (a adicionar) ⬜
Além das métricas já previstas (concordância, F1, calibração/ECE, ganho líquido),
incorporar análise estatística formal aos resultados:
- **Correlação**: entre confiança e acerto; entre nº de chamados por categoria e
  concordância; entre comprimento/qualidade do texto e acerto (Pearson/Spearman).
- **Normalidade**: testar distribuição das métricas/erros (Shapiro–Wilk, D'Agostino,
  Kolmogorov–Smirnov; QQ-plots) para escolher testes paramétricos vs não-paramétricos.
- **Análise de resíduos**: resíduos de concordância por turno/categoria; homocedasticidade,
  autocorrelação (Durbin–Watson), tendência ao longo dos turnos.
- **Testes de significância entre modelos**: comparar as 7 IAs (McNemar par a par para
  classificadores; Cochran's Q / Friedman + pós-teste de Nemenyi entre os 7; intervalos
  de confiança por bootstrap da acurácia/F1).
- **Concordância entre avaliadores/fontes**: Kappa de Cohen (IA × histórico; IA × validação
  humana quando existir) e Kappa de Fleiss entre as IAs.
- **Tamanho de efeito e IC**: bootstrap dos indicadores (acurácia, F1, ECE) com IC 95%.
- **Saída**: tabelas/figuras publicáveis (ABNT) + JSON agregado p/ o painel (sem texto).

## Atualizações no PAINEL (feitas)
- Filtros: chips dos ativos, botões destacados, Limpar com contagem; **aparecem só nas
  abas onde funcionam** (Classificacao/Categorias/Metricas) e somem nas demais.
- A aba **Classificacao** agora tem seletor de fonte: **Multimodelo (7 IAs)** ou
  **Etapa 1 (LSTM)**. O dashboard publica `multimodelo_registros.json` agregado,
  sem texto de chamado, para permitir filtro por **Modelo** na propria Classificacao.
  Assim, o filtro deixa de ficar restrito a `LSTM`/`LSTM_BAIXA_CONF` quando a fonte
  multimodelo esta selecionada.
- Aba **Modelos**: média + ranking + evolução por lote (todos os recortes).
- Overflow horizontal corrigido.

> **Próximo do roteiro**: concluir o LSTM (Ext. A) → rodar Etapa 2 multimodelo →
> implementar a Extensão B (estatística) → quando liberado, validação humana (24–35) e
> métricas validadas (28, 36, 38–43).

## Atualizacao pos-Claude - 2026-06-05 13:48

- O run `27026916670` concluiu a materializacao do LSTM; a Extensao A agora tem as 7 IAs completas.
- Multimodelo atual: 13.825 registros por IA, 0 pendentes em cada modelo.
- Ranking vs historico: `linear_svc` 80,26%, `extra_trees` 78,47%, `sgd` 77,51%, `random_forest` 76,80%, `regressao_logistica` 76,59%, `naive_bayes` 70,07%, `lstm` 67,57%.
- A Extensao B foi iniciada e executada: `src/analise_estatistica.py` gerou `docs/dados/estatistica.json` com correlacao confianca x acerto, normalidade, residuos/tendencia, bootstrap IC 95%, Kappa, Cochran Q, McNemar e Friedman/Nemenyi.
- O dashboard ganhou aba `Estatistica` e o grafico de modelos ganhou seletor de metrica/acumulado.
- PDFs gerados: `docs/ESTADO_DO_ROTEIRO.pdf` e `docs/DOCUMENTACAO_MODELOS_E_ESTATISTICA.pdf`.
- A reclassificacao permanece sem prioridade ate concluir toda Etapa 1/multimodelo, estatistica e documentacao.
- Diagnostico de normalidade: a normalidade nao deve ser forcada nos modelos. Quando Shapiro rejeitar normalidade a 5%, usar testes nao parametricos, bootstrap e modelos apropriados para proporcoes.
