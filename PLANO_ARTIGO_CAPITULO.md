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

**Feito no Doc:** corpo do artigo reescrito para o corte B: Resumo, Abstract, Introdução (seis elementos, 10 modelos), 2.1 (cinco referências novas) a 2.4, Método 3.1 a 3.8 (novas 3.6 controle de risco e 3.7 validação na UFRN), Resultados 4.1 a 4.8 (novas 4.6 controle de risco, 4.7 UFRN com kappa, 4.8 temporal e entre campi), Tabelas 1 a 4, Discussão 5.1 a 5.4 e Considerações Finais. Referências acrescentadas: Angelopoulos, Clopper e Pearson, Cohen, UFRN, Chen, Khalid, Lutz, Sammani, Wang. Removidos por falta de reexecução no corte B: BERTimbau, ensemble/stacking (Tabela 5), sensibilidade de denominador, vocabulário por categoria e as Figuras 2 a 7.

**Feito nesta rodada:** Apêndice A refeito para o corte B (A1 a A3, conferido célula a célula; A4 e A5 removidas por serem do corpus vivo). Figuras 2 a 4 (`src/figuras_trilha_b.py`), figuras de pesos por categoria 5 (`src/figuras_pesos_trilha_b.py`, sete páginas, termos revisados) e esquemas 6 a 9 (`src/figuras_esquemas_trilha_b.py`: estrutura do modelo, tokens, cálculo da categoria, ciclo de aprendizado) em `docs/trilha_b/figuras/`. No Doc de trabalho já estão, com legenda e citação no texto, a Figura 2 (estrutura do modelo, 3.3), 3 (ciclo, 3.9), 4 (custo × acurácia, 4.1), 5 (confiabilidade, 4.3) e 6 (controle de risco, 4.6), inseridas pela URL do GitHub; ficaram de fora as de pesos (5) e os esquemas 7 e 8. Simulação cronológica de aprendizado contínuo (`src/aprendizado_continuo.py`; `docs/dados/trilha_b/aprendizado_continuo*.json`; linear_svc, treino até 2021, 20 trimestres, 7.691 chamados): estático 0,7673 (cai de 0,81 em 2022 a 0,70 em 2026); só auditoria aleatória de 100 por trimestre 0,7977 (+3,0 pontos, IC95% [1,45; 4,86], melhor em 15 de 20 trimestres), cerca de 70% do ganho de 0,8109 com tudo confirmado; revisões extras acrescentam 0,3 a 0,9 ponto; ativo × aleatório: +0,3, +0,7 e +0,3 ponto com 20, 40 e 100 revisões, só o de 40 exclui o zero. Teste de LLM zero-shot local (qwen2.5:7b, 100 chamados de baixa confiança) deu 34% contra 61% do modelo; GitHub Models não respondeu do runner; não entra no artigo. No Doc de trabalho: resumo reescrito (mais curto, sem dois-pontos, com a simulação), nova 3.9 (método da simulação), nova 4.9 (resultados), nova 5.5 (contribuição de cada etapa do protocolo, a partir de resultados já existentes, sem ablação experimental) e uma frase nas Considerações Finais. Revisão a partir da avaliação por revisor (nota estimada 5,5): resumo e Abstract reescritos com a validação prospectiva em destaque (0,7680, vantagem sobre o LinearSVC desaparece) e "controle de risco" no lugar de "garantia"; nota em 3.6 de que a garantia vale sob trocabilidade e sob deriva é verificada empiricamente; meta de 10% qualificada em 4.6; achado novo em 4.4 (fusão dos sete pares de mesmo nome eleva a acurácia de 0,8307 a 0,8380 e remove 105 de 2.431 erros, 4,3%, de modo que a duplicação taxonômica é fonte menor); teste exploratório de LLM local em 2.4; declaração de dados e código em 3.8; candidato a piloto em 6 passa a citar o LinearSVC; períodos longos da Introdução e de 3.4 desmembrados. Em andamento ou pendente de pessoa: BERTimbau ajustado nas mesmas dobras (`src/bertimbau_corte_b.py`, roda em CPU, retomável, perto de 1,5 a 2 horas por dobra; pode ir ao Colab) e segunda avaliação cega de 300 chamados (`src/segunda_avaliacao.py`, excluídos os 222 chamados pré-triados; planilha e chave em `TRILHA_B/SEGUNDA_AVALIACAO` no Drive; a chave não deve ser aberta pelo avaliador).

**Falta no Doc:** decidir e inserir as figuras de pesos por categoria (quais das sete páginas ao corpo) e os esquemas de tokens e de cálculo (apêndice), com legendas (Figuras 7 e 8 ilustrativas); seção 5.4 e Figura 1 conferidas apenas por varredura de números; ordem alfabética e ABNT das referências; arXiv do Angelopoulos; atualizar o Abstract e traduzir para inglês; revisão estilística final com `meu-estilo-textual`.

**Números-chave de B:** controle de risco (`controle_risco.json`): meta 10% sem violação em 14 cenários, cobertura 42 a 68%; limiar ingênuo excede em 2024 e 2026. Meta 5%: certificado em 3 de 14. UFRN (`avaliacao_cruzada_manual.json`): 73,3% e 84,0% (modelo principal), segunda avaliação kappa 0,70 e 0,52. LAI: pedidos de 30/10/2026, prazo 23/11/2026 (Ifes, UFPB, UFRB, UFERSA, UFS).

**Divisão em capítulo e artigo (02/11/2026).** O Doc de trabalho foi renomeado `RASCUNHO - CAPITULO 2` (texto integral, cerca de 13.100 palavras, preservado). A cópia `ARTIGO - CORTES PROPOSTOS` traz 2.709 palavras de cortes como sugestões do Docs (2.4, parte da 3.8, 3.9 e 4.9 com a Figura 3, partes da 4.4, 4.5 inteira, 5.4 e 5.5, trechos das Considerações Finais); restam cerca de 10.400 palavras, e a meta de 7.500 a 8.500 exige ainda condensar Introdução, 2.1 a 2.3, 3.1 a 3.4, 4.1 a 4.3 e 5.1 a 5.3. Revista-alvo ainda por decidir (ver análise na conversa); depois dela, ajustar o layout.

**Artigo para a RAP (02/11/2026).** Revistas-alvo sem taxa: Revista de Administração Pública (primeira) e Cadernos EBAPE.BR (segunda); ambas pedem 6.000 a 8.000 palavras contando tudo, APA 7, revisão duplo-cega, resumo de até 250 palavras. Texto-fonte em `docs/trilha_b/artigo_rap/artigo_rap.txt` (marcadores simples) e gerador em `src/gerar_docx_artigo_rap.py`; saída `ARTIGO_RAP.docx` na pasta do Drive (6.003 palavras, A4, TNR 12, espaçamento 1,5, 3 tabelas). Eixo: auditoria do rótulo, triagem em vez de reescrita, controle de risco e segunda avaliação cega; aprendizado contínuo ficou para um segundo artigo. Segunda versão (02/11/2026): título novo, subseções 2.2 e 3.1, apêndice estatístico, referências brasileiras da RAP, discussão com rotina prática; 7.330 palavras. Lista de downloads e itens a confirmar em `docs/trilha_b/artigo_rap/REFERENCIAS_PARA_BAIXAR.md`. Pendências: conferir limites e modelo no site da RAP; anonimizar propriedades do arquivo antes de submeter.

**Próximo passo.** (0) BERTimbau já no Doc (2.4, 4.1, 5.1; acurácia 0,8151, macro-F1 0,6419, 1,56 pp abaixo do tfidf_embedding, IC 1,09 a 2,08; `bertimbau_comparacao.json`), avaliado à parte, fora da Tabela 2 e dos testes dos dez modelos; (a segunda avaliação cega já está no Doc: 3.1, 4.2, 5.3, 5.5 e resumo; concordância ponderada com a referência 81,7%, com o histórico 78,9%, kappa 0,64 na amostra estratificada; resultado em `segunda_avaliacao.json`; avaliador da mesma unidade, ressalva declarada). (1) Decidir as figuras de pesos e os esquemas restantes. (2) Testar auditorias menores que 100 por trimestre e repetir a simulação com o tfidf_embedding; estimar a correção por erro de rótulo; repetir o controle de risco com o linear_svc e a transferência entre campi com o tfidf_embedding. (3) Ablação experimental do protocolo, se a revista exigir. (4) Avaliar as bases que chegarem por LAI (prazo 23/11/2026) com o mesmo protocolo da UFRN. (5) Referências conferidas (ordem alfabética, todas as citações com entrada, Angelopoulos com arXiv:2110.01052 verificado) e varredura de estilo sem travessão nem frases de remate; resta a leitura final do texto inteiro com `meu-estilo-textual` e a conferência visual do Doc. Decisões do autor pendentes: revista-alvo com rota gratuita (Journal of Facilities Management, Automation in Construction, Advanced Engineering Informatics ou Journal of Building Engineering), categoria Elevador preventivo fora das partições.

## Critérios para novo fechamento científico

A nova rodada científica somente poderá ser considerada fechada quando:

1. corpus, referência e taxonomia estiverem congelados e reconciliados;
2. grupos e partições canônicas estiverem salvos e reproduzíveis;
3. os sete modelos tiverem predições *out-of-fold* sob o mesmo protocolo agrupado;
4. a camada de regras preventivas tiver comparação pareada com os modelos puros;
5. o BERTimbau estiver no mesmo protocolo ou explicitamente classificado como exploratório;
6. calibração, intervalos e testes estatísticos derivarem da mesma execução;
7. a segunda avaliação (217 pré-triados ancorados e 300 chamados cegos estratificados) e a ausência dela no restante do corpus estiverem declaradas no texto, com a limitação correspondente;
8. cada número, tabela e figura tiver proveniência rastreável;
9. Resumo, Abstract, tabelas, figuras, discussão e conclusões estiverem coerentes;
10. o PDF final tiver sido gerado e revisado visualmente;
11. o alcance temporal estiver declarado, com avaliação em períodos sucessivos executada ou limitação explícita, e nenhuma afirmação prospectiva excedendo a evidência disponível.

## Registro histórico

Planos concluídos, auditorias antigas, números substituídos e decisões de implementação devem ser consultados no histórico do Git e nos Pull Requests. Eles não devem voltar a ser acumulados neste arquivo.
