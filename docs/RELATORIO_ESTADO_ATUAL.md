# Relatório de estado atual — classificacao-chamados

> Revisão técnica e metodológica do repositório no contexto do doutorado
> (manutenção predial pública orientada por dados). Diagnóstico honesto:
> distingue o que foi **verificado** do que **não pôde** ser verificado.
> Data: 2026-06-10. Branch `main`, último commit observado `4d93f9a`.

## 0. Limitação de ambiente (declarada)

Esta revisão rodou **sem credenciais da conta de serviço** (`credenciais_sa.json`/
`SPREADSHEET_ID` ausentes) e **sem executar GitHub Actions**. Portanto:

- O **estado real das abas** da planilha (`CHAMADOS_ESQUELETO_REDUZIDO`, `CLASSIF__*`,
  `VALIDACAO_HUMANA`, etc.) **não pôde ser verificado** diretamente.
- Os números de concordância (ex.: `linear_svc` 80,26%) vêm dos JSON/docs do repositório,
  **não** foram recalculados aqui.
- Nenhum workflow foi disparado; os comandos `gh workflow run ...` ficam documentados,
  não executados.

O que **foi** verificado neste ambiente está marcado como ✅ abaixo.

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

- Conteúdo real das abas e dos JSON privados em `dados/` (gitignored).
- Execução dos workflows e dos `gh workflow run ...`.
- Se os números publicados batem com a planilha hoje (recálculo exigiria credenciais).

## 6. O que foi adicionado nesta revisão

- **`src/relevancia_termos.py`** — termos característicos por categoria (log-odds com prior
  de Dirichlet + peso TF-IDF) e **mapa de correlação** (cosseno entre centróides). Exploratório,
  dry-run por padrão, JSON sanitizados, não toca no histórico. Testado em corpus sintético ✅.
- **`docs/mapa_correlacao.html`** — visualizador (mapa de calor estilo geoprocessamento +
  termos por categoria). Renderização verificada ✅.
- **`.github/workflows/relevancia_termos.yml`** — workflow manual, `aplicar=false` por padrão.
- **`docs/RELEVANCIA_TERMOS.md`** e este relatório.

Detalhe e justificativa metodológica em [`RELEVANCIA_TERMOS.md`](RELEVANCIA_TERMOS.md).

## 7. Próximos passos pendentes (exigem o usuário / credenciais)

1. Rodar `relevancia_termos.yml` (dry-run) **com credenciais** para gerar os JSON reais e
   conferir os termos/mapa contra a planilha viva.
2. Cruzar o mapa de correlação com a **matriz de confusão IA×histórico** para priorizar a
   revisão da taxonomia (etapa 46).
3. Quando liberado pelo usuário: preencher M/N nos divergentes → métricas **validadas**,
   matriz de confusão validada, calibração definitiva, re-treino com base validada.
4. Housekeeping: remover Apps Script legado; manter `CONTEXTO.md` atualizado.

> **Conclusão honesta**: o repositório já estava metodologicamente sólido e alinhado às
> premissas do doutorado. Esta revisão **confirmou** a consistência (compilação, testes,
> workflows, separação de métricas, privacidade) e **acrescentou** a análise de vocabulário
> por categoria + mapa de correlação pedida, sem alterar dado bruto nem inflar resultados.
> O que falta é, sobretudo, **validação humana** — pendência deliberada do usuário — e a
> execução com credenciais reais, que este ambiente não permitiu.
