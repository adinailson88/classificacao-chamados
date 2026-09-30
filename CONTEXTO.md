# CONTEXTO — classificação de chamados

Este arquivo registra somente o estado vigente e a próxima ação do projeto. O histórico completo permanece nos commits, Pull Requests e execuções do GitHub Actions.

Atualizado em 28/07/2026, no fuso America/Bahia.

## Acesso público

- Artigo em PDF: <https://adinailson88.github.io/classificacao-chamados/artigo_classificacao_chamados.pdf>
- Painel: <https://adinailson88.github.io/classificacao-chamados/>
- Texto-fonte: [`04_artigo/artigo_classificacao_chamados_v3.md`](04_artigo/artigo_classificacao_chamados_v3.md)

## Objetivo

Avaliar modelos de aprendizagem de máquina para classificar chamados de manutenção predial em português brasileiro, distinguindo:

- concordância com a categoria administrativa histórica;
- acerto contra a decisão validada pela conferência humana;
- reclassificação e possíveis problemas da taxonomia histórica.

Os resultados alimentam o painel público e o artigo/capítulo da tese em Biossistemas Construídos.

## Estado dos resultados publicados

Os JSONs são dinâmicos e devem ser conferidos por data de geração antes de qualquer atualização do artigo.

- `docs/dados/avaliacao_final.json`, gerado em 28/07/2026, registra 8.895 decisões validadas, 639 casos restritos e 201 conflitos, sobre 8.895 decisões. Nesse recorte, o `linear_svc` lidera com acerto validado de 95,27% (IC95%: 94,82%–95,69%); os ensembles avaliados não superam o melhor modelo isolado.
- `docs/dados/bertimbau_training_state.json` está com `status=ok`: o treino do BERTimbau foi concluído em modo automático. `docs/dados/avaliacao_bertimbau_holdout.json` registra a avaliação held-out complementar, no mesmo lote de 1.000 chamados usado pelos outros sete modelos (639 com decisão M/N/P/Q): BERTimbau com acerto validado de 77,46% (IC95%: 74,02%–80,75%), segunda posição, contra 78,56% do LinearSVC (McNemar, *p* = 0,510, sem diferença significativa). O BERTimbau não integra o ranking integral dos sete modelos por não possuir predições *out-of-fold* sobre toda a base; é apresentado em subseção própria (4.3) do artigo.

## Arquitetura vigente

- A aba principal é lida em `A:Q`.
- A verdade validada é derivada por `src/decisao_validada.py` a partir de M, N, P e, quando necessário, Q.
- A memória de treino validada é lida diretamente da aba principal por `src/memoria_validada.py`; a antiga aba separada `VALIDACAO_HUMANA` não é mais fonte operacional.
- A consolidação das abas privadas usa `src/consolidar_validacao.py`, sem regra paralela de verdade e com exclusão de conflitos. O cron executa apenas dry-run; a gravação exige disparo manual explícito.
- Modelos compartilhados de reclassificação ficam em `src/modelos_reclassificacao.py`.
- Rotinas destrutivas de reset e executores legados da Etapa 2 não integram mais o fluxo vigente.

## Fontes canônicas

| Assunto | Fonte |
|---|---|
| Números do artigo, sem exceção | artefatos com `hash_corpus = 1e476243…`; ver `PLANO_ARTIGO_CAPITULO.md` e `docs/MATRIZ_PROVENIENCIA.md` |
| Resultado do painel por modelo | `docs/dados/avaliacao_final.json` |
| Estatística comparativa do painel | `docs/dados/estatistica.json` |
| Calibração e faixas de confiança do painel | `docs/dados/calibracao.json` e `docs/dados/calibracao_ajustada_modelos.json` |
| Verdade e memória validadas | `src/decisao_validada.py` e `src/memoria_validada.py` |
| Estado do BERTimbau | `docs/dados/bertimbau_training_state.json` e `docs/dados/bertimbau_metr_full.json` |
| Texto científico | `04_artigo/artigo_classificacao_chamados_v3.md` |
| Regras operacionais | `AGENTS.md` e `README.md` |

## Regras operacionais

1. Trabalhar em branch e Pull Request; não fazer push direto em `main`.
2. Qualquer escrita na planilha viva exige opção explícita de aplicação e dry-run prévio quando cabível.
3. Preservar as colunas de conferência humana M, N, P e Q.
4. Não confundir concordância com o histórico e acerto validado.
5. Não publicar texto livre de chamados nos arquivos do GitHub Pages.
6. Não copiar números antigos para o artigo sem conferir os JSONs vigentes e seus timestamps.
7. Novas execuções do BERTimbau devem usar diretamente `transformer_ft.yml`. Avaliação, estatística e consolidação devem ser verificadas e disparadas separadamente.

## Próxima ação

0. **Pendente (28/07/2026): reprocessamento após mesclagem de categorias no GLPI.** O usuário mesclou diretamente no GLPI os casos `Manutenção Preventiva > Extintor` → `Manutenção Preventiva > Sistemas de combate a incêndio (extintores, hidrantes)` e `Área Externa e Ambiental > Poda de árvore / Roçagem` → `Área Externa e Ambiental > Manutenção área externa / meio ambiente / Poda de árvore / Roçagem` (o usuário excluiu a categoria de Poda no GLPI e renomeou a categoria maior para esse nome novo combinado; por isso os DOIS nomes antigos apontam para ele — ver `config_categorias_canonicas.json`) (identificados via `docs/dados/cruzamento_taxonomia.json`, workflow `relevancia_termos.yml` rodado com `min_chamados_categoria=5`). Isso vai exigir atualizar o JSON de categorias de manutenção, o que propaga para o IMPORTRANGE da planilha e provavelmente exige rodar a pipeline inteira de novo (classificação, comparação de modelos, avaliação, calibração). Decisão explícita do usuário: quando isso acontecer, **não alterar a estrutura do artigo nem do dashboard** — só os dados/números devem mudar, seguindo o mesmo padrão do PR do BERTimbau (script editorial pontual, sem reescrever seções).
0.1. **Pendente (01/08/2026): a planilha esbarrou no teto de 10 milhões de células do Google Sheets.** A criação da aba `CONFERENCIA_MULTIMODELO` falhou com `This action would increase the number of cells in the workbook above the limit`. Auditoria em `scripts/migracoes/auditar_abas_planilha.py` (workflow `auditar_abas_planilha.yml`, read-only) mediu **9.008.123 células alocadas (90,1% do limite) para 7.427.340 usadas — 1.580.783 de desperdício**. Conclusões, para não refazer o diagnóstico:
    - **Não há lixo relevante.** Só 2 abas órfãs, somando 84 mil células (0,8% do limite). Apagar o que não é usado não resolve.
    - **O ganho está em redimensionar a grade**, sem apagar dado nenhum. Piores casos: `COMPARACAO_MODELOS` (260.000 alocadas para 1.313 usadas), `CLASSIF__transformer_ft` (220.000 para 11), `CONTROLE_CLASSIFICACAO_2` (180.000 para 261), `RECLASS_VALIDADOS` (260.000 para 50.115), `RECLASS__linear_svc` (476.720 para 225.520), `VALIDACAO_HUMANA` e `LOG_TURNOS_RECLASSIFICACAO` (alocadas e **totalmente vazias**). Redimensionar tudo levaria de 90,1% para ~74%.
    - **NÃO APAGAR `BACKUP_ETAPA1_20260726_131413`.** A auditoria o marca como órfão pelo prefixo, mas ele guarda **coluna A (ID) + G:K de 26/07, com 13.967 linhas** — é a fonte para restaurar a coluna G por `id_chamado`, ver item 0.2.
    - `RECLASS_HISTORICO` ocupa 2.718.336 células (30% de tudo), com zero desperdício. Compactar para a última entrada por chamado liberaria ~2,3 milhões, **mas só depois de exportar o histórico completo para arquivo** — foi essa trilha que permitiu restaurar a coluna O em 01/08.

0.2. **RESOLVIDO em 01/08/2026: coluna G realinhada.** Estava em `C == G` de 9,1% contra referencia de 67-71%. Rematerializada via `rematerializar_etapa1_oficial.yml` (backup em `BACKUP_ETAPA1_20260801_162324`) e repreenchida pela Etapa 1 sobre as 14.094 linhas atuais. Resultado medido: **`C == G` = 91,9%** e conflitos M+N de 7.469 para 351. A taxa ficou acima de 67-71% porque a coluna G e o modelo de PRODUCAO (LSTM+RF com `memoria_validada`), que reaproveita decisoes ja validadas — nao e *out-of-fold*; a referencia antiga era do LSTM OOF, comparacao indevida. Os 351 conflitos remanescentes sao vereditos da coluna N que se referiam ao G anterior; como a verdade nao usa mais N (ver `src/avaliacao_final.py --verdade glpi`), nao afetam metrica alguma.

0.3. **RESOLVIDO em 01/08/2026: workflows de escrita reabilitados.** Os oito haviam sido desabilitados durante o diagnostico e voltaram ao ar apos o realinhamento de G.

0.30. **CONSOLIDADO em 02/08/2026: base definitiva de 14.058 chamados, com predições limpas.** Estado final do dia, depois das correções descritas em 0.35.
    - **Base:** 14.058 chamados (= exatamente o que o GLPI mostra), 100% conferidos, 0 pendentes, 0 anomalias. Verdade: 13.452 do GLPI (M=Correto) + 606 da coluna Q. 65 categorias históricas em uso, mais 2 raízes residuais com 6 chamados.
    - **Fonte do IMPORTRANGE trocada** pelo pesquisador: as colunas A a D passaram a vir de `1VgHY6NmCQLtA3lcfQAzGIRqJFZGHwcGhZ4zaXkqOmz4` (aba `CHAMADOS`), com `FILTER` por `entidade = "UFSB > Dinfra"`. Isso removeu 54 chamados de `UFSB > Dinfra > Projetos e Obras`, fora do escopo. E e F continuam vindo de `1zTSo5oTFDyo3espWmYl1WjpFU57PwHDeZqnxUkrGQ2Y`, casadas por `A2`.
    - **Predições rematerializadas do zero, SEM memória validada.** As sete abas `CLASSIF__` e os logs foram apagados e refeitos com `--sem-memoria-validada`, k-fold 5, `base_treino_fixa=0`. Todos os sete têm 14.058 predições, mesmo protocolo, mesmo denominador.
    - **Números vigentes (acerto validado, n = 14.058):** LinearSVC 0,8198 [0,8138–0,8260], SGD 0,8013, Extra Trees 0,7984, Regressão Logística 0,7963, Random Forest 0,7897, LSTM 0,7106, Naive Bayes 0,7088. McNemar do 1º contra o 2º: p = 4,8×10⁻¹⁶. Cochran Q = 2446,95 (p ≈ 0), Friedman p = 1,9×10⁻⁸, Fleiss kappa 0,7767. Concordância histórica do LinearSVC: 0,8049.
    - **F1 macro:** SGD 0,5598 é o melhor entre os sete, à frente do LinearSVC (0,5567), embora perca 1,85 ponto em acurácia. Naive Bayes desaba para 0,2382.
    - **Held-out comum (983 validados):** BERTimbau 0,6785 e LinearSVC 0,6734, sem diferença significativa.
    - **Custo de treino medido** (`docs/dados/custo_computacional.json`, runner CPU, base inteira): Naive Bayes 1,21 s, LinearSVC 2,68 s, SGD 2,87 s, Regressão Logística 9,54 s, Random Forest 20,56 s, Extra Trees 24,40 s, LSTM 133,65 s. BERTimbau: 161 a 304 min, medidos nos logs de `transformer_ft.yml`, sobre subconjunto.

0.31. **CONSOLIDADO em 02/08/2026, fim do dia: recorte do F1 por volume e por tipo de manutenção, e a raiz `Manutenção Preventiva` deixou de existir.** Substitui os números de 0.30 no que diverge.
    - **Categoria raiz corrigida.** Os chamados `2025015458` e `2026070065` estavam na raiz `Manutenção Preventiva`, sem folha. Foram recategorizados no GLPI para `Manutenção Preventiva > Ar condicionado split`, o que fez a coluna C passar de 50 folhas mais 1 raiz para **50 folhas e nenhuma raiz**. A verdade validada continua com 13.452 do GLPI e 606 da coluna Q, e a taxa de erro do rótulo histórico segue em 4,3%.
    - **Números vigentes (acerto validado, n = 14.058):** LinearSVC 0,8197 [0,8136–0,8258], SGD 0,8011, Extra Trees 0,7984, Regressão Logística 0,7962, Random Forest 0,7899, LSTM 0,7107, Naive Bayes 0,7090. McNemar do 1º contra o 2º: p = 4,8×10⁻¹⁶. Cochran Q = 2448,55, Friedman p = 1,9×10⁻⁸, Fleiss kappa 0,7767. **F1 macro:** SGD 0,5555, LinearSVC 0,5523, Naive Bayes 0,2425. São **56 categorias com suporte na verdade**, e não 57: a raiz saiu, e com ela o F1 de 0,8000 sobre suporte 2 que premiava três modelos.
    - **Critério de tipo de manutenção, decisão do pesquisador:** três tipos, e não dois. `Outros`, `Suprimentos / Apoio Técnico`, `Posto de trabalho`, `Projetos e Reformas` e as raízes legadas `Projeto` e `Revisão` formam **Não manutenção**, 595 chamados (4,23%), que antes iam para Corretiva e inflavam o denominador dela em 7% relativos. `TI / Dados / Rede` permanece em Corretiva por ser reparo de infraestrutura predial. Implementado em `src/tipo_manutencao.py`, com espelho em JavaScript no painel.
    - **Recortes publicados** em `docs/dados/curva_abc_categorias.json`, aba `CURVA_ABC_CATEGORIAS` e três cartões do painel (PRs #161 e #162). Curva ABC global: classe A com 12 categorias e 80,92% do volume, B com 14, C com 30 e 642 chamados. F1 do LinearSVC: 0,8152 em A contra 0,3571 em C, o que localiza na cauda a distância entre acurácia de 0,82 e F1 macro de 0,55. **Tarefa de tipo** (verdade e predição projetadas): LinearSVC com acurácia de 0,9393, F1 de 0,9724 em preventiva e 0,9507 em corretiva, contra 0,4940 em não manutenção. Distinguir preventivo de corretivo é tarefa quase resolvida, e é ela que sustentará a contagem automática de preventivas no argumento de ESG da tese.
    - **ARMADILHA MEDIDA: durante o recálculo do IMPORTRANGE a aba devolve leitura incompleta sem sinal de erro.** Uma inspeção read-only rodada logo após a mudança no GLPI não encontrou dois ids que existiam, com a contagem de linhas inalterada e zero células de erro do Sheets. Minutos depois os mesmos ids estavam lá. Workflow disparado nessa janela grava número plausível e errado. Confirmar duas vezes antes de concluir que a base mudou.

0.35. **RESOLVIDO em 02/08/2026: a base saiu de 14.094 para 14.058 chamados e dois scripts quebraram em silêncio.** A fonte do IMPORTRANGE passou a filtrar a entidade estritamente (`UFSB > Dinfra`), removendo 54 chamados de `UFSB > Dinfra > Projetos e Obras`, que estavam fora do escopo, mais 2 excluídos no GLPI, e entraram 20 novos de julho. O total bate com o GLPI.
    - **Bug encontrado:** `avaliacao_final.py` e `avaliacao_bertimbau_holdout.py` cruzavam as abas materializadas (`CLASSIF__<modelo>`, `COMPARACAO_PREVISOES`) com a planilha principal **pelo número da linha**. Com a base menor, passaram a comparar a predição de um chamado com a verdade de outro: a avaliação final reportou **0,08** de acerto e o held-out **0,13**, ambos com o Naive Bayes em primeiro lugar. Os números eram plausíveis o bastante para serem publicados sem chamar atenção.
    - **O que salvou:** a matriz de confusão indexa por `id_chamado` e continuou marcando 0,8228 para o LinearSVC. A divergência entre as duas ferramentas foi o sinal.
    - **Correção:** PRs #152 e #153. `dv.carregar_decisoes` ganhou o parâmetro `chave` (padrão `'linha'`, para não quebrar os outros onze consumidores); as duas avaliações passam a pedir `'id'`. Regressão fixada em `tests/test_avaliacao_final_indexa_por_id.py`.
    - **RESOLVIDO (PR #159): varredura completa.** Depois de quatro ferramentas quebrarem no mesmo dia, os 27 arquivos que citam linha foram varridos, isolando os que cruzam DUAS fontes onde uma pode mudar de tamanho. Mais sete tinham o defeito: `analise_estatistica.py`, `calibracao.py`, `ablation_lstm.py` (o carregador nem lia o `id_chamado`), `reclassificacao_multimodelo.py` e `classificacao_ia_2_comite.py` (estes dois ESCREVEM, e podiam gravar no chamado errado), `validacao_nao_supervisionada.py` e `planilha.ler_conferencias` (que ganhou o parâmetro `chave`, como `carregar_decisoes`). Onze pontos no total passaram a casar por `id_chamado`.
    - **RESOLVIDO: leva duplicada e cron.** Um run cancelado às 12:16 gravou uma segunda leva em `CLASSIF__extra_trees` (28.152 registros), treinada com `memoria_validada=13703`, elevando o acerto de 0,7958 para 0,9816. A causa raiz era `linhas_ja_classificadas` ler a coluna B: com a base menor, todo chamado virou pendente. Corrigido para a coluna C (`ids_ja_classificados`), e o cron voltou a rodar, agora SEMPRE com `--sem-memoria-validada`. A Etapa 1 (produção) segue usando a memória, que é onde ela faz sentido.
    - **RESOLVIDO: calibração desalinhada.** Derivava a verdade de M, N e P, contra M e Q do resto do pipeline, produzindo 13.703 em vez de 14.058 sem que nada avisasse. Alinhada com `so_conferencia_glpi=True`.
    - **LIÇÃO:** nenhuma dessas falhas gerava erro. Todas devolviam números plausíveis e errados. O que expôs a primeira foi a discordância entre duas ferramentas que calculavam a mesma coisa por caminhos diferentes (avaliação final contra matriz de confusão). Vale manter essa redundância.

0.4. **CONCLUÍDO em 01/08/2026: a conferência manual das categorias GLPI cobre a base inteira.** Auditoria e regeneração da cadeia feitas na mesma data. Totais finais, medidos por `conferencia_derivada.yml` (run 30726343256):

| campo | antes (15:33) | final |
|---|---|---|
| com conferência GLPI (M) | 9.547 | 14.094 |
| sem conferência (M vazia) | 4.547 | 0 |
| pendente (M=Errado, Q vazia) | 242 | 0 |
| verdade do GLPI (M=Correto) | 9.305 | 13.492 |
| verdade da coluna Q | 0 | 602 |
| **base com verdade** | **9.305** | **14.094** |

   Duas verificações novas foram acrescentadas a `src/conferencia_derivada.py` (PR #147): `correto_com_q_preenchida` e `distribuicao_q`, mais `errado_com_q_igual_a_c`, que apareceu na prática. Estado final: **0 em ambas as anomalias**; 30 categorias distintas em Q, concentradas em `Manutenção Preventiva > Ar condicionado split` (189) e `Instalação de Acessórios e Mobiliário > Instalação/reparo de equipamentos` (78 + 45 em duas grafias — verificar se são a mesma categoria).

   Cadeia regerada: conferência derivada, avaliação final, estatística, held-out do BERTimbau e painel. Números vigentes (n = 14.094, acerto validado): LinearSVC 0,8220 [0,8155–0,8283], Extra Trees 0,8026, Regressão Logística 0,7991, SGD 0,7991, Random Forest 0,7969, LSTM 0,7264, Naive Bayes 0,7165. O LinearSVC segue líder (McNemar contra o segundo, *p* = 3,1×10⁻¹⁴; rank médio de Friedman 1,679). A ressalva do BERTimbau permanece: 0,8298 sobre 9.550 chamados da coluna O, contra 14.094 out-of-fold dos demais — vantagem de protocolo, não de modelo.

0.5. **BLOQUEADO: o artigo não pode ser sincronizado por substituição de números.** `src/sincronizar_numeros_artigo.py` aborta, corretamente. Dois motivos, e o segundo não se resolve editando o script:
    - Os trechos esperados estão duas gerações atrás do texto (o script procura 13.965/8.895/639; o artigo está em 14.094/9.305/242).
    - **`restritos` passou de 242 para 0.** Com cobertura de 100% e nenhum caso pendente, deixam de existir os objetos sobre os quais o artigo constrói sua principal limitação: a amostra conferida não é mais parcial, o acerto validado deixa de ser "limite superior por construção amostral", a análise de sensibilidade fica sem objeto e a coluna "Limite inferior" da Tabela 2 vira cópia do acerto validado. Passagens afetadas: linhas 76, 667, 768–769, 847, 856–866, 1227–1241, 1321–1326, 1385, 1398.

   Isso é reescrita de argumento, não troca de dado, e por decisão registrada cabe a uma pessoa. A limitação foi **eliminada**, não alterada — é ganho metodológico a ser redigido, não número a substituir.

1. ~~Preencher a categoria manual Q dos 639 casos restritos~~ — concluído, ver 0.4.
1.1. **Levar os recortes de 0.31 ao artigo.** Falta a última etapa da sequência planilha, painel, artigo. Envolve trocar os números do corte (0,8198 para 0,8197, F1 macro de 0,5567 para 0,5523, 57 para 56 categorias), retirar a menção à raiz residual, acrescentar o recorte ABC e por tipo à Subseção 4.10 de análise de erro, e montar a tabela do Apêndice em três blocos (P, C e NM), cada bloco ordenado por volume, com percentual e classe ABC relativos ao tipo, em uma página. O PR #160 precisa ser rebaseado sobre `main` antes.
2. Avaliar a viabilidade de uma execução *out-of-fold* integral do BERTimbau sobre toda a base, para permitir sua entrada no ranking principal. O treino atual roda em CPU no runner do GitHub Actions (teto de 6h), o que obriga o modo `auto` a usar subamostragem estratificada (`.github/workflows/transformer_ft.yml`); a base inteira (~13,8 mil chamados) não cabe nesse limite. **Ideia registrada, ainda não decidida:** rodar o fine-tuning em notebook Google Colab (GPU T4/A100), fora do fluxo automatizado por Actions, trazendo os artefatos de volta ao repositório manualmente. Ganho esperado: viabilizar o treino sobre a base inteira. Trade-off: sai do fluxo 100% reprodutível por Action; exige atenção ao levar a credencial da conta de serviço para dentro do notebook.
3. Considerar validação externa em outras instituições para testar a estabilidade dos resultados sob taxonomias e volumes distintos.
4. **PENDENTE (a partir de 14/10/2026): apagar a aba legada pós-migração do IMPORTRANGE.** Em 30/09/2026 a aba principal `CHAMADOS_ESQUELETO_REDUZIDO` foi substituída pela cópia sem IMPORTRANGE (ex-`COPIA`, mantida por script via ID, alinhamento linha a linha 18.859/18.859 conferido antes da troca). A aba principal antiga foi renomeada para `CHAMADOS_ESQUELETO_REDUZIDO_LEGADO_IMPORTRANGE` e deixada oculta, só como rede de segurança — não apagar antes de 14/10/2026 (2 semanas de observação). Pipeline e dashboard já validados rodando contra a nova aba (run manual do workflow "Atualizar dashboard" em 30/09/2026, números batendo com a execução anterior). Depois do prazo: (a) confirmar com o usuário, (b) apagar `CHAMADOS_ESQUELETO_REDUZIDO_LEGADO_IMPORTRANGE`, (c) remover o código morto de sync (`sincronizarCopiaPorId`/`sincronizarGQPorId` e funções de preflight/aplicar) em `SincronizarCopia.gs` no projeto Apps Script "API Classificacao Chamados". Pendência à parte: o gatilho `sincronizarGQPorId` ficou órfão, criado sob outro login Google do usuário — só pode ser removido logado com a conta que o criou.

## Registro histórico

Decisões anteriores, auditorias, planos concluídos e números substituídos devem ser consultados no histórico do Git e nos Pull Requests. Não devem voltar a ser acumulados neste arquivo.
