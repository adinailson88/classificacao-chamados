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

**Rodada:** Trilha B, texto de trabalho no Google Doc `ARTIGO (TRILHA B - VERSÃO DE TRABALHO 2026-10-30)` (copia do rascunho, editada direto; o original `ARTIGO (QUASE PRONTO)` segue intacto). Modelo principal: `tfidf_embedding` (acurácia 0,8307; +0,65 pp sobre o LinearSVC, significativo e pequeno). Corte B: 14.559 chamados, 14.357 avaliados, 39 categorias, 10.596 grupos, 10 modelos.

**Feito no Doc:** Método 3.1 a 3.5 reescrito para o corte B (corpus, referência, 217 pré-triados, 10 modelos, denominadores, validação temporal e entre campi); novas 3.6 (controle de risco) e 3.7 (validação na UFRN, amostragem aleatória, protocolo cego em duas etapas, segunda avaliação); Resultados 4.1 e Tabelas 1 a 4 atualizadas com os 10 modelos; novas 4.6 (controle de risco, 14 cenários) e 4.7 (UFRN, kappa 0,70 e 0,52); Resumo e Abstract; referências Angelopoulos, Clopper e Pearson, Cohen e UFRN. Removidos por falta de reexecução no corte B: BERTimbau, análise de ensemble/stacking (Tabela 5), sensibilidade de denominador e Figura 2.

**Falta no Doc:** texto de 4.2 a 4.5 (ainda com números do corte antigo, embora os dados de B existam em `comparacao_historica.json`, `utilidade_reclassificacao.json`, `calibracao*.json`, `recortes.json`, `regras_versus_modelos.json`); Tabela 5 e parágrafos de ensemble em 4.5; Introdução e 2.x; Discussão 5.1 a 5.4 (5.3 ainda diz que não há data de abertura); Considerações Finais; 3.8 (reprodutibilidade, ambiente); Apêndice A (Tabelas A1 a A3 com categorias do corte antigo); figuras 2 a 4 a regerar; citar Khalid, Chen, Wang, Sammani e Lutz; tradução para inglês.

**Números-chave de B:** controle de risco (`controle_risco.json`): meta 10% sem violação em 14 cenários, cobertura 42 a 68%; limiar ingênuo excede em 2024 e 2026. Meta 5%: certificado em 3 de 14. UFRN (`avaliacao_cruzada_manual.json`): 73,3% e 84,0% (modelo principal), segunda avaliação kappa 0,70 e 0,52. LAI: pedidos de 30/10/2026, prazo 23/11/2026 (Ifes, UFPB, UFRB, UFERSA, UFS).

**Próximo passo.** (1) Reescrever 4.2 a 4.5 com os JSON de B e remover a Tabela 5. (2) Atualizar Introdução, 2.x, Discussão e Considerações Finais, citando as cinco referências novas. (3) Estimar a correção por erro de rótulo e repetir o controle de risco com o linear_svc. (4) Regerar figuras e o Apêndice A. (5) Revisar com base nas bases que chegarem por LAI. Decisões do autor pendentes: revista-alvo (Journal of Facilities Management, Automation in Construction, Advanced Engineering Informatics ou Journal of Building Engineering, rota gratuita), tradução, categoria Elevador preventivo fora das partições.

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
