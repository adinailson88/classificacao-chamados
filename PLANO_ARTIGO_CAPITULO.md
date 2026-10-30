# Plano — Artigo/Capítulo “Classificação Automática de Chamados”

Este documento registra somente a estrutura, os critérios editoriais e o estado atual do artigo/capítulo. O plano operacional vigente, os critérios de aceite e o ponto de continuidade estão em [`PLANO_EXECUCAO_ATUAL.md`](PLANO_EXECUCAO_ATUAL.md). Os dois documentos têm finalidades distintas e não devem acumular versões concorrentes do mesmo estado.

Atualizado em 30/10/2026, no fuso America/Bahia (atualização do artigo para a Trilha B).

## Regra de uso

Antes de alterar o artigo:

1. ler `CONTEXTO.md`, `PLANO_EXECUCAO_ATUAL.md`, este plano e `04_artigo/README.md`;
2. conferir os timestamps e denominadores dos JSONs utilizados;
3. não reaproveitar números de rodadas antigas sem revalidação;
4. ao concluir uma rodada, substituir a seção “Estado desta rodada”, sem acumular histórico;
5. não reescrever resultados ou conclusões antes do fechamento da nova execução canônica.

## Escopo científico

O artigo avalia a classificação automática de chamados de manutenção predial em português brasileiro como camada auditável de governança e estruturação de dados para modelagem preditiva da infraestrutura pública.

A análise distingue três objetos:

- concordância entre a classificação automática e a categoria administrativa histórica;
- acerto contra a referência humana revisada;
- reclassificação e identificação de problemas na taxonomia histórica.

O texto deve tratar a categoria histórica como registro administrativo sujeito a auditoria, não como referência definitiva. Também não deve afirmar que o estudo já realiza previsão de demanda, previsão de custos ou classificação de criticidade.

## Posicionamento vigente

A contribuição central é um protocolo auditável de classificação de chamados de manutenção predial, articulando governança de rótulo, inferência que respeita a dependência textual, calibração, automação seletiva por confiança e avaliação do risco de reclassificação. A comparação entre sete modelos é meio de prova do protocolo, e não a contribuição em si.

Título vigente:

> **Classificação auditável de chamados de manutenção predial: fluxo humano–IA, calibração e risco de reclassificação**

O título não deve sugerir previsão de demanda ou de custos, classificação de criticidade, anotação independente ou cega, validação temporal inexistente, nem enfatizar a comparação multimodelo a ponto de obscurecer a contribuição.

## Estrutura do artigo

1. Introdução.
2. Referencial conceitual.
3. Método.
4. Resultados.
5. Discussão e limitações.
6. Considerações finais.
7. Declarações e referências.

A fonte editável é `04_artigo/artigo_classificacao_chamados_v3.md`. O PDF publicado fica em `docs/artigo_classificacao_chamados.pdf`.

## Fontes canônicas

Todo artefato da rodada canônica carrega `hash_corpus = 1e476243…`. Quem não
carrega pertence ao painel ou ao snapshot legado e **não** deve alimentar o
artigo.

| Assunto | Fonte canônica |
|---|---|
| Plano operacional e ponto de continuidade | `PLANO_EXECUCAO_ATUAL.md` |
| Manifesto da rodada | `docs/dados/rodada_canonica.json` |
| Acurácia, macro-F1 e custo por modelo | `docs/dados/retreino_canonico.json` |
| Concordância histórica, Kappa, ganho líquido e dispersão | `docs/dados/comparacao_historica.json` |
| Calibração, ECE, Brier e automação seletiva | `docs/dados/calibracao_canonica.json` |
| Intervalos por modelo, consenso e pressupostos secundários | `docs/dados/inferencia_canonica.json` |
| Inferência pareada no nível do grupo textual, efeito de desenho, teste global e Holm | `docs/dados/inferencia_agrupada.json` |
| Cobertura e macro-F1 sob as três convenções de denominador | `docs/dados/sensibilidade_classes_raras.json` |
| Utilidade da reclassificação sob custos assimétricos | `docs/dados/utilidade_reclassificacao.json` |
| Recortes por tipo e curva ABC | `docs/dados/recortes_canonicos.json` |
| Camada de regras de periodicidade | `docs/dados/regras_versus_modelos.json` |
| Custo computacional | `docs/dados/custo_computacional_canonico.json` e `docs/dados/custo_bertimbau.json` |
| Corpus, taxonomia, grupos e partições | `auditoria_base_canonica.json`, `grupos_textuais.json` e `particoes_canonicas.json` |
| Tabelas do apêndice | `docs/dados/tabelas_apendice_canonicas.json` |
| Grupos com referência divergente e sua natureza | `docs/dados/grupos_divergentes_canonicos.json` |
| Disponibilidade de data de abertura no corpus | `docs/dados/disponibilidade_temporal.json` |
| Rastreabilidade e ressalvas | `docs/MATRIZ_PROVENIENCIA.md` e `docs/RASTREABILIDADE_LSTM.md` |

**Fontes que NÃO são do artigo.** `avaliacao_final.json`, `estatistica.json`,
`calibracao.json`, `calibracao_ajustada_modelos.json` e a família
`shannon_*.json` alimentam o painel e vêm da execução legada, com 14.058 a
14.082 linhas, oito modelos e verdade derivada de outro modo. Não carregam
`hash_corpus` e não podem ser citados no artigo.

## Critérios editoriais

- Toda afirmação teórica deve ter referência bibliográfica adequada.
- Datas de execução, IDs de workflow, caminhos internos e linguagem de relatório técnico não devem aparecer no corpo científico, salvo quando metodologicamente indispensáveis.
- O corpo científico deve descrever o procedimento de revisão humana, não as letras das colunas da planilha.
- Utilizar “referência humana revisada” ou “categoria de referência revisada”, evitando “verdade validada”, “verdade final” e “acerto validado”.
- Descrever a revisão humana como auditoria administrativa de rótulo por avaliador único; os 4,25% são taxa de alteração do rótulo histórico, nunca prevalência de erro.
- Resultados estatísticos detalhados devem permanecer em material suplementar quando não forem necessários à interpretação principal.
- Números repetidos no Resumo, Abstract, tabelas, figuras, resultados, discussão e conclusão devem ser atualizados em conjunto.
- O BERTimbau só integrará a comparação principal se utilizar o mesmo protocolo dos demais modelos; caso contrário, ficará como experimento exploratório no suplemento.
- O PDF deve ser regenerado e revisado visualmente após qualquer alteração estrutural ou numérica.
- A meta provisória é de 8 a 9 mil palavras, aproximadamente quatro figuras e quatro ou cinco tabelas principais, ajustável após a escolha do periódico.

## Estado desta rodada

**Rodada:** Trilha B, validação entre campi e em outra instituição (30/10/2026). O texto vigente do manuscrito é o Google Doc `ARTIGO (QUASE PRONTO)` (20/09/2026), na pasta do artigo no Drive, que não foi alterado; a cópia `ARTIGO (TRILHA B - RASCUNHO 2026-10-30)` recebeu 16 substituições como sugestões (denominadores, referência revisada, grupos, inferência por grupo e a descrição da revisão: segunda avaliação só nos 217 chamados pré-classificados, com acordo de 94,01% e kappa 0,935). O detalhe está em `TRILHA_B/MAPA_ATUALIZACAO_ARTIGO_TRILHA_B.md`, no Drive.

**Feito nesta rodada.** Modelos candidatos nas mesmas dobras (`alternativas.json`): tfidf_embedding 0,8307 e tfidf_caracteres 0,8280 contra 0,8241 do LinearSVC, ganho de 0,65 pp (p ajustado 0,009), sem ganho no teste prospectivo (0,7680 contra 0,7721); calibração deles em `calibracao_candidatos.json` (tfidf_embedding cobre 70,2% com acurácia seletiva de 0,949 ao alvo de 0,95). Transferência entre campi (`avaliacao_campi.json`): treino na Reitoria e teste nos demais dá 0,755 a 0,780 no LinearSVC; deixando um campus fora, 0,792 a 0,807. Validação em outra IFES com a base pública de requisições de manutenção da UFRN (`ufrn_resumo.json`, `ufrn_reverso.json`, `comparacao_direcoes_ufrn.json`): nossa taxonomia sobre a UFRN concorda 82% nas quatro divisões com correspondência (67% com o Viário); treino na UFRN classifica 83,6% da nossa base nas divisões equivalentes. A correspondência entre taxonomias é hipótese e depende da avaliação manual do autor, com as planilhas em `TRILHA_B` no Drive. A LSTM e o e5 isolado ficaram fora das direções com a UFRN (TensorFlow não importa na máquina local); o runner do GitHub não alcança `dados.ufrn.br`, então essas etapas rodam localmente.

**Fonte dos números.** Corte B, `hash_corte` `67812136fc0868862717280daeb85590d48d56779f4f5e4e28651920be6a57cb`, artefatos em `docs/dados/trilha_b/`. A execução canônica `1e476243` (14.060 e 13.972 linhas) continua congelada e descreve o texto antigo; os dois conjuntos não devem se misturar no mesmo manuscrito.

**Próximo passo.** (1) Avaliação manual do autor das duas planilhas da UFRN, depois a comparação entre a avaliação, o modelo e a divisão da UFRN. (2) Decidir o modelo principal (tfidf_embedding ou LinearSVC); regras de periodicidade, utilidade da reclassificação e recortes foram calculados só para os sete modelos originais. (3) Gerar os artefatos que faltam (concordância histórica e ganho líquido, utilidade, classes raras, custo, apêndice, ensemble, curva e ablation da LSTM, BERTimbau) e só então atualizar Tabelas 2 a 5, Resumo, Abstract, Discussão e Considerações Finais. (4) Buscar bases de outras IFES: UNEB (Central de Serviços), UFPB (SIPAC, cerca de 6.800 requisições), Ifes Vitória (2.232 chamados), UFERSA (auditoria), UFRB (SIPAC). Decisões do autor pendentes: modelo principal, limitação temporal reescrita como resultado, categoria Elevador preventivo fora das partições, correspondência entre taxonomias.

## Critérios para novo fechamento científico

A nova rodada científica somente poderá ser considerada fechada quando:

1. corpus, referência e taxonomia estiverem congelados e reconciliados;
2. grupos e partições canônicas estiverem salvos e reproduzíveis;
3. os sete modelos tiverem predições *out-of-fold* sob o mesmo protocolo agrupado;
4. a camada de regras preventivas tiver comparação pareada com os modelos puros;
5. o BERTimbau estiver no mesmo protocolo ou explicitamente classificado como exploratório;
6. calibração, intervalos e testes estatísticos derivarem da mesma execução;
7. a segunda avaliação, restrita aos 217 chamados pré-classificados, e a ausência dela no restante do corpus estiverem declaradas no texto, com a limitação correspondente;
8. cada número, tabela e figura tiver proveniência rastreável;
9. Resumo, Abstract, tabelas, figuras, discussão e conclusões estiverem coerentes;
10. o PDF final tiver sido gerado e revisado visualmente;
11. o alcance temporal estiver declarado, com avaliação em períodos sucessivos executada ou limitação explícita, e nenhuma afirmação prospectiva excedendo a evidência disponível.

## Registro histórico

Planos concluídos, auditorias antigas, números substituídos e decisões de implementação devem ser consultados no histórico do Git e nos Pull Requests. Eles não devem voltar a ser acumulados neste arquivo.
