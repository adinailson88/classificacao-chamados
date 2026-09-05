# Classificação de Chamados

> ## [PLANO ATUAL E PONTO DE CONTINUIDADE](PLANO_EXECUCAO_ATUAL.md)
>
> **Leia este documento antes de alterar código, resultados ou artigo.** Ele registra por que a execução experimental precisa ser refeita, quais decisões científicas já foram aprovadas, o estado de cada passo e como outro agente deve continuar sem perder contexto.

## [Abrir o artigo em PDF](https://adinailson88.github.io/classificacao-chamados/artigo_classificacao_chamados.pdf)

[Visualizar o painel](https://adinailson88.github.io/classificacao-chamados/) · [Acompanhar workflows](https://github.com/adinailson88/classificacao-chamados/actions) · [Abrir o texto-fonte do artigo](04_artigo/artigo_classificacao_chamados_v3.md)

Repositório experimental para classificação e reclassificação automática de chamados de manutenção predial, com validação humana, comparação de modelos e publicação de resultados em painel e artigo científico.

## Objetivo do projeto

O projeto avalia modelos de aprendizagem de máquina para apoiar a classificação de chamados de manutenção predial. O experimento mantém separadas três dimensões:

- classificação em relação ao histórico administrativo;
- acerto em relação à decisão validada por conferência humana;
- reclassificação e potencial correção da taxonomia histórica.

Os resultados alimentam o painel público e o artigo/capítulo da tese em Biossistemas Construídos.

## Componentes principais

| Componente | Local |
|---|---|
| Plano atual e ponto de continuidade | [`PLANO_EXECUCAO_ATUAL.md`](PLANO_EXECUCAO_ATUAL.md) |
| Artigo em Markdown | [`04_artigo/artigo_classificacao_chamados_v3.md`](04_artigo/artigo_classificacao_chamados_v3.md) |
| Artigo em PDF | [`docs/artigo_classificacao_chamados.pdf`](docs/artigo_classificacao_chamados.pdf) |
| Painel público | [`docs/index.html`](docs/index.html) |
| Dados agregados | [`docs/dados/`](docs/dados/) |
| Plano editorial do artigo | [`PLANO_ARTIGO_CAPITULO.md`](PLANO_ARTIGO_CAPITULO.md) |
| Guia de reprodutibilidade (planilha → scripts → artigo) | [`docs/GUIA_REPRODUTIBILIDADE.md`](docs/GUIA_REPRODUTIBILIDADE.md) |
| Contexto técnico atual | [`CONTEXTO.md`](CONTEXTO.md) |
| Regras do repositório | [`AGENTS.md`](AGENTS.md) |
| Governança final do repositório (writers, proteção de `main`, três domínios de dados) | [`docs/GOVERNANCA_FINAL_REPOSITORIO.md`](docs/GOVERNANCA_FINAL_REPOSITORIO.md) |
| Código do experimento | [`src/`](src/) |
| Testes | [`tests/`](tests/) |

## Workflows principais

| Workflow | Função |
|---|---|
| `transformer_ft.yml` | Fine-tuning e avaliação controlada do BERTimbau |
| `avaliacao_final.yml` | Acerto validado, intervalos e análise de erros |
| `estatistica.yml` | Estatísticas e comparações entre modelos |
| `consolidar_validacao.yml` | Consolidação M/N/P/Q; cron em dry-run e aplicação somente manual |
| `sincronizar_correcoes_glpi.yml` | Dry-run e sincronização controlada das categorias aprovadas com o GLPI |
| `dashboard.yml` | Atualização do painel e dos dados publicados |
| `artigo_pdf.yml` | Geração do PDF a partir do Markdown |

A execução do BERTimbau não possui mais orquestrador temporário. Treino, verificação dos artefatos e etapas posteriores devem ser executados e conferidos separadamente.

## Regras operacionais

1. Alterações de código e documentação devem ser feitas em branch e Pull Request.
2. Escritas na planilha exigem opção explícita de aplicação e, quando cabível, dry-run anterior.
3. As colunas de conferência humana devem ser preservadas, especialmente M, N, P e Q.
4. Resultados do artigo devem ser conferidos nos JSONs vigentes antes de qualquer atualização textual.
5. O histórico detalhado das rodadas não deve ser acumulado neste README; deve permanecer em `CONTEXTO.md`, `PLANO_ARTIGO_CAPITULO.md`, commits e Pull Requests.

## Autoria e contexto

Pesquisa de Adinailson Guimarães de Oliveira, doutorando no Programa de Pós-Graduação em Biossistemas Construídos da Universidade Federal do Sul da Bahia, com aplicação em manutenção predial orientada por dados e governança preditiva da infraestrutura pública.
