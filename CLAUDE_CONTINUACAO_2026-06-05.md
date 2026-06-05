# Continuidade para Claude — classificacao-chamados

Data de referencia: 05/06/2026, horario America/Bahia.

## Objetivo do usuario

O usuario quer chegar a um modelo/rotina de IA capaz de indicar, com confianca minima alvo de 95%, se a categoria historica de um chamado esta correta ou nao, antes de iniciar validacao humana manual.

A validacao humana NAO deve ser iniciada agora. O foco atual e fortalecer scripts, comparacoes, dashboard, memoria e reclassificacao automatica.

## Repositorio e site

- Repo: `https://github.com/adinailson88/classificacao-chamados`
- Branch: `main`
- Site: `https://adinailson88.github.io/classificacao-chamados/`
- Dashboard estatico: `docs/index.html`
- Dados publicos do dashboard: `docs/dados/*.json`
- Documento principal de contexto: `CONTEXTO.md`

## Estado atual publicado no dashboard

Dados observados em `docs/dados/resumo.json` apos pull do remoto:

- `gerado_em`: `05/06/2026 11:55`
- `log_turnos_classificacao`: `540`
- `registros`: `8100`
- `metricas_por_categoria`: `49`
- `comparacao_modelos`: `35`
- `log_turnos_reclassificacao`: `0`
- calibracao total: `8100`
- `ece_historico`: `0.0537`
- `validados`: `0`

Dados observados em `docs/dados/metricas_experimento.json`:

- concordancia acumulada global vs historico: `0.7765`
- processados acumulado: `8100`
- pendentes restantes: `5725`
- modelo da Etapa 1: `LSTM_Bidirecional`
- ultimo lote acima de 95%: `267`, concordancia vs historico `0.9925`
- ultimo lote entre 70% e 95%: `276`, concordancia vs historico `0.942`
- ultimo lote abaixo de 70%: `357`, concordancia vs historico `0.4034`

Importante: esses acertos sao comparacao contra categoria historica, nao contra validacao humana.

## O que ja foi feito

1. Reset completo do experimento.
   - Limpou `CHAMADOS_ESQUELETO_REDUZIDO!G:K`.
   - Preservou categoria historica, formula descritiva e conferencia manual.
   - Limpou logs, metricas, comparacoes e abas multimodelo.
   - `src/resetar_experimento.py` passou a limpar tambem abas `CLASSIF__*`, `RECLASS__*` e `MULTIMODELO_*`.

2. Treino/reclassificacao conferidos.
   - O texto de classificacao usa B, D, E e F da aba `CHAMADOS_ESQUELETO_REDUZIDO`.
   - A coluna `titulo` em `LOG_LINHA_A_LINHA` e apenas resumo/auditoria; nao significa que o treino use so titulo.

3. LSTM e memoria.
   - `src/modelo_lstm.py` tem perfil `padrao` e perfil `robusto`.
   - `config_experimento.json` documenta `modelo_ia`, `objetivo_final` e `memoria_validada`.
   - `src/memoria_validada.py` le `VALIDACAO_HUMANA` quando houver linhas com `usar_para_treino=SIM`.
   - Sem validacao humana, a memoria validada fica vazia.

4. Dashboard automatico.
   - `.github/workflows/dashboard.yml` roda por agenda, por disparo manual e por `workflow_run` apos workflows principais.
   - Foi adicionada retentativa em `src/exportar_dashboard.py` para falhas transitorias de Google Sheets, incluindo quota 429.
   - O dashboard enfileira execucoes e nao cancela execucao em curso.

5. Comparacao de modelos.
   - Foram publicados 5 recortes completos de 200 registros:
     - `0-200`
     - `200-400`
     - `400-600`
     - `600-800`
     - `800-1000`
   - Cada recorte tem 7 modelos:
     - `naive_bayes`
     - `regressao_logistica`
     - `linear_svc`
     - `sgd`
     - `extra_trees`
     - `random_forest`
     - `lstm`
   - Total publicado em `comparacao_modelos.json`: 35 linhas.

## Resultado comparativo observado

Media dos 5 recortes de `docs/dados/comparacao_modelos.json`:

| Modelo | Lotes | Acuracia media | F1-macro media | Melhor acuracia |
|---|---:|---:|---:|---:|
| linear_svc | 5 | 0.6670 | 0.3450 | 0.7350 |
| regressao_logistica | 5 | 0.6270 | 0.3410 | 0.7150 |
| sgd | 5 | 0.6270 | 0.3262 | 0.7050 |
| extra_trees | 5 | 0.6210 | 0.3061 | 0.7050 |
| random_forest | 5 | 0.6130 | 0.3213 | 0.6800 |
| naive_bayes | 5 | 0.5650 | 0.2083 | 0.6450 |
| lstm | 5 | 0.4990 | 0.1944 | 0.5300 |

Leitura objetiva: nos recortes comparados ate agora, o LSTM nao esta competitivo. Os modelos TF-IDF lineares estao superiores para comparacao contra categoria historica.

## Falha recente que deve ser corrigida

Run manual `27001950857` da Etapa 1 falhou antes de executar o script.

Causa observada no log:

- `pip` falhou baixando `tensorflow==2.17.0`.
- Erro: `IncompleteRead(... bytes read, ... more expected)`.
- Exit code: `2`.

Isso nao e erro de classificacao. E falha de instalacao/download. Execucoes agendadas posteriores rodaram com sucesso e o dashboard avancou para 8.100 registros.

Correcao recomendada:

1. Adicionar cache de pip nos workflows com `actions/setup-python`:
   - `cache: pip`
   - `cache-dependency-path: requirements.txt`
2. Separar dependencias leves e TensorFlow onde possivel.
3. Na Etapa 1, considerar retry de instalacao:
   - `python -m pip install --retries 5 --timeout 120 -r requirements.txt`
4. Se o objetivo for reduzir falhas por TensorFlow, criar workflow leve com baseline/linear para comparacoes e deixar TensorFlow apenas para LSTM.

## Problema percebido no dashboard

O usuario percebeu que o dashboard nao esta mostrando o que deveria mostrar. A analise do HTML/JSON confirma pontos provaveis:

1. Aba `Modelos` nao mostra uma visao consolidada por modelo.
   - O grafico `cModelos` usa apenas a ultima execucao de cada modelo:
     - no codigo: `const ult={}; rows.forEach(r=>{ ult[r.modelo]=r; });`
   - Isso apaga visualmente os 5 recortes e pode dar a impressao de que a comparacao esta incompleta.
   - Deve mostrar:
     - media por modelo;
     - melhor/pior por modelo;
     - evolucao por lote;
     - tabela com todos os recortes.

2. Dashboard nao exporta nem mostra dados multimodelo.
   - Existem scripts e abas para:
     - `CLASSIF__<modelo>`
     - `RECLASS__<modelo>`
     - `MULTIMODELO_TURNOS`
     - `MULTIMODELO_METRICAS`
     - `MULTIMODELO_RECLASS_TURNOS`
   - `src/exportar_dashboard.py` nao exporta essas abas.
   - `docs/index.html` nao tem aba especifica para multimodelo materializado.

3. Dashboard nao mostra `COMPARACAO_CATEGORIA` nem `COMPARACAO_PREVISOES`.
   - O workflow `comparar_modelos_lote.py` grava essas abas.
   - O exportador so publica `comparacao_modelos.json`.
   - Faltam:
     - comparacao por categoria;
     - exemplos/contagens de previsoes divergentes;
     - categorias onde cada modelo erra mais.

4. A aba `Reclassificacao` esta vazia por desenho atual.
   - `log_turnos_reclassificacao=0`.
   - Isso precisa ficar mais explicito no dashboard: nao e erro visual, a Etapa 2 ainda nao foi aplicada apos o reset.

5. O dashboard mistura "acerto/concordancia contra historico" com linguagem que pode parecer validacao real.
   - Deve deixar mais visivel:
     - `validados=0`;
     - `acerto_validado=null`;
     - toda metrica atual e preliminar contra historico.

6. O dashboard nao evidencia a meta de 95% corretamente.
   - Atualmente mostra que a faixa `>=95%` tem alta concordancia contra historico.
   - Mas nao mostra uma decisao clara:
     - "aprovado contra historico";
     - "nao validado humanamente";
     - "ainda nao liberado para producao".

7. Os filtros nao afetam todos os graficos.
   - Pelo texto atual, series temporais e reclassificacao nao usam filtros.
   - Isso pode ser aceitavel, mas precisa estar visualmente claro no topo de cada aba.

## Correcoes prioritarias para Claude

1. Corrigir a aba `Modelos`.
   - Trocar grafico atual por:
     - barras de media de acuracia e F1-macro por modelo;
     - linha por lote ou grafico agrupado por lote;
     - ranking dos modelos por media;
     - destaque do melhor modelo atual.
   - Nao usar apenas a ultima execucao por modelo.

2. Exportar mais JSONs no dashboard.
   - Em `src/exportar_dashboard.py`, adicionar:
     - `comparacao_categoria.json`
     - `comparacao_previsoes.json`
     - `multimodelo_turnos.json`
     - `multimodelo_metricas.json`
     - `multimodelo_reclass_turnos.json`
   - Se as abas nao existirem ou estiverem vazias, exportar `[]`.

3. Criar uma aba `Multimodelo` no dashboard.
   - Mostrar progresso por modelo.
   - Mostrar acuracia/concordancia por modelo materializado.
   - Mostrar pendentes por modelo.
   - Mostrar dados de reclassificacao multimodelo quando existirem.

4. Melhorar a aba `Metricas`.
   - Separar:
     - metricas contra historico;
     - metricas validadas;
     - calibracao;
     - pendentes;
     - meta 95%.
   - Incluir aviso grande quando `validados=0`.

5. Melhorar a aba `Reclassificacao`.
   - Exibir estado vazio com chamada objetiva:
     - "Etapa 2 ainda nao executada apos reset".
     - "Nao iniciar validacao humana ainda".
     - "Proximo passo tecnico: dry-run ou aplicacao controlada da reclassificacao".

6. Robustecer workflows.
   - Adicionar cache/retry de pip.
   - Evitar que download do TensorFlow derrube execucoes manuais.
   - Considerar separar workflow LSTM de workflow leve.

7. Atualizar `CONTEXTO.md` apos cada correcao.
   - Sempre registrar:
     - o que foi alterado;
     - workflow/run ID;
     - estado dos JSONs;
     - pendencias.

## Comandos uteis

Checar estado:

```powershell
git pull --rebase
gh run list --repo adinailson88/classificacao-chamados --limit 20
Get-Content -LiteralPath docs\dados\resumo.json
Get-Content -LiteralPath docs\dados\metricas_experimento.json
```

Validar Python:

```powershell
python -m py_compile src\exportar_dashboard.py src\resetar_experimento.py src\executar_etapa1.py
```

Rodar dashboard localmente, se necessario:

```powershell
python -m http.server 8000 -d docs
```

Disparar dashboard:

```powershell
gh workflow run dashboard.yml --repo adinailson88/classificacao-chamados
```

Comparar proximo recorte leve:

```powershell
gh workflow run comparar_modelos.yml --repo adinailson88/classificacao-chamados -f modelo=todos -f inicio=1000 -f limite=200
```

Comparar LSTM no mesmo recorte:

```powershell
gh workflow run comparar_modelos.yml --repo adinailson88/classificacao-chamados -f modelo=lstm -f inicio=1000 -f limite=200
```

## Proximo passo recomendado

Antes de disparar mais execucoes, corrigir o dashboard. O usuario ja percebeu que ele nao mostra o que deveria. A prioridade nao e processar mais registros agora; e fazer o painel refletir corretamente:

1. classificacao progressiva;
2. comparacao consolidada de modelos;
3. calibracao contra historico versus validacao humana;
4. multimodelo;
5. pendencias e proximos passos.
