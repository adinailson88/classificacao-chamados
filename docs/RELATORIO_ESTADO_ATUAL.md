# Relatório de estado atual — classificacao-chamados

> Revisão técnica e metodológica do repositório no contexto do doutorado
> (manutenção predial pública orientada por dados). Diagnóstico honesto:
> distingue o que foi **verificado** do que **não pôde** ser verificado.
> Data: 2026-06-10 (atualizado na sessão da tarde). Branch `main`.

## 0. Limitação de ambiente (declarada)

A primeira revisão (manhã de 2026-06-10) rodou **sem credenciais da conta de serviço**
e **sem executar GitHub Actions**. Na sessão seguinte (tarde de 2026-06-10), com `gh`
autenticado e os secrets (`GCP_SA_KEY`, `SPREADSHEET_ID`) confirmados no repositório,
os workflows **foram executados de verdade** — ver §8. Permanece não verificado:

- O **estado real das abas privadas** da planilha (`CHAMADOS_ESQUELETO_REDUZIDO`,
  `CLASSIF__*`, etc.) — o acesso continua mediado pelos workflows, sem leitura direta.
- Recalcular localmente os números de concordância (ex.: `linear_svc` 80,26%); eles
  vêm dos JSON publicados pelos workflows.

O que **foi** verificado está marcado como ✅ abaixo.

## 1. O que existe (verificado ✅)

- **37 scripts** em `src/` — todos compilam (`python -m py_compile src/*.py` ✅).
- **20 workflows** em `.github/workflows/` — **todos** referenciam apenas scripts que
  existem em `src/` (sem caminho quebrado ✅).
- **Testes offline**: `tests/test_github_first.py` passa (4/4 ✅), cobrindo seleção de
  elegíveis, montagem G:J, rótulo de confiança e snapshot.
- **Pipeline multimodelo** (7 IAs) materializado, com predição **out-of-fold** (k-fold 5),
  uma aba por modelo — desenho correto contra vazamento.
- **Separação preliminar × validado já implementada**: `planilha.ler_conferencias`
  (colunas M/N/P), `calibracao.py` e `exportar_dashboard.py` distinguem concordância vs
  histórico de acerto validado por humano; `acerto_validado`/`acuracia_validada` só
  aparecem nos caminhos validados, hoje vazios (`validados=0`).
- **Validação não supervisionada** (`src/validacao_nao_supervisionada.py`) implementada:
  TF-IDF + SVD, centróides, distância à categoria, outliers, consenso multimodelo,
  prioridade de revisão — sem alterar o histórico. ✅ desenho coerente.
- **Camada estatística não paramétrica** (`src/analise_estatistica.py`): Spearman,
  Shapiro, McNemar, Cochran Q, Friedman/Nemenyi, Kappa, bootstrap.
- **Dashboard** estático em `docs/` consumindo JSON agregados (sem texto de chamado).
- **Privacidade**: `.gitignore` exclui credenciais, ID da planilha e JSON com texto;
  `comparacao_previsoes.json` é publicado em versão sanitizada. ✅ índice de `docs/index.html`
  não usa "Malha IA" como nome do projeto.

## 2. O que funciona (verificado ✅)

- Compilação de todo o `src/`; testes offline; integridade workflow→script.
- A **nova** ferramenta de termos/correlação (ver §6) foi testada sobre corpus sintético
  e o visualizador renderiza corretamente no navegador.

## 3. O que parece incompleto (não executável aqui)

- **Etapa 2 (reclassificação) não aplicada após o reset** — scripts prontos, dry-run
  registrado; ganho líquido marginal nos dry-runs (`FALTA_FAZER.md` P1).
- **Validação humana pausada** por decisão do usuário (`validados=0`): toda métrica atual
  é **preliminar vs histórico**, não validada. Estrutura (colunas M/N/P, `VALIDACAO_HUMANA`,
  `memoria_validada.py`) pronta, sem dados.
- **Calibração definitiva** (P3) depende de rótulos humanos; só há calibração preliminar.
- **Roteiro de 50 etapas**: etapas 35–36, 39, 41–42, 46–48, 50 pendentes (dependem de
  validação humana / decisão de taxonomia).

## 4. O que está errado / risco

- **Nenhuma inconsistência crítica encontrada** nesta revisão (caminhos, nomes de aba,
  separação de métricas e privacidade estão coerentes). O repositório já incorpora as
  premissas metodológicas centrais do pedido (histórico ≠ verdade final; métricas
  preliminares nomeadas como tal; sem escrita automática em dado bruto).
- **Risco de governança, não de código**: a conta autenticada neste ambiente
  (`adinailson88-jpg`) é **diferente** do dono do repositório (`adinailson88`). Push para
  `main` pode exigir a conta correta / permissão de colaborador.
- **Housekeeping pendente** (não bloqueante): `apps_script/Code.gs` legado ainda no repo;
  `CONTEXTO.md` a atualizar a cada correção.

## 5. O que não pôde ser verificado

- Conteúdo real das abas e dos JSON privados em `dados/` (gitignored) — o acesso
  segue mediado pelos workflows.
- Recálculo independente dos números publicados (exigiria ler a planilha diretamente).

> Atualização 2026-06-10 (tarde): a execução dos workflows **deixou** de ser uma
> limitação — `relevancia_termos.yml` e `validacao_nao_supervisionada.yml` foram
> disparados e acompanhados nesta sessão (ver §8).

## 6. O que foi adicionado nesta revisão

- **`src/relevancia_termos.py`** — termos característicos por categoria (log-odds com prior
  de Dirichlet + peso TF-IDF) e **mapa de correlação** (cosseno entre centróides). Exploratório,
  dry-run por padrão, JSON sanitizados, não toca no histórico. Testado em corpus sintético ✅.
- **`src/cruzamento_taxonomia.py`** — cruza a **matriz de confusão IA×histórico** com a
  correlação vocabular e ranqueia **candidatos a revisão de taxonomia** (pares confundidos E
  com vocabulário sobreposto). Testado: par sobreposto no topo, ruído zerado ✅.
- **`docs/mapa_correlacao.html`** — visualizador (mapa de calor estilo geoprocessamento +
  termos por categoria + tabela de candidatos a revisão). Renderização verificada ✅.
- **`.github/workflows/relevancia_termos.yml`** — workflow manual, `aplicar=false` por padrão,
  roda os dois scripts e commita os 4 JSON.
- **`docs/index.html`** (aba Documentação) — card "O que mudou" com todas as novidades +
  link para o mapa. Verificado no preview ✅.
- **`docs/RELEVANCIA_TERMOS.md`** e este relatório.

Detalhe e justificativa metodológica em [`RELEVANCIA_TERMOS.md`](RELEVANCIA_TERMOS.md).

## 7. Próximos passos pendentes (exigem o usuário / credenciais)

1. ~~Rodar `relevancia_termos.yml` (dry-run) com credenciais~~ ✅ feito em 10/06/2026
   (run `27298524010`) — ver §8.
2. ~~Cruzar o mapa de correlação com a matriz de confusão IA×histórico~~ ✅ os JSON reais
   do cruzamento estão publicados; a **decisão** de fusão/desambiguação de categorias
   segue pendente de revisão humana (etapa 46).
3. Quando liberado pelo usuário: preencher M/N nos divergentes → métricas **validadas**,
   matriz de confusão validada, calibração definitiva, re-treino com base validada.
4. Recalibrar os limiares de prioridade da validação não supervisionada (ver §8.2):
   com os critérios atuais, 62% da base cai em prioridade "Alta", o que esvazia a
   função de triagem.
5. Housekeeping: remover Apps Script legado; manter `CONTEXTO.md` atualizado.

## 8. Execução com credenciais reais (sessão de 2026-06-10, tarde)

### 8.1 Relevância de termos + correlação + cruzamento ✅

`relevancia_termos.yml` executado em dry-run (run `27298524010`, sucesso em 36s;
parâmetros `top_n=25`, `min_df=5`, `min_chamados_categoria=10`). Commit de dados
`6065597` publicou os 4 JSON em `docs/dados/` e o Pages atualizou
(run `27298562277`). Conferência de conteúdo:

- **44 categorias** com termos (das 54 do histórico; as demais ficaram abaixo de
  `min_chamados_categoria=10`), vocabulário TF-IDF de 8.933 termos.
- **Termos coerentes** com as categorias (ex.: `Climatização > Ar condicionado`,
  1.621 chamados → "ar condicionado", "gelando", "split", "gás", "parou funcionar").
  Saída sanitizada: apenas termos agregados com frequência ≥ 5, sem texto de chamado.
- **Pares mais próximos** plausíveis e dominados por duplicações estruturais da
  taxonomia: `Manutenção Preventiva > Hidráulica` × `... > Reservatório` (0,817);
  `Climatização > Ar condicionado` × `Manutenção Preventiva > Ar condicionado split`
  (0,647); `Telhados, calhas, rufos` duplicado em dois grupos; `Extintor` ×
  `Sistemas de combate a incêndio`.
- **Candidatos a revisão de taxonomia** (cruzamento confusão×vocabulário): topo =
  `Climatização > Ar condicionado` → `Manutenção Preventiva > Ar condicionado split`
  (confusão 22,7%, correlação 0,647, score 0,383). Leitura exploratória; a decisão
  é humana.
- **Aba Taxonomia do painel verificada** em servidor local com os dados reais:
  heatmap 44×44, 15 pares, 30 candidatos, termos clicáveis; sem erro de console.

### 8.2 Validação não supervisionada — primeira execução real ✅ (dry-run)

Os 5 disparos anteriores de `validacao_nao_supervisionada.yml` (09/06) **nunca
executaram**: ficaram presos na fila do grupo de concorrência `escrita-planilha`
(ocupado por runs longos) e foram cancelados — inclusive o de "1h34m", que era só
fila. Nesta sessão o run `27298888472` executou em ~35s (dry-run, sem escrita):

- `n_chamados=13.825`, `n_categorias=53`, representação `tfidf_svd_100`.
- **Qualidade de agrupamento fraca, como esperado** para 53 categorias textuais
  sobrepostas: silhouette **0,0972**, Davies-Bouldin 3,99, Calinski-Harabasz 128,2.
  Coerente com a sobreposição vocabular vista em §8.1.
- Prioridades de revisão: **Alta=8.589 (62%)**, Média=1.719, Baixa=3.517.
  ⚠️ O critério atual de "Alta" (consenso ≥6 modelos contra o histórico OU ≥2
  motivos) é largo demais — 62% da base em prioridade máxima não tria nada.
  Recomenda-se recalibrar (ex.: exigir consenso forte E margem semântica, ou
  ranquear por score contínuo em vez de 3 faixas) **antes** de usar como fila de
  validação humana. Nada foi gravado na planilha (`aplicar=false`).

> Nota metodológica: ambos os resultados são **exploratórios** e medidos contra a
> categoria histórica, que não é verdade absoluta. `validados=0` permanece.

### 8.3 Memória de decisão + primeira avaliação validada (sessão da noite) ✅

Implementadas as regras de memória pedidas pelo pesquisador: categoria conferida
como **errada** fica vetada para o chamado (a predição escolhe a melhor classe fora
do veto, com probabilidade renormalizada); categoria conferida como **certa** trava
a decisão e é reaproveitada sem reprocessar. Módulos novos: `decisao_validada.py`,
`avaliacao_final.py`, `analise_erros.py`; workflow `avaliacao_final.yml`; aba
`Decisão` no painel; 18 testes offline (todos passando).

Na primeira execução real (run `27300506477`), a planilha já tinha **354
conferências** (305 decisões travadas; 2 conflitos a revisar). Resultado **parcial**
(~2,2% da base, amostra possivelmente não aleatória):

- Ranking validado: `linear_svc` 67,9% [IC95 62,6–73,1] à frente, mas sem
  significância sobre a segunda (`regressao_logistica`, McNemar p=0,73).
- **Combinar IAs ainda não compensa**: nenhum ensemble supera a melhor IA isolada
  com significância (melhor delta +0,33 p.p., p=1,0).
- Análise de erros: nesta amostra, os erros têm títulos **mais longos** que os
  acertos (p=0,008) — a hipótese "texto pobre → erro" não se confirmou até aqui;
  a cobertura de termos discriminativos ainda não discrimina (p=0,17). Releitura
  obrigatória quando a conferência terminar.

`validados` deixou de ser 0 nesta data; as métricas validadas continuam
**parciais** até o fim da conferência manual.

> **Conclusão honesta**: o repositório já estava metodologicamente sólido e alinhado às
> premissas do doutorado. Esta revisão **confirmou** a consistência (compilação, testes,
> workflows, separação de métricas, privacidade), **acrescentou** a análise de vocabulário
> por categoria + mapa de correlação pedida e, na sessão da tarde, **executou** os
> workflows com as credenciais reais (§8), populando a aba Taxonomia com dados da
> planilha viva e rodando pela primeira vez a validação não supervisionada. O que falta
> é, sobretudo, **validação humana** — pendência deliberada do usuário — e a recalibração
> dos limiares de prioridade apontada em §8.2.

## 9. Revisao tecnica final antes de M/N/P (2026-06-11 11:50)

Revisao pontual executada sem mudar o desenho metodologico e sem escrever na planilha.

O que foi corrigido:

- `planilha.ler_conferencias` e `decisao_validada.carregar_decisoes` agora localizam C/G/O/M/N/P por cabecalho normalizado, com fallback para o layout atual.
- `src/auditar_conferencias.py` audita conferencias humanas, gera `docs/dados/auditoria_conferencias.json` sanitizado e so grava `AUDITORIA_CONFERENCIAS` com `--aplicar`.
- `.github/workflows/auditar_conferencias.yml` e `.github/workflows/check_final_ready.yml` foram adicionados.
- `src/check_final_ready.py` verifica arquivos, compilacao e JSONs publicos sem acessar texto de chamado.
- `reclassificar_validados.yml` ficou dry-run por padrao e exige `confirmacao=APLICAR_O` para gravar O.
- `classificacao_ia_2_dryrun.yml` explicita que nao grava O.
- `validacao_nao_supervisionada.py` passou a usar `score_prioridade_revisao` e prioridade Alta seletiva por percentil 85/top 15%.

Validacoes executadas:

- `git pull --rebase`: `Already up to date`.
- `python -m py_compile` dos arquivos alterados: OK.
- `python src/check_final_ready.py`: OK; compilou todo `src`, validou JSONs publicos e reportou `status=ok`.
- `python -m unittest discover -s tests -v`: OK com dependencias leves via `PYTHONPATH` para `.codex_deps`; 23 testes.
- Workflows referenciam scripts existentes.

Workflows/runs verificados:

- `avaliacao_final.yml`: sucesso `27300506477`; falha posterior `27301142348`.
- `dashboard.yml`: sucessos recentes; alguns `workflow_run` pulados.
- `multimodelo_reclassificacao.yml`: run pendente `27353706958`; run `27352686850` existe e esta cancelado. `gh run view 27352686850 --log` nao retornou log.
- `reclassificar_validados.yml`: ultimos sucessos observados em 06/06/2026.

Estado atual dos dados publicos: `avaliacao_final.json` esta com `status=ok`, `validados=305`, `conflitos=2` e `melhor_ia=linear_svc`. O proximo passo humano e revisar/concluir M/N/P, com atencao aos conflitos, antes de qualquer decisao de gravar a coluna O.
