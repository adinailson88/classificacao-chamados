# PLANO ATUAL — REFORMULAÇÃO CIENTÍFICA E EXECUÇÃO CANÔNICA

> **LEITURA OBRIGATÓRIA ANTES DE ALTERAR CÓDIGO, RESULTADOS OU ARTIGO.**
>
> **Estado geral:** execução canônica `1e476243` concluída; hash completo
> `1e4762438a7e3627d3e32c1025f6bcb169e786881d8e86207806fdf98846409a`
> preservado em todos os artefatos e conferido por
> `python src/matriz_proveniencia.py`, sem divergência. O artigo (título
> "Classificação de chamados de manutenção predial com aprendizado de
> máquina: desempenho e limites da automação", reformulado na Rodada 12)
> tem seis figuras, cinco tabelas principais no corpo (Tabela 5 acrescida
> na Rodada 12), Apêndice A com as Tabelas A1 a A3, e 44 referências
> bibliográficas, todas citadas, auditadas conforme NBR 6023:2025/NBR
> 10520:2023 na Rodada 13. A Rodada 14 (branch
> `docs/correcoes-parecer-artigo-projeto`, PR draft #215) corrigiu os itens
> 1 a 12 de um parecer científico confrontado com o projeto de doutorado —
> reconciliação 598/593, decomposição do custo do BERTimbau, definição de
> "neutros", curva ABC global vs. interna ao tipo, otimismo da seleção do
> LinearSVC, "alvo de 0,95" no Resumo/Abstract, ausência de busca de
> hiperparâmetros, `p ≤ 0,0005`, "biossistema construído" como definição
> operacional autoral, harmonização de Capra/Odum/Grimm com o projeto,
> meia frase sobre o Naive Bayes, introdução do Apêndice A e Ticket-BERT
> como preprint — e, em microcorreção subsequente na mesma branch,
> resolveu o item 10 (Odum), substituindo Howard T. Odum por Eugene P.
> Odum (*Fundamentos de ecologia*, 6. ed., Fundação Calouste Gulbenkian,
> 1996), a partir do acervo do projeto, com ressalva bibliográfica apenas
> sobre a confirmação do ano na página de créditos do exemplar. Em segunda
> microcorreção na mesma branch, removida a seção "Disponibilidade de
> dados e código", que prometia disponibilização futura sem conteúdo
> científico. Em terceira microcorreção na mesma branch, substituída a
> formulação defensiva das Considerações Finais. Corpo científico em
> 8.961 palavras, dentro da faixa-meta de 8.850 a 9.000; PDF em 21
> páginas, inspecionado visualmente nas 21. Detalhes completos em
> `docs/AUDITORIA_PARECER_ARTIGO_PROJETO.md`. A Rodada 15 (branch
> `docs/consolidacao-material-suplementar`, PR draft separada, sem
> empilhamento sobre a PR #215) resolveu o item 13 do parecer —
> consolidação e renumeração contínua do material suplementar de S5–S17
> para S4–S16, sem recriar a antiga tabela legada S4, e publicação em
> `04_artigo/material_suplementar_classificacao_chamados.md`/
> `docs/material_suplementar_classificacao_chamados.pdf`. Detalhes
> completos em `docs/AUDITORIA_MATERIAL_SUPLEMENTAR.md`.
>
> **Regra principal:** os números do artigo já correspondem à execução canônica `1e476243`, a única que deve alimentar o texto. Qualquer alteração numérica futura exige nova execução canônica, reproduzível e comum a todos os modelos, antes de tocar o artigo; não é permitido substituir número isolado por preferência editorial.
>
> **Etapa 8 (governança de infraestrutura e dados), separada desta numeração de Passos do artigo: CONCLUÍDA no Lote 8I.** Cobre writers do GitHub Actions, proteção de `main`, privacidade e a separação entre artigo congelado, operação viva e novos cortes científicos. Estado final e auditoria de encerramento em [`docs/GOVERNANCA_FINAL_REPOSITORIO.md`](docs/GOVERNANCA_FINAL_REPOSITORIO.md).

Atualizado em 19/08/2026, no fuso America/Bahia.

**Pendência documental registrada em 05/08/2026, confirmada na Rodada 10:** não existe no repositório
documento de autorização institucional formal, de aprovação por comitê de ética
ou de dispensa de apreciação ética para uso científico dos registros do GLPI.
`Informação insuficiente para verificar.` O artigo declara essa ausência na
Subseção 3.6 (não 3.8: o Método vigente tem seis subseções) e nada afirma sobre aprovação. Providenciar a formalização antes
da submissão. Ver bloqueador correspondente em `docs/AUDITORIA_FINAL_SUBMISSAO.md`.

## 1. Por que este plano existe

A auditoria do artigo e do repositório identificou que os resultados atuais não respondem integralmente ao desenho metodológico definitivo escolhido pelo autor. Há quatro causas centrais:

1. os modelos principais foram treinados com as categorias históricas do GLPI, enquanto a avaliação posterior utilizou a referência humana revisada;
2. a validação principal foi dividida por chamado, permitindo que textos idênticos ou muito semelhantes aparecessem em partições diferentes;
3. o BERTimbau não foi avaliado no mesmo protocolo *out-of-fold* integral dos sete modelos principais;
4. documentos e artefatos ainda misturam estados incompatíveis, incluindo 14.058 e 8.895 decisões, além de 50 categorias declaradas pelo autor e 56 categorias com suporte registradas nos resultados vigentes.

Essas diferenças não devem ser corrigidas apenas por edição textual. Elas exigem reconstrução do protocolo experimental, retreinamento, recomputação das métricas e somente depois reescrita do artigo.

## 2. Posicionamento científico aprovado

A contribuição central será apresentada como:

> **Fluxo híbrido, auditável e sensível à confiança para classificação e revisão de chamados de manutenção predial, com comparação entre modelos estatísticos, regras de domínio e modelo contextual, considerando desempenho e viabilidade computacional.**

Título vigente:

> **Classificação auditável de chamados de manutenção predial: fluxo humano–IA, calibração e risco de reclassificação**

O estudo atenderá a dois usos:

- classificação de chamados futuros;
- revisão e correção da base histórica.

O artigo não deve afirmar que já realiza previsão de demanda, previsão de custos ou classificação de criticidade. Sua contribuição para a tese é a camada auditável de governança e estruturação de dados que antecede essas aplicações preditivas.

## 3. Decisões autorais já encerradas

Estas decisões não precisam ser perguntadas novamente:

- o corpus informado contém 14.058 chamados revisados;
- a referência humana final foi definida para todos os registros;
- o autor informou taxonomia final de 50 categorias;
- a categoria da coluna C é a saída do GLPI, produto do registro pelo demandante e da verificação pela equipe de triagem, e não atribuição isolada;
- a revisão final foi feita por um único especialista, em desenho de auditoria sobre rótulo já verificado, e não de anotação do zero;
- o especialista analisou título, descrição do chamado, título e descrição de OSM, quando existentes, e a categoria histórica;
- previsões e níveis de confiança dos modelos não estavam visíveis durante a revisão;
- ver a categoria histórica é constitutivo da tarefa de auditoria, e não contaminação: julgar um rótulo inadequado pressupõe conhecê-lo;
- o artigo não deve descrever colunas da planilha no corpo científico;
- deve-se usar “referência humana final” ou “categoria de referência revisada”, não “verdade validada”;
- todos os modelos devem ser retreinados com a referência humana revisada, em partições que preservem a separação entre treino e teste;
- a validação cruzada agrupada será o protocolo principal;
- a divisão aleatória por chamado poderá permanecer apenas como análise de sensibilidade;
- o BERTimbau só participará da comparação principal se cumprir o mesmo protocolo;
- regras de periodicidade preventiva serão avaliadas como camada híbrida separada;
- a operação pretendida comparará sugestão humana e automação seletiva por confiança;
- os erros terão custo uniforme nesta versão;
- não haverá segunda avaliação humana; ver o Passo 9 para a justificativa;
- os detalhes de reprodutibilidade serão divididos entre corpo, suplemento e repositório;
- o periódico será escolhido depois da revisão;
- a meta editorial provisória é de 8 a 9 mil palavras.

## 4. Estado verificável no início desta execução

| Item | Decisão/valor pretendido | Estado atual observado | Situação |
|---|---:|---|---|
| Corpus revisado | 14.058 | o plano antigo também conserva referência a 8.895 | reconciliar |
| Taxonomia final | 50 categorias, conforme informação do autor | resultados e plano vigentes registram 56 categorias com suporte | reconciliar por código |
| Rótulo de treino | referência humana revisada | execução vigente usou histórico do GLPI | substituir |
| Partição principal | grupos textuais | execução vigente foi principalmente por registro | substituir |
| BERTimbau | mesmo protocolo ou suplemento | protocolo diferente dos sete modelos | decidir após teste de viabilidade |
| Resultados atuais | apenas histórico | ainda sustentam artigo, painel e JSONs | arquivar e substituir |
| Segunda revisão cega | descartada | inaplicável ao desenho de auditoria | encerrada, ver Passo 9 |

Nenhum número divergente deve ser escolhido por preferência editorial. O total correto precisa ser produzido por uma auditoria reproduzível da base e da taxonomia.

## 5. Regras inegociáveis

1. Trabalhar sempre em branch e Pull Request; nunca enviar diretamente para `main`.
2. Antes de qualquer escrita na planilha viva, executar e reportar *dry-run*.
3. Nunca apagar, limpar ou sobrescrever as conferências humanas M, N e P nem a categoria manual Q.
4. Localizar colunas por cabeçalho, não por posição fixa.
5. Preservar snapshots dos resultados legados; substituir referências canônicas somente após validação completa.
6. Executar, antes de cada commit de código:
   - `python -m unittest discover -s tests`;
   - `python -m py_compile src/*.py`.
7. Não declarar acesso à planilha, retreinamento, métrica, custo computacional ou validação como concluídos sem evidência real.
8. Toda afirmação teórica incluída no artigo deve ter referência bibliográfica verificável.
9. Não iniciar a redução editorial antes de congelar os novos resultados.
10. Atualizar este arquivo ao fim de cada passo, registrando evidências, arquivos e próxima ação.

## 6. Plano de execução e critérios de aceite

### Passo 0 — registrar o plano e o ponto de continuidade

**Objetivo:** impedir perda de contexto entre agentes e sessões.

**Entregas:**

- este documento;
- link destacado no início do `README.md`;
- atualização do “Estado desta rodada” em `PLANO_ARTIGO_CAPITULO.md`;
- Pull Request próprio.

**Aceite:** qualquer novo agente encontra, pelo topo do README, o motivo da reformulação, o estado real e o próximo passo.

### Passo 1 — congelar e auditar a base canônica

**Objetivo:** produzir uma referência única antes de qualquer treinamento.

**Ações:**

- materializar a referência humana final por registro;
- validar ausência de referência vazia ou inválida;
- reconciliar 14.058 versus 8.895;
- reconciliar 50 categorias declaradas versus 56 categorias com suporte;
- listar categorias, frequências e mapeamentos de normalização;
- registrar hash, data, fonte, denominadores e script;
- produzir relatório sem escrever na planilha.

**Aceite:**

- 100% dos registros elegíveis possuem referência válida;
- nenhuma categoria fica fora da taxonomia congelada;
- corpus e taxonomia têm os mesmos valores em relatório, testes e metadados;
- qualquer exclusão é nominal, justificada e reproduzível.

### Passo 2 — construir grupos textuais

**Objetivo:** impedir vazamento entre chamados duplicados.

**Ações:**

- normalizar os quatro campos textuais usados pelos modelos;
- gerar grupos de textos idênticos;
- diagnosticar quase duplicados em análise separada;
- definir limiar de similaridade somente com justificativa e teste de sensibilidade;
- salvar identificador ou hash do grupo por registro.

**Aceite:** nenhum grupo idêntico atravessa treino e teste.

### Passo 3 — gerar partições canônicas

**Objetivo:** garantir comparação justa entre os modelos.

**Ações:**

- usar `StratifiedGroupKFold`, preferencialmente com cinco partições e semente fixa;
- verificar suporte das 50 categorias em cada dobra;
- tratar explicitamente classes raras que impeçam estratificação;
- salvar IDs ou hashes das partições;
- usar as mesmas partições para todos os modelos e para a camada de regras;
- manter separação aleatória por chamado somente como sensibilidade.

**Aceite:** partições reproduzíveis, sem sobreposição de grupos e com relatório de distribuição por categoria.

### Passo 4 — retreinar os sete modelos principais

Modelos:

- Naive Bayes;
- regressão logística;
- Random Forest;
- Extra Trees;
- SGD;
- LinearSVC;
- LSTM.

**Regras:**

- referência humana final como rótulo;
- predições *out-of-fold* para todo o corpus elegível;
- busca de hiperparâmetros restrita aos dados de treinamento;
- mesma representação de entrada e mesmas partições comparáveis;
- registrar tempo, memória, versão de dependências e semente.

**Aceite:** cada registro recebe previsão de modelo que não treinou no próprio registro nem no seu grupo textual.

### Passo 5 — comparar modelo puro e regras preventivas

**Objetivo:** medir, e não presumir, o valor das regras de domínio.

**Ações:**

- implementar regras em módulo separado e auditável;
- comparar cada configuração nas mesmas partições;
- incluir termos de periodicidade, como mensal, semanal, trimestral e semestral, apenas na camada explícita;
- medir desempenho global e desempenho nos chamados preventivos;
- registrar conflitos entre regra e modelo.

**Aceite:** relatório mostra ganho ou perda com denominadores idênticos e sem alterar silenciosamente o rótulo de referência.

### Passo 6 — decidir o BERTimbau

**Condição para o corpo principal:** mesma referência, mesmos grupos, mesmas partições, mesmos registros e seleção de hiperparâmetros sem acesso ao teste.

Se a execução integral não for viável:

- preservar os resultados como experimento exploratório;
- mover a análise detalhada para o suplemento;
- registrar hardware, memória, duração e motivo objetivo da interrupção;
- não comparar diretamente rankings produzidos por protocolos distintos.

**Aceite:** decisão documentada por evidência computacional, sem alegação vaga de custo.

**Decisão tomada em 03/08/2026:** o BERTimbau **não** integra a comparação principal e fica como experimento exploratório no suplemento. A medição em `docs/CUSTO_BERTIMBAU.md` cronometrou 10,774 segundos por passo de fine-tuning, com variação entre 10,706 e 10,824, sobre executor hospedado de quatro processadores e sem GPU. São 701 passos por época e 2.103 por dobra, o que projeta 6,44 horas por dobra e 32,2 horas nas cinco. Uma única dobra já excede o teto de seis horas de um job, de modo que nenhuma dobra completa cabe na infraestrutura disponível. A interrupção é, portanto, por limite de infraestrutura verificado, e não por escolha editorial. Rankings produzidos sob protocolos distintos não devem ser comparados diretamente.

### Passo 7 — calibração e automação seletiva

**Ações:**

- calibrar somente com dados internos de treinamento;
- definir ECE e método de cálculo;
- produzir curva de confiabilidade;
- incluir métrica complementar adequada;
- selecionar limiares sem usar a dobra de teste;
- reportar cobertura, acurácia seletiva e taxa de encaminhamento humano;
- comparar sugestão humana e automação condicionada à confiança.

**Aceite:** nenhum dado de teste influencia calibração ou escolha do limiar.

### Passo 8 — inferência estatística

**Ações:**

- bootstrap por grupo textual, não por linha, tanto para as métricas quanto
  para as diferenças entre modelos;
- unidade estatística no grupo textual também nos testes de hipótese, e não
  apenas nos intervalos;
- teste global pela estatística Q de Cochran com distribuição de referência
  obtida por permutação do rótulo de modelo dentro de cada grupo;
- comparações pareadas por permutação com troca de sinal da diferença de
  acertos por grupo;
- correção de Holm sobre a família dos 21 pares;
- por comparação: diferença observada, intervalo da diferença, grupos que
  favorecem cada modelo, tamanho de efeito e *p* ajustado;
- limitar testes ao necessário para as hipóteses do artigo, mantendo
  pressupostos periféricos fora do corpo.

**Aceite:** todos os testes usam as mesmas observações pareadas, a mesma
execução canônica e a mesma unidade de dependência que o Passo 3 usou para
particionar.

### Passo 9 — segunda validação humana cega

**Encerrado em 03/08/2026 como NÃO APLICÁVEL ao desenho.** Não é dependência
pendente e não deve ser retomado como tarefa.

**Por que a especificação original não se sustenta.** O passo pedia um segundo
avaliador "sem acesso à categoria histórica". Isso descreve anotação do zero,
que é tarefa diferente da que foi executada e da que faz sentido executar aqui.
O que existe é auditoria de rótulo: a pergunta é se a categoria registrada é
adequada ao chamado, e a categoria é o objeto do julgamento. Ocultá-la não
remove viés, torna a tarefa impossível — para corrigir um rótulo é preciso
vê-lo, e isso vale igualmente para a triagem da etapa operacional.

**Por que a medida também não é necessária.** A pergunta de pesquisa é se os
modelos classificam corretamente contra uma referência, não se a referência
seria reproduzida por outra pessoa. Um Kappa entre humanos responderia à
segunda pergunta, e ainda assim mal: como o revisor viu a categoria antes de
decidir, o coeficiente sairia inflado pela adjudicação e violaria o pressuposto
de independência. Publicá-lo como confiabilidade entre avaliadores seria
afirmar mais do que o dado sustenta.

**O que ocupa o lugar dele.** O Passo 2 mediu 17 grupos de texto idêntico com
referência divergente, afetando 85 linhas, ou 0,61% das linhas avaliadas. É
inconsistência interna da própria referência, medida sem segundo avaliador.
`src/auditar_grupos_divergentes.py` caracterizou esses grupos em 05/08/2026: em
14 deles, somando 74 linhas, as categorias em disputa pertencem a tipos
distintos de manutenção, e o par dominante opõe `Hidrossanitária > Hidráulica`
a `Manutenção Preventiva > Reservatório`, com 11 grupos e 65 linhas. Trata-se,
portanto, de ambiguidade de contexto não textual, e **não** de piso de erro de
anotação; a expressão "piso de erro irredutível" saiu do artigo.

**O que o artigo pode e não pode afirmar.** Pode reportar a inconsistência
interna com a caracterização acima e descrever a linha de base como rótulo
administrativo verificado por equipe técnica, e não como atribuição única. Não
pode afirmar que a referência é reproduzível por outro especialista, nem
estimar a prevalência de erro do rótulo histórico, porque nada disso foi
medido; a ausência dessas medidas entra nas limitações, junto com o efeito de
ancoragem decorrente de o revisor decidir vendo o rótulo que audita.

**Aceite:** justificativa registrada e limitação declarada. Nada a executar.

### Passo 10 — proveniência e reconstrução dos artefatos

**Ações:**

- criar tabela ligando cada número, tabela e figura ao script, entrada, denominador, taxonomia, partições e hash;
- gerar JSONs, tabelas, figuras, painel e artigo a partir da mesma execução;
- verificar que resultados antigos não permanecem no Resumo, Abstract, discussão ou conclusão;
- revisar o PDF visualmente.

**Aceite:** cada afirmação quantitativa principal pode ser rastreada até um artefato canônico.

### Passo 11 — redução e reescrita editorial

**Somente após o Passo 10.**

**Corpo principal:**

- problema e contribuição;
- construção da referência humana;
- protocolo agrupado;
- modelos e camada de regras;
- métricas essenciais;
- confiança e custo computacional;
- resultados centrais e implicações operacionais.

**Suplemento:**

- hiperparâmetros completos;
- matrizes de confusão extensas;
- resultados por categoria;
- ablações;
- testes secundários;
- detalhes operacionais.

**Meta provisória:** 8 a 9 mil palavras, aproximadamente quatro figuras e quatro ou cinco tabelas principais, ajustável depois da escolha do periódico.

## 7. Resultados atuais: tratamento obrigatório

Os resultados publicados antes desta reformulação não devem ser apagados. Devem ser identificados como **snapshot legado**, porque respondem a outro protocolo.

Não reutilizar nas conclusões definitivas, sem recomputação:

- rankings dos modelos;
- acurácia e F1 atuais;
- testes estatísticos atuais;
- calibração e limiares atuais;
- comparações diretas com BERTimbau;
- tabelas e figuras derivadas desses valores.

A preservação do snapshot permite auditoria histórica e comparação metodológica, mas não autoriza misturar números antigos e novos.

## 8. Ordem prática das próximas Pull Requests

| PR | Escopo | Dependência | Estado |
|---|---|---|---|
| PR-0 | registrar plano, README e estado da rodada | nenhuma | concluído — [PR #164](https://github.com/adinailson88/classificacao-chamados/pull/164) |
| PR-1 | Passo 1: base e taxonomia canônicas | PR-0 | concluído — ferramenta no [PR #166](https://github.com/adinailson88/classificacao-chamados/pull/166) e auditoria final `apto_para_congelar` |
| PR-2 | Passos 2 e 3: grupos e partições | PR-1 | concluído — 9.786 grupos textuais e partições canônicas em cinco dobras, `apto_para_treinar` |
| PR-3 | Passos 4 e 5: sete modelos e regras | PR-2 | concluído — rodada canônica `3aa42e31` |
| PR-4 | Passo 6: BERTimbau | PR-2 | concluído — exploratório, por custo medido |
| PR-5 | Passos 7 e 8: calibração e estatística | PR-3 e PR-4 | concluído — inferência refeita no nível do grupo textual em 05/08/2026 |
| PR-6 | Passo 9: validação humana | nenhuma | encerrado como não aplicável ao desenho |
| PR-7 | Passo 10: proveniência e artefatos | PR-5 e PR-6 | concluído — números, tabelas e figuras substituídos pelos da rodada `1e476243` |
| PR-8 | Passo 11: reescrita editorial | PR-7 | em execução — corpo em ~13.300 palavras, meta de 8 a 9 mil |

## 9. Registro de andamento

| Data | Passo | Estado | Evidência | Próxima ação |
|---|---|---|---|---|
| 02/08/2026 | 0 | concluído | [PR #164](https://github.com/adinailson88/classificacao-chamados/pull/164), merge `e39338c` | iniciar o Passo 1 em nova branch: auditoria canônica da base e da taxonomia |
| 03/08/2026 | 1 | concluído | [workflow final](https://github.com/adinailson88/classificacao-chamados/actions/runs/30780457229), artefato `8844276140`, 14.060/14.060 referências válidas, 50/50 categorias e hash `e10c78e4db0026cfcbfa5267ddac034a3c8d3a7a0a1d63fa0cf2ce52f165b174` | executar o Passo 2: normalizar os quatro campos textuais e construir grupos de textos idênticos |
| 03/08/2026 | 2 | concluído | [PR #168](https://github.com/adinailson88/classificacao-chamados/pull/168), merge `b990cbe4`, [workflow](https://github.com/adinailson88/classificacao-chamados/actions/runs/30784573148); 14.060 linhas em 9.786 grupos textuais, 9.474 unitários, 4.586 linhas com duplicata (32,62%), maior grupo com 219 linhas, nenhum grupo maior que uma dobra e hash do mapa `ab352b9424e31d2644ed6d075643adf562acc38767e0098eed77595e2dea0bb6` | executar o Passo 3: `StratifiedGroupKFold` com k=5 e semente fixa sobre os grupos congelados |
| 03/08/2026 | 3 | concluído | [PR #171](https://github.com/adinailson88/classificacao-chamados/pull/171) e [PR #172](https://github.com/adinailson88/classificacao-chamados/pull/172), [workflow](https://github.com/adinailson88/classificacao-chamados/actions/runs/30861272862); 13.972 linhas em 9.734 grupos, cinco dobras de 2.556 a 3.045 linhas, nenhum grupo dividido, 41 das 50 categorias com suporte em todas as dobras, 88 linhas fora por suporte insuficiente e hash do mapa `9465857d83ba76ec193974982835d91e03e783587153e26597051d4dfd9abcf2` | executar o Passo 4: retreinar os sete modelos sobre estas partições, com a referência humana como rótulo |
| 03/08/2026 | 4 | concluído | rodada canônica `3aa42e31`, [workflow](https://github.com/adinailson88/classificacao-chamados/actions/runs/30869618529); 13.972 linhas e 41 categorias, predição *out-of-fold* nos sete modelos, zero vazamento de grupo; melhor macro-F1 e melhor acurácia no `linear_svc` (0,6696 e 0,8255) | executar o Passo 8: inferência estatística com bootstrap por grupo textual |
| 03/08/2026 | 8 | concluído | rodada canônica `3aa42e31`, `docs/INFERENCIA_CANONICA.md`; bootstrap de 1.000 repetições sobre 9.735 grupos, Cochran Q = 2669,67 com p nulo, McNemar nos 21 pares com Holm; 18 pares significativos e 3 empatados | executar o Passo 10: proveniência e artefatos |
| 03/08/2026 | 10 | em execução | `docs/MATRIZ_PROVENIENCIA.md`; os 5 artefatos derivados conferem o hash `3aa42e31` e os 3 do congelamento estão presentes; a varredura achou 35 ocorrências de números legados na fonte do artigo | substituir os números legados no artigo, o que é decisão editorial |
| 03/08/2026 | 5 | concluído | rodada canônica `3aa42e31`, mesmo run; regra dispara em 4.487 dos 13.972 registros e melhora o macro-F1 de apenas 3 dos 7 modelos, com ganho concentrado no `naive_bayes` | resultado negativo registrado; nada a executar |
| 03/08/2026 | 6 | concluído | [PR #178](https://github.com/adinailson88/classificacao-chamados/pull/178), [workflow](https://github.com/adinailson88/classificacao-chamados/actions/runs/30866677706); 10,774 s por passo em CPU de quatro núcleos, 2.103 passos por dobra, 6,44 h por dobra e 32,2 h nas cinco, contra teto de 6 h por job; BERTimbau fica como exploratório no suplemento | decisão registrada; BERTimbau fora da comparação principal |
| 03/08/2026 | 7 | concluído | rodada canônica `3aa42e31`, mesmo run; calibração isotônica em dobra interna reduz o ECE de 5 dos 7 modelos, com o `linear_svc` caindo de 0,6926 para 0,0173; ao alvo de 0,95 o `extra_trees` automatiza 67,9% com acurácia seletiva de 0,9507 e encaminha 32,1% ao humano | executar o Passo 8: inferência estatística |

| 04/08/2026 | 10 | concluído | rodada canônica `1e476243`, `docs/MATRIZ_PROVENIENCIA.md`; os 5 artefatos derivados e os 3 do congelamento conferem o hash; as Tabelas 1 a 5 do corpo, as Figuras 2 a 6 e as tabelas do apêndice passaram a sair da rodada canônica; a varredura caiu de 35 para 2 ocorrências, ambas falso positivo (`0,7781` é o acordo bruto do SGD) | executar o Passo 11: redução editorial |
| 04/08/2026 | 11 | em execução | corpo do artigo de 14.782 para ~13.100 palavras; cinco tabelas no corpo e cinco movidas ao suplemento (S7 a S11); a antiga Tabela 3 virou S6; removida a Subseção 3.7, de fluxo interno de triagem; corrigido o protocolo declarado na Subseção 3.5, que ainda dizia `KFold` por linha | concluir a redução até 8 a 9 mil palavras e revisar o PDF |
| 05/08/2026 | 11 | em execução | rodada da referência humana: o artigo passou a nomear o desenho como auditoria administrativa de rótulo por avaliador único, e não anotação independente; os 4,25% viraram taxa de alteração do rótulo histórico, o que elimina a contradição com a limitação sobre prevalência; a ancoragem entrou como ressalva explícita; a ausência de segunda avaliação, de cegamento e de adjudicação está declarada, com a segunda avaliação registrada como validação futura; `src/auditar_grupos_divergentes.py` e `docs/dados/grupos_divergentes_canonicos.json` caracterizaram os 17 grupos e 85 linhas divergentes, mostrando que 14 grupos e 74 linhas opõem tipos distintos de manutenção, o que retira do valor o rótulo de piso de erro irredutível; Figura 1 e Subseção 3.1 recolocaram a revisão humana antes do treino e sobre o corpus integral; Subseção 3.8 registrou a governança de dados e a ausência de documento de ética ou autorização; corrigido "três registros" para dois com texto editado após o congelamento; fonte de 17.244 para 17.209 palavras | concluir a redução até 8 a 9 mil palavras e revisar o PDF gerado em `main` |
| 04/08/2026 | 10 | concluído | auditoria canônica dos bloqueadores numéricos, `docs/RASTREABILIDADE_LSTM.md`; matriz de proveniência ampliada com as grandezas de fora da rodada e suas ressalvas; 74 números do artigo conferidos contra os artefatos, com zero divergências, e nenhum decimal do corpo sem lastro em artefato versionado; 9.786/9.735/9.734 conciliados; discrepância do LSTM atribuída à coincidência de 100% entre referência e histórico nas 9.096 linhas do *ablation*; `src/ablation_lstm.py` corrigido, com regressão em `tests/test_ablation_lstm_chave.py` | executar o Passo 11: reduzir o corpo até 8 a 9 mil palavras e o PDF de 28 para cerca de 22 páginas |
| 05/08/2026 | 8 e 11 | concluído o 8, em execução o 11 | rodada canônica `1e476243`, `docs/INFERENCIA_AGRUPADA.md`, `docs/SENSIBILIDADE_CLASSES_RARAS.md` e `docs/UTILIDADE_RECLASSIFICACAO.md`; auditoria da unidade estatística mediu efeito de desenho entre 4,47 e 8,83, isto é, o McNemar por linha declarava erro padrão de 2,1 a 3,0 vezes menor do que a amostra sustenta; inferência refeita no nível do grupo, com Q de Cochran contra permutação por grupo (p < 0,0005), 21 permutações pareadas com Holm e bootstrap de conglomerados da diferença; os 21 vereditos não mudam, 19 significativos e 2 empatados; Subseção 4.9 reescrita e Shapiro-Wilk, Levene, VIF, outliers e correlação confiança-acerto retirados do corpo para a Tabela S15, com 15 referências órfãs removidas; sensibilidade das classes raras mediu cobertura de 99,37% das linhas e 82% das categorias e macro-F1 de 0,6684, 0,5481 e 0,6816 sob as três convenções de denominador; ganho líquido ganhou função de utilidade com ρ e λ adimensionais, ρ de equilíbrio de 0,2047 no melhor modelo e precisão de fila de triagem de 18,53%; corpo científico de 13.350 para 13.323 palavras e sete para seis figuras | concluir a redução até 8 a 9 mil palavras e revisar o PDF gerado em `main` |
| 05/08/2026 | 11 | em execução | rodada da validação temporal: `src/auditar_disponibilidade_temporal.py` e `docs/dados/disponibilidade_temporal.json` verificaram o contrato de colunas de `AGENTS.md` e os sete artefatos do congelamento e da rodada canônica, com veredito `sem_variavel_temporal` e zero campos candidatos a data do chamado, apenas carimbos `gerado_em` de geração de artefato; a avaliação em períodos sucessivos é, portanto, inexecutável sobre o corpus congelado e nenhum número temporal foi produzido; o artigo passou a declarar corte de extração na Subseção 3.2, a delimitar na 3.5 que o protocolo estima generalização entre grupos textuais e não desempenho futuro, a registrar na 5.3 a limitação e os riscos de implantação, e a condicionar as afirmações prospectivas da 5.2, da 5.4 e da Seção 6; corpo de 13.323 para 13.719 palavras, com compensação parcial na Discussão | reconstituir o corte preservando a data de abertura, o que habilita a avaliação temporal, e concluir a redução até 8 a 9 mil palavras |
| 05/08/2026 | 11 | em execução | rodada de posicionamento editorial: o título passou a nomear a contribuição real, sem multimodelo, sem validação humana e sem promessa temporal; Resumo e Abstract foram reescritos em estrutura paralela de nove movimentos, de 436 para 249 e de 413 para 247 palavras; a Introdução foi reordenada em relevância, registros textuais, rótulos históricos, lacuna, pergunta, contribuição e objetivo, com os quatro objetivos específicos substituídos por um objetivo geral e cinco contribuições, e caiu de 719 para 571 palavras; o Referencial foi reorganizado em quatro subseções, com uma nova sobre calibração e classificação seletiva, e caiu de 732 para 550 palavras; entraram CHOW (1970) e EL-YANIV; WIENER (2010) e saiu VASWANI *et al.* (2017), órfã após os cortes; os símbolos Unicode crus rô, lambda e menor ou igual viraram `$\rho$`, `$\lambda$` e `$\leq$`, com a conversão a LaTeX verificada por pandoc; 507 testes aprovados e matriz de proveniência sem divergências | concluir a redução até 8 a 9 mil palavras e revisar o PDF gerado em `main` |
| 05/08/2026 | 11 | em execução | rodada do método reprodutível: a Seção 3 foi reestruturada de oito para seis subseções, na ordem delineamento e referência revisada, pré-processamento e representação, modelos e configuração experimental, validação e calibração e inferência, reclassificação e análises complementares, e reprodutibilidade e governança; entrou a Tabela 1 com modelo, representação, hiperparâmetros, balanceamento, saída de confiança e papel, o que deslocou as tabelas do corpo de 1 a 6 para 2 a 7; as famílias de modelos deixaram de ser explicadas duas vezes e o `StratifiedGroupKFold` passou a ser descrito uma única vez; cada afirmação foi conferida contra `src/modelos_zoo.py`, `src/modelo_lstm.py`, `src/construir_grupos_textuais.py`, `src/gerar_particoes_canonicas.py` e `src/calibrar_confianca.py`, entrando os itens verificáveis que faltavam e saindo a regra de contingência do Random Forest, que é de produção; a calibração passou a declarar sem ambiguidade a dobra interna de ajuste, a dobra externa de avaliação e a ausência de acesso ao teste por transformações, tokenizadores, vocabulários, calibradores e limiares; 9.786, 9.735 e 9.734 estão distinguidos no corpo; auditoria independente incorporada: a consistência interna deixou de ser apresentada como dispensa de segundo avaliador, os 17 grupos divergentes deixaram de delimitar teto quantitativo e seus números passaram à Subseção 4.6, a declaração de sementes passou a registrar que a execução canônica da LSTM não fixou a semente global do TensorFlow e que a reprodução exata dos pesos não é garantida, e a discussão histórica de *post-hoc* saiu do corpo, com a remoção de BENAVOLI; CORANI; MANGILI (2016), DEMŠAR (2006), NEMENYI (1963) e NOMA *et al.* (2021), órfãs; Método de 2.972 para 2.228 palavras, menos 25,03%, dentro da meta; 507 testes aprovados e matriz de proveniência sem divergências | concluir a redução editorial nos Resultados e na Discussão e revisar o PDF gerado em `main` |
| 05/08/2026 | 11 | em execução | rodada dos resultados hierarquizados: a Seção 4 foi reestruturada de doze para cinco subseções, na ordem desempenho/incerteza/custo, auditoria do histórico e risco de reclassificação, calibração e automação seletiva, erros por categoria e implicações taxonômicas e análises complementares; a concordância histórica, a acurácia, o macro-F1, o custo de treino e o núcleo da inferência sob dependência textual fundiram-se em uma única tabela de desempenho (nova Tabela 2), substituindo três tabelas antigas; a tabela de calibração foi reduzida aos quatro modelos mais competitivos, com o ECE piorado do Naive Bayes e do LSTM declarado em texto e a tabela completa dos sete no suplemento; a matriz de 21 comparações pareadas saiu do corpo, restando teste global, contagem de pares significativos e um exemplo em prosa; as figuras foram renumeradas pela nova ordem de aparição (trade-off de custo passou a Figura 2, confiabilidade a Figura 3, mapa de categorias a Figura 4, matriz de confusão a Figura 5, curva do LSTM manteve o número 6); o parágrafo de abertura deixou de declarar o LinearSVC vencedor absoluto, registrando que a Regressão Logística tem macro-F1 pontual ligeiramente superior e o SGD permanece próximo; o macro-F1 de 0,5481 passou a cenário conservador de sensibilidade; os 17 grupos e 85 linhas divergentes, os 14 grupos e 74 linhas entre tipos distintos e o par dominante permanecem no corpo, sem tratamento de teto; todas as remissões a "Subseção 4.X" no Método, na Discussão e nas Considerações Finais foram remapeadas para a nova numeração; a frase "não está em falha de cálculo" saiu do texto; Seção 4 de 6.082 para 3.712 palavras, menos 38,97%, dentro da meta de 30% a 40%; corpo científico de cerca de 11.900 para 9.539 palavras, 539 acima do teto provisório de 9.000; 507 testes aprovados e matriz de proveniência sem divergências | revisar a Discussão por redundância remanescente com a Seção 4, concluir o ajuste fino até 8 a 9 mil palavras e revisar o PDF gerado em `main` |
| 05/08/2026 | 11 | concluído | Rodada 8 (agent/rodada-08-discussao-conclusao): a Discussão foi reestruturada de "5.1 concordância histórica" e "5.2 reclassificação/calibração" para quatro subseções, 5.1 adequação dos modelos e decisão multicritério, 5.2 auditoria do histórico/reclassificação/fluxo humano-IA, 5.3 limitações e alcance da evidência, 5.4 implicações para governança e continuidade da tese; os números já publicados na Tabela 2, na Tabela 3 e na Tabela 4 (as sete acurácias, os sete macro-F1, as 21 comparações pareadas, a calibração completa e os tempos de treino) deixaram de ser repetidos em prosa, restando remissão às tabelas; 475/2.321/−1.846 do ganho líquido passaram a aparecer uma única vez; as catorze limitações antes espalhadas entre Discussão, Conclusão e Declarações foram reunidas na única Subseção 5.3; Considerações Finais reescritas em cinco parágrafos curtos (contribuição, achados, implicação operacional, limitações, continuidade); nenhum número de Método ou Resultados foi alterado. Discussão de 1.955 para 1.421 palavras, Considerações Finais de 525 para 372, corpo científico de 9.539 para 8.871 palavras (dentro da faixa-meta de 8.850 a 9.000); Figuras 2, 4 e 5 reduzidas 20% (`width=95%→76%`, `91%→73%`, sem largura→`80%`); Tabelas 1 a 4 convertidas de `longtable` para floats `\begin{table}[!tbp]` com `tabularx`, verificado no LaTeX intermediário (4 tabelas fechadas, nenhuma em `longtable`, Tabelas A1 a A3 do apêndice mantidas como estavam); 507 testes aprovados, `py_compile` limpo e matriz de proveniência sem divergências | inspecionar visualmente o PDF gerado pelo workflow após o merge (figuras e tabelas) e tratar as Tabelas A1 a A3 do apêndice na Rodada 9 |
| 05/08/2026 | 11 | concluído | auditoria independente da PR #202: as legendas "Tabela 1" a "Tabela 4" saíram do parágrafo Markdown externo e passaram para `\caption{...}` dentro de cada `\begin{table}[!tbp]`, com `\label{tab:modelos}`, `tab:desempenho`, `tab:reclassificacao` e `tab:calibracao`; as quatro tabelas passaram de colunas fixas em `p{}` (que somavam entre 0,93 e 0,96 de `\textwidth` antes do `\tabcolsep`) para ao menos uma coluna flexível do tipo X por tabela (`\newcolumntype{Y}`/`{Z}` ponderadas por `\hsize`), as colunas flexíveis limitam a tabela à largura declarada do tabularx, mantendo necessária a inspeção do PDF quanto a conteúdo não separável e legibilidade; a Subseção 5.2 deixou de atribuir os 2,92 pontos percentuais de diferença diretamente às 598 alterações do rótulo histórico, já que a quantidade de alterações dentro das 13.972 linhas avaliadas não foi contabilizada separadamente; a recomendação do LinearSVC nas Considerações Finais e a frase da Subseção 5.1 passaram a descrever candidato/piloto controlado condicionado a validação temporal, monitoramento de deriva e auditoria humana, não implantação já validada; a expressão "preservados byte a byte" saiu de `PLANO_ARTIGO_CAPITULO.md`; auditoria bibliográfica encontrou quatro referências já órfãs antes desta rodada (COHEN, 1960; LANDIS; KOCH, 1977; MCNEMAR, 1947; WONGPAKARAN *et al.*, 2013), não removidas por estarem fora do escopo pedido; corpo científico de 8.871 para 8.917 palavras (Discussão 1.421→1.450, Conclusão 372→393), ainda dentro da faixa 8.850–9.000; 507 testes aprovados, `py_compile` limpo, matriz de proveniência sem divergências | inspecionar visualmente o PDF gerado pelo workflow após o merge e tratar as Tabelas A1 a A3 do apêndice na Rodada 9 |
| 05/08/2026 | 11 | concluído | segunda auditoria independente da PR #202: `\newcolumntype{Y}`/`{Z}` passaram a sincronizar `\linewidth=\hsize` dentro de cada coluna X (exigência do mecanismo interno do `tabularx` para colunas ponderadas, ausente na primeira correção); a afirmação de transbordo "estruturalmente impossível" saiu dos planos e do comentário no cabeçalho LaTeX do artigo, substituída por formulação que reconhece a necessidade de inspeção visual do PDF; removidas da lista de referências as quatro entradas já órfãs (COHEN, 1960; LANDIS; KOCH, 1977; MCNEMAR, 1947; WONGPAKARAN *et al.*, 2013); contagem precisa de referências (blocos separados por linha em branco entre "**REFERÊNCIAS**" e o Apêndice A) é de 49 antes e 45 depois, não 46/42 como estimado na primeira auditoria; confirmado que as 45 restantes têm ao menos uma citação no corpo e que toda citação do corpo tem entrada correspondente; nenhum conteúdo, linha, coluna, fonte, caption, label ou posição de float foi alterado além do pedido; corpo científico recontado após a remoção das referências (a lista bibliográfica não conta para a rotina de contagem do corpo, que vai de "**1. INTRODUÇÃO**" a "**REFERÊNCIAS**" exclusive); 507 testes aprovados, `py_compile` limpo, matriz de proveniência sem divergências | inspecionar visualmente o PDF gerado pelo workflow após o merge e tratar as Tabelas A1 a A3 do apêndice na Rodada 9 |
| 06/08/2026 | 11 | concluído | Rodada 9 (agent/rodada-09-figuras-paginacao): auditoria visual do PDF publicado após a PR #202 (commit `66ef86b6`, 21 páginas), renderizado página a página em PNG a 180 dpi via PyMuPDF (sem xelatex/Docker locais). Figuras 2, 4 e 5 (76%/73%/80%) legíveis, mantidas sem alteração; Figuras 1, 3 e 6 não criam página exclusiva nem espaço vazio desproporcional; Tabelas 1 a 4 íntegras, com caption e conteúdo na mesma página. Tabelas A1 a A3 do apêndice, embora `longtable`, já cabiam cada uma numa única página, mas usavam `\scriptsize`, abaixo do piso de legibilidade desta rodada; convertidas para floats não divisíveis (`\begin{table}[!tbp]`/`[!tp]` com `tabularx`, colunas `Y`/`Z`/nova `W` ponderadas por `\hsize`), fonte subida para `\footnotesize`, numeração renumerada para A1/A2/A3 via `\renewcommand{\thetable}{A\arabic{table}}` + `\setcounter{table}{0}`. Quatro rodadas de renderização real via `workflow_dispatch` na própria branch (sem tocar `main`) corrigiram dois problemas que só o PDF real revelava: legenda duplicada/numerada como "Tabela 5"/"6" (contador não resetado) e posição `[!p]` forçando página exclusiva mesmo cabendo com folga, que subiu a paginação de 21 para 24 páginas; corrigidos com o reset de contador e troca para `[!tbp]`, fechando em 22 páginas. Página com grande espaço vazio observada antes da Figura 3 (float não divisível migrando inteiro para a página seguinte) e espaço acima da Tabela A3 (última da página final, sem texto depois) registrados como limitações conhecidas, sem correção aplicada por não haver ajuste permitido nesta rodada (sem reduzir fonte/margem) que as resolvesse com segurança. Pendência registrada nesse momento (eixo Y da Figura 2 arredondando rótulos a uma casa decimal) resolvida na microcorreção seguinte, linha abaixo. 507 testes aprovados, `py_compile` limpo, matriz de proveniência sem divergências, hash `1e476243` mantido, 45 referências, corpo científico ~8.913 palavras (rotina antiga, incluindo blocos LaTeX brutos) | aguardar auditoria independente da Rodada 9 |
| 06/08/2026 | 11 | concluído | Microcorreção pendente da PR #203: `formatar_decimal()` em `src/gerar_figuras_canonicas.py` ganhou o parâmetro `casas` (padrão 1, preservando as demais figuras); `figura_custo()` passou a chamar `formatar_decimal(ax, eixo="y", casas=2)`. Apenas `04_artigo/figuras/fig_tradeoff_custo.pdf`/`.png` foram regenerados (`python src/gerar_figuras_canonicas.py --apenas custo`), hash `1e4762438a7e` conferido pelo próprio gerador; inspeção visual do PNG confirmou seis marcas distintas no eixo Y (0,72 a 0,82), sem rótulos repetidos. O gerador legado `src/gerar_figura3_tradeoff_custo.py` não foi executado nem alterado. Referências documentais em `PLANO_ARTIGO_CAPITULO.md` e `04_artigo/README.md` que atribuíam a pendência ao script legado foram corrigidas para apontar o gerador canônico; a menção histórica em `src/gerar_figuras_canonicas.py` (por que o módulo existe, cita os quatro geradores antigos como legados) foi preservada por já cumprir essa função. `origin/main` avançou um commit de dashboard (`314bd8e5`, `[skip ci]`) durante a rodada, sem conflito; integrado por merge. 507 testes aprovados, `py_compile` limpo, matriz de proveniência sem divergências, hash canônico completo `1e4762438a7e3627d3e32c1025f6bcb169e786881d8e86207806fdf98846409a` preservado | nenhuma; aguardar auditoria independente da Rodada 9 |
| 06/08/2026 | 11 | concluído | Rodada 10 (agent/rodada-10-auditoria-final-submissao): PR #203 (Rodada 9) confirmada mesclada (`69052405`) com PDF pós-merge regenerado (`7338214f`) e sem PR aberta; auditoria final de submissão sem reabertura de decisões científicas. Matriz de consistência numérica conferida contra os artefatos canônicos: corpo científico recontado em 8.913 palavras pela mesma rotina histórica antes de qualquer edição desta rodada (o valor de 8.917 registrado após a PR #202 refletia o corpo antes da conversão das Tabelas A1–A3 e da microcorreção da Figura 2, não uma rotina divergente); após a correção da chamada "(Tabela 4)" ausente na Subseção 4.3, a contagem passou a 8.915 palavras, ainda dentro da faixa-meta; 45 referências confirmadas, todas citadas no corpo, sem órfã nem duplicata; seis figuras e quatro tabelas principais confirmadas, com arquivos presentes; Tabelas A1–A3 confirmadas como floats `\footnotesize` não divisíveis, com soma de linhas batendo (14.060 = A1; 13.972 = A2; 88 = A3); a Subseção 4.3 citava em prosa os valores da Tabela 4 (calibração) sem nomeá-la, diferente das Tabelas 1 a 3, todas chamadas por número — corrigido com uma chamada "(Tabela 4)" acrescentada. Referência cruzada `Subseção 3.8` corrigida para `Subseção 3.6` neste documento (o Método vigente tem seis subseções; o artigo já citava 3.6 corretamente). Seções `PLANO_ARTIGO_CAPITULO.md` e `04_artigo/README.md` com "Estado desta rodada"/"Estado atual" que acumulavam narrativa de rodadas 6 a 9 condensadas ao estado vigente, com o detalhamento remetido ao histórico de commits/PRs. PDF regenerado via `workflow_dispatch` (run `31068296264`, commit `e8610cd9`) e inspecionado visualmente nas 22 páginas (renderização PyMuPDF a 150 dpi): seis figuras, quatro tabelas principais, Tabelas A1–A3 e lista de referências íntegras, sem regressão frente à Rodada 9. Bloqueador de submissão confirmado: nenhum documento de autorização institucional, aprovação ética ou dispensa formal no repositório; nenhuma declaração de financiamento, conflito de interesses, contribuição dos autores ou uso de inteligência artificial localizada no artigo — itens que dependem de decisão do autor. Veredito: apto com pendência documental. Detalhes completos em `docs/AUDITORIA_FINAL_SUBMISSAO.md` | abrir PR draft; aguardar decisão do autor sobre as declarações de submissão e a lacuna do suplemento S4 |
| 14/08/2026 | 11 | concluído | Rodada 11 (feat/integracao-editorial-ensemble): integração editorial do resultado confirmatório do ensemble da Fase 2C (PR #209 já mesclada em `main`, `c385fe03`, preservando os 25 commits científicos e as releases `ensemble-fase2b-execucao-cientifica-1`/`ensemble-fase2c-execucao-cientifica-1` conferidas). Acrescentado um parágrafo em cada uma das Subseções 3.5 (protocolo confirmatório: previsões cross-fitted dos sete modelos-base, sem novo ajuste, capacidade `K_f` por outer fold, sem tau otimizado), 4.5 (votação majoritária 516/−7, votação suave 503/−20, stacking 512/−11, contra 523 do LinearSVC, sobre 593 casos de `Y=1` e capacidade `K`=2.840; único ganho local do stacking no fold 3 não sustentado no agregado) e 5.1 (interpretação: reforça a escolha parcimoniosa neste corpus e capacidade, sem provar ensembles genericamente ineficazes, sem eliminar as limitações já registradas). Nenhuma alteração em Resumo, Abstract, Introdução, Considerações Finais, tabelas/figuras principais ou resultados canônicos anteriores. `src/tabelas_suplementares_canonicas.py` ganhou `s17_ensemble_confirmatorio()`, fonte exclusiva `docs/dados/ensemble/fase2c/fase2c_execucao_cientifica_1_manifest.json` (sem `hash_corpus`, por ser de outra trilha experimental), com validação de proveniência (universo 13.970, `Y=1` 593, `K` 2.840, run/commit da Fase 2B) e teste direcionado em `tests/test_tabelas_suplementares_s17.py` (9 testes); gera `04_artigo/figuras/tabela_S17_ensemble_confirmatorio.csv` (agregado + 5 outer folds × 4 métodos), numeração provisória após S16. Corpo científico de 8.915 para 8.999 palavras, com cortes compensatórios locais nas três subseções tocadas, dentro da faixa-meta de 8.850 a 9.000. 765 testes aprovados (756 + 9 novos), `py_compile` limpo, `python src/matriz_proveniencia.py` sem divergências (hash `1e4762438a7e` preservado; única mudança em `docs/MATRIZ_PROVENIENCIA.md`/`docs/dados/matriz_proveniencia.json` é o campo `gerado_em`). PDF regenerado pelo workflow oficial (`workflow_dispatch` na própria branch, run `31764231212`) e inspecionado visualmente nas 21 páginas (dentro de 21–23): seis figuras, quatro tabelas principais, Tabelas A1–A3 e lista de referências íntegras (45 entradas, sem órfã nem duplicata), sem regressão frente à Rodada 10. Zero retreino: fits de modelo-base = 0, fits de stacking = 0, execuções LSTM = 0 — todos os números vêm do manifesto já congelado. PR draft aberta contra `main`, sem merge, aguardando autorização do autor | aguardar decisão do autor sobre merge da PR e sobre os itens pendentes da Rodada 10 (autorização institucional, declarações de submissão, renumeração de S4–S17) |
| 14/08/2026 | 11 | concluído | Rodada 13 (correcao-referencias-abnt-2025): correção bibliográfica pontual, pendência registrada desde a Rodada 12 (auditoria da lista de referências contra a NBR 6023). Chamadas autor-data parentéticas convertidas de caixa alta para Maiúscula/minúscula (NBR 10520:2023); ordem de autoria de Marcuzzo *et al.* (2022) corrigida conforme a ACL Anthology; referência de Brown *et al.* (2020) simplificada; destaque tipográfico (itálico) do título da publicação padronizado nas 44 referências; DOIs verificados em fonte primária (CrossRef/ACL Anthology/página do periódico) — 30 referências passaram a ter DOI em relação à base (31 novos identificadores, pois Shannon recebeu dois; inclui Liu; Benge; Jiang, arXiv, completado com URL e data de acesso), 3 preexistentes reformatados para `https://doi.org/...`, 11 confirmadas sem DOI atribuído (não inventados; total final: 33 referências com DOI, 11 sem DOI, 34 identificadores no texto — ver correção complementar de 14/08/2026 e `docs/AUDITORIA_REFERENCIAS_2025.md`); correções pontuais de metadados (título de Martins; Espejo, páginas de Morais; Paula; Reis, fascículo de Pampana *et al.* e de Sundaram; Zeid, cidade de Souza; Nogueira; Lotufo). Na Introdução, removida a afirmação não comprovada "menos de 2%" do orçamento institucional, mantendo a restrição orçamentária genérica já sustentada pelas mesmas duas referências. 44 referências, todas citadas, sem duplicata nem órfã (inalterado). Nenhum número experimental, tabela, figura, resultado, conclusão ou contrato metodológico foi alterado. 764/765 testes aprovados (única falha é a divergência de ambiente já documentada na Rodada 12, não tocada nesta rodada), `compileall` limpo, matriz de proveniência sem divergências (hash `1e4762438a7e` preservado; timestamp da matriz revertido). PDF regenerado pelo workflow oficial, 21 páginas (dentro de 21–23), inspeção visual sem referência cortada ou sobreposta. Zero retreino: fits de modelo-base = 0, fits de stacking = 0, execuções LSTM = 0. Relatório completo em `docs/AUDITORIA_REFERENCIAS_2025.md`. PR draft aberta contra `main`, sem merge | aguardar decisão do autor sobre merge da PR e sobre os itens pendentes da Rodada 10 (autorização institucional, declarações de submissão, renumeração de S4–S17) |
| 15/08/2026 | 11 | concluído | Rodada 14 (docs/correcoes-parecer-artigo-projeto): correção dos itens 1 a 12 de um parecer científico confrontado com o projeto de doutorado (item 13, consolidação/publicação do suplemento, fica fora do escopo para PR separada). Corrigido: reconciliação 598/593 (Subseção 5.2); decomposição do custo do BERTimbau em 6,29h de treino e 6,44h totais (Subseção 4.5 e `docs/CUSTO_BERTIMBAU.md`, sem tocar `docs/dados/custo_bertimbau.json`); definição de "neutros" e fórmula da precisão de 18,53% (Tabela 3/Subseção 4.2); distinção entre curva ABC global e classe ABC interna ao tipo (Subseção 4.5); frase sobre o otimismo da seleção do LinearSVC (Subseção 5.3); "no alvo de 0,95 de acurácia" no Resumo e "under a target accuracy of 0.95" no Abstract; declaração de ausência de busca de hiperparâmetros (Subseção 3.3); renderização `p ≤ 0,0005` no artigo, em `docs/INFERENCIA_AGRUPADA.md` e em `src/inferencia_agrupada.py` (com teste unitário novo em `tests/test_inferencia_agrupada.py`, sem recalcular permutações nem tocar o JSON canônico); "biossistema construído" reescrito como definição operacional autoral, distinta dos fundamentos teóricos de Capra/Odum/Grimm (Introdução); harmonização parcial das referências — Capra corrigido para 1997 e Grimm *et al.* substituído por Grimm *et al.* (2000, *BioScience*, DOI conferido via redirecionamento OUP), ambos verificados em fontes externas; Odum **não alterado** e registrado como bloqueado, por achado de que a obra indicada pelo projeto ("Fundamentos de Ecologia") é de Eugene P. Odum, autor distinto do Howard T. Odum citado no artigo, sem acesso ao projeto para confirmar qual dos dois era pretendido; meia frase sobre o Naive Bayes ser o único modelo sem reponderação de classes (Subseção 4.4) e parágrafo na introdução do Apêndice A distinguindo a base de rótulo de A1 (histórica) e A2/A3 (referência revisada); referência de Liu; Benge; Jiang (Ticket-BERT) marcada explicitamente como preprint sem publicação revisada por pares localizada, e citação no corpo ajustada. Também constatado e registrado (não corrigido, fora do escopo dos itens 1–12): `PLANO_EXECUCAO_ATUAL.md` e `PLANO_ARTIGO_CAPITULO.md` estavam desatualizados frente a `main`, que já havia recebido as Rodadas 12 (revisão editorial v4) e 13 (correção bibliográfica) sem que os planos refletissem título, Subseção 3.6 ou Tabela 5 vigentes — reconciliado nesta rodada. Corpo científico de 8.855 (estado de `main`) para 8.999 palavras, com cortes compensatórios locais nas subseções tocadas, dentro da faixa-meta de 8.850 a 9.000. Matriz detalhada dos 12 itens, verificação bibliográfica externa e decisões documentadas em `docs/AUDITORIA_PARECER_ARTIGO_PROJETO.md` | aguardar decisão do autor sobre merge da PR, sobre a harmonização de Odum (confirmar autor/edição no projeto) e sobre a PR separada do item 13 (consolidação do material suplementar) |
| 15/08/2026 | 11 | concluído | Microcorreção da Rodada 14 (mesma branch `docs/correcoes-parecer-artigo-projeto`, sem nova PR): resolvido o bloqueio do item 10. O acervo do projeto de doutorado (exemplar e ficha de leitura em Google Drive, arquivo `1996_OUTRO_Ecologia_Odum_Fundamentos_Ecologia.pdf`) confirma que o autor pretendido é Eugene P. Odum, não Howard T. Odum; referência do artigo substituída para `ODUM, E. P. Fundamentos de ecologia. 6. ed. Lisboa: Fundação Calouste Gulbenkian, 1996.` e citação no corpo para "Odum (1996)", com corte local mínimo no mesmo parágrafo para manter a faixa de palavras. Autoria e edição (6ª) confirmadas pelo exemplar; o ano de 1996 é o do projeto e do nome do arquivo do acervo, não confirmado na página de créditos — registrado como ressalva bibliográfica, não como bloqueio. Inspeção visual do PDF completada nas 21 das 21 páginas (as páginas 3 e 4, antes não registradas individualmente, foram inspecionadas nesta rodada). Contagem inicial da auditoria reconciliada de 8.948 para 8.855 palavras, conforme `origin/main`, `04_artigo/README.md` e `PLANO_ARTIGO_CAPITULO.md` (nota de divergência de método de contagem registrada na auditoria). Corpo científico final: 8.999 palavras. 44 referências mantidas. Testes, `py_compile`, matriz de proveniência e hash canônico reconferidos sem divergência. PDF regenerado pelo workflow oficial e reinspecionado. Descrição da PR #215 atualizada | aguardar decisão do autor sobre merge da PR e sobre a PR separada do item 13 (consolidação do material suplementar); nenhum bloqueador de conteúdo remanescente dos itens 1–12 |
| 15/08/2026 | 11 | concluído | Segunda microcorreção da Rodada 14 (mesma branch `docs/correcoes-parecer-artigo-projeto`, sem nova PR): removida integralmente a seção "Disponibilidade de dados e código" do artigo, que prometia disponibilização futura de dados e código em repositório público permanente sem conteúdo científico correspondente; nenhuma declaração defensiva a substitui. Busca por construções equivalentes ("será/serão disponibilizado(s)", "disponibilidade de dados", "repositório público permanente") não encontrou outra ocorrência no corpo do artigo. Auditoria final dos itens 1 a 12 do parecer repetida diretamente sobre o texto do artigo (não apenas sobre a matriz declarada em `docs/AUDITORIA_PARECER_ARTIGO_PROJETO.md`): os 12 itens confirmados presentes e coerentes (reconciliação 598/593 na Subseção 5.2; decomposição 6,29h/6,44h/32,2h na Subseção 4.5; definição de "neutros" e fórmula 18,53% na Tabela 3/Subseção 4.2; curva ABC global vs. interna ao tipo na Subseção 4.5/Tabela A2; otimismo do LinearSVC na Subseção 5.3; "alvo de 0,95" no Resumo/Abstract; ausência de busca de hiperparâmetros na Subseção 3.3; `p ≤ 0,0005` em LaTeX na Subseção 4.1; "biossistema construído" como definição operacional na Introdução; Capra 1997/Grimm *et al.* 2000/Odum 1996 nas referências; frase do Naive Bayes na Subseção 4.4 e distinção A1/A2-A3 no Apêndice A; Ticket-BERT como preprint na Subseção 2.1 e nas referências); item 13 confirmado como pendência fora de escopo, registrada em `docs/AUDITORIA_PARECER_ARTIGO_PROJETO.md`, `PLANO_ARTIGO_CAPITULO.md` e nesta linha do plano, para PR separada. Corpo científico recontado pela mesma rotina histórica (split de espaços em branco entre "**1. INTRODUÇÃO**" e "**REFERÊNCIAS**", exclusive): de 8.999 para 8.972 palavras, dentro da faixa-meta de 8.850 a 9.000, sem nenhum texto acrescentado para compensar a remoção | rodar testes, `py_compile` e matriz de proveniência; commit único; disparar `artigo_pdf.yml`; inspecionar o PDF regenerado, com atenção à transição Considerações Finais → Referências |
| 15/08/2026 | 11 | concluído | Terceira microcorreção da Rodada 14 (mesma branch `docs/correcoes-parecer-artigo-projeto`, sem nova PR): nas Considerações Finais, a frase "Nenhuma delas invalida o protocolo: qualifica o que ele já entrega e delimita o que ainda depende de trabalho futuro para ser afirmado" foi substituída por "Essas limitações delimitam o alcance dos resultados e orientam as validações futuras", sem acrescentar explicação sobre a substituição no corpo do artigo; a ressalva metodológica sobre a impossibilidade de comparar o desempenho do BERTimbau sem execução equivalente permanece inalterada. Nove commits novos de `origin/main` (dados de dashboard/estatística) verificados como alterações exclusivas de campos de timestamp e incorporados por merge não destrutivo antes da edição. Corpo científico recontado pela mesma rotina histórica: de 8.972 para 8.961 palavras, dentro da faixa-meta de 8.850 a 9.000 | rodar testes, `py_compile` e matriz de proveniência; commit único; disparar `artigo_pdf.yml`; inspecionar o PDF regenerado, com atenção à transição Considerações Finais → Referências |
| 14/08/2026 | 11 | concluído | Correção complementar da Rodada 13 (correcao-referencias-abnt-2025), motivada por auditoria independente da PR #212: entrada de Brown *et al.* (2020) ainda listava sete autores nominais antes de "et al." apesar do relatório já descrever a simplificação — corrigida para `BROWN, T. B. et al.`; localizados e inseridos DOIs válidos de Efron; Tibshirani (1993, `10.1201/9780429246593`) e Kohavi (1995, `10.5555/1643031.1643047`, identificador confirmado como DOI real — prefixo `10.5555` é prefixo DOI registrado —, corrigindo alegação anterior em contrário); contagens finais harmonizadas em todos os documentos: 44 referências, 33 com ao menos um DOI, 11 sem DOI, 34 identificadores DOI no texto (Shannon possui dois), 30 referências passaram a ter DOI em relação à base, 31 novos identificadores (Shannon recebeu dois), 3 DOIs preexistentes apenas reformatados; afirmações antigas incompatíveis ("23 inseridos", "10 sem DOI", "13 sem DOI", alegação de que o identificador de Kohavi não seria DOI real) removidas deste documento, de `04_artigo/README.md` e de `docs/AUDITORIA_REFERENCIAS_2025.md`. `origin/main` integrado por merge (não destrutivo) antes da edição. Nenhum experimento repetido, nenhum modelo retreinado, nenhum número/tabela/figura/resultado alterado. Validações bibliográficas repetidas: 44 referências, 44/44 citadas, zero órfãs, zero citações sem referência, zero duplicatas, ordem alfabética correta, Brown como `BROWN, T. B. et al.`. PDF regenerado pelo workflow oficial `artigo_pdf.yml`. PR #212 mantida como draft, sem merge | aguardar decisão do autor sobre merge da PR #212 |
| 16/08/2026 | 11 | concluído | Rodada 15 (`docs/consolidacao-material-suplementar`): item 13 do parecer — consolidação, renumeração contínua e publicação do material suplementar, em PR draft separada, sem empilhamento sobre a PR #215. S5–S17 renumeradas para S4–S16 via `git mv` (ordem decrescente, sem colisão), conteúdo dos 13 CSVs renomeados preservado byte a byte (SHA-256 idêntico antes e depois); S1–S3 permanecem inalteradas; a antiga tabela legada S4 (`tabela_S4_holdout_vs_kfold.csv`) não foi recriada. As dez funções de `src/tabelas_suplementares_canonicas.py` que geravam S7–S17 renomeadas para `s6_`–`s16_`, mesma lógica; a constante de saída de `src/comparacao_kfold_groupkfold.py` atualizada para `tabela_S4_kfold_vs_groupkfold.csv`; `tests/test_tabelas_suplementares_s17.py` renomeado para `test_tabelas_suplementares_s16.py`. As duas únicas chamadas por número no artigo ("Tabela S16" na Subseção 4.3; "Tabela S17" na Subseção 4.5) atualizadas para "Tabela S15"/"Tabela S16". Criado `04_artigo/material_suplementar_classificacao_chamados.md` (sumário S1–S16, título técnico e nota de fonte/proveniência — distinguindo rodada canônica, legado pré-congelamento, exploratório do BERTimbau e confirmatório da Fase 2C — por tabela; tabelas largas divididas por largura de página), publicado em `docs/material_suplementar_classificacao_chamados.pdf` (13 páginas) via workflow próprio `material_suplementar_pdf.yml` (não integrado a `artigo_pdf.yml`, decisão registrada em `docs/AUDITORIA_MATERIAL_SUPLEMENTAR.md`, Seção 8). Três problemas visuais encontrados e corrigidos ao longo de quatro ciclos de geração/inspeção do PDF do suplemento (fallback de `placeins.sty` ausente; cabeçalhos de coluna sobrepostos e corte horizontal em tabelas largas; símbolos ρ/λ ausentes por estarem em Unicode bruto fora de modo matemático), nenhum deles envolvendo dado ou resultado. PDF principal regenerado pelo workflow oficial (`workflow_dispatch`, run `31922342255`), 21 páginas, inspecionado visualmente nas 21 — as duas chamadas renumeradas corretas, sem regressão. 767 testes aprovados, `py_compile` limpo, matriz de proveniência sem divergências (hash `1e4762438a7e` preservado; único campo alterado é `gerado_em`). Zero retreino: fits de modelo-base = 0, fits de stacking = 0, execuções LSTM/BERTimbau = 0. Detalhes completos em `docs/AUDITORIA_MATERIAL_SUPLEMENTAR.md` | aguardar decisão do autor sobre merge desta PR e da PR #215 |
Estados permitidos: `pendente`, `em execução`, `bloqueado`, `concluído`, `substituído`.

## 10. Instruções para continuidade por outro agente

Ao retomar:

1. ler `AGENTS.md`, este arquivo, `PLANO_ARTIGO_CAPITULO.md`, `CONTEXTO.md` e `04_artigo/README.md`;
2. verificar o PR e a branch em andamento;
3. conferir a última linha da seção “Registro de andamento”;
4. não repetir perguntas autorais registradas na seção 3;
5. não iniciar pelo artigo: iniciar pelo primeiro passo técnico pendente;
6. antes de alterar código, inspecionar testes e artefatos já existentes;
7. atualizar esta tabela e o “Estado desta rodada” ao concluir cada PR;
8. informar com precisão qualquer credencial ou workflow que falte, sem inventar execução.

### Prompt curto de retomada

> No repositório `adinailson88/classificacao-chamados`, leia primeiro `AGENTS.md` e `PLANO_EXECUCAO_ATUAL.md`. Continue a partir do primeiro passo técnico pendente no “Registro de andamento”. Trabalhe em branch e Pull Request, preserve M/N/P/Q, execute os testes exigidos antes de commits de código e atualize o plano com evidências reais. Não reescreva o artigo antes da execução canônica.

## 11. Trilha B (novo corte científico), iniciada em 30/10/2026

A Trilha B refaz toda a análise sobre um único corte de dados, em namespace e hash próprios (`docs/dados/trilha_b/`), sem tocar nos artefatos de `docs/dados/MANIFESTO_ARTIGO_CONGELADO.json`. Motivo: o artigo atual mistura cálculos feitos em datas diferentes (curva de aprendizado da LSTM de 25/07, ablation de 24/07, KFold contra GroupKFold de 01/08, ensemble em trilha própria, BERTimbau extrapolado). Decisão do autor: o estado do artigo atual não é restrição.

| Etapa | Estado | Evidência |
|---|---|---|
| Referência humana completa | concluída | 14.559 chamados, M/N/Q revisados pelo autor e por uma pessoa da DINFRA; 594 alterações (4,08%) |
| Corte B congelado | concluído | `src/corte_b.py`, aba imutável `CORTE_B_20261030`, `docs/dados/trilha_b/corte_b.json`, `hash_corte` `67812136fc08…`, `hash_entrada_modelo` `365922ce65a4…` |
| Grupos textuais e partições | concluídas | `src/trilha_b.py particoes`: 14.357 linhas, 10.596 grupos, 39 de 50 categorias, 202 linhas fora, zero grupo dividido |
| Retreino dos sete modelos | em execução | `src/trilha_b.py retreino`, semente do TensorFlow fixada |
| Avaliação temporal | pendente | `src/trilha_b.py temporal`: treino até 31/07/2026 e teste nos 500 chamados posteriores, mais origem rolante por ano |
| Calibração, inferência por grupo, recortes ABC e tipo, regras | pendente | scripts da rodada anterior ainda presos ao corte congelado; precisam ser parametrizados |
| Reexecução do que ficou fora da rodada (LSTM, ablation, KFold×GroupKFold, ensemble) e decisão do BERTimbau | pendente | |
| Proveniência, painel, artigo | pendente | nesta sequência |

Escopo: data de abertura e campus entram só como recorte de análise (campus) e como eixo temporal; localização e latitude/longitude ficam fora. Os workflows `corte_b.yml` e `trilha_b.yml` rodam por push na branch (a mensagem do commit precisa do marcador `[corte-b-aplicar]` ou `[trilha-b:etapa]`) enquanto não estiverem na `main`.

Pontos a decidir pelo autor: a categoria `Manutenção Preventiva > Elevador` (93 linhas) saiu das partições por sorteio, porque seus textos formam poucos grupos; o suporte mínimo de 5 grupos por categoria excluiu 11 das 50 categorias, contra 9 na rodada anterior.
