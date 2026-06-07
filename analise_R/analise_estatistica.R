# ============================================================================
# ANALISE ESTATISTICA DAS IAs DE CLASSIFICACAO DE CHAMADOS  (script em R)
# ----------------------------------------------------------------------------
# Projeto: classificacao-chamados (manutencao predial / UFSB)
# Autor base: Adinailson G. de Oliveira  |  Gerado para uso reprodutivel
#
# O QUE ESTE SCRIPT FAZ
#   Le um arquivo de dados pronto (TXT, separado por TAB) com o resultado de
#   cada IA por chamado e calcula TODA a estatistica comparativa nao parametrica
#   adequada ao problema (classificacao categorica, pareada e desbalanceada):
#     - Acuracia (concordancia vs historico) por modelo + IC95 por bootstrap;
#     - Cochran's Q (as k IAs tem a mesma taxa de acerto?);
#     - McNemar par a par + correcao de Holm-Bonferroni (FWER);
#     - Kappa de Cohen (IA x historico) e Kappa de Fleiss (entre as IAs);
#     - Friedman + diferenca critica de Nemenyi (sobre janelas da base);
#     - Shapiro-Wilk (apenas DIAGNOSTICO da nao-normalidade da serie por janela);
#     - Correlacao de Spearman (confianca x acerto);
#     - Macro-F1 por modelo.
#   Gera GRAFICOS (ggplot2), TABELAS (knitr::kable) e SAIDAS em arquivo.
#
# QUAL DOCUMENTO BAIXAR PARA RODAR
#   Baixe, do repositorio (pasta  analise_R/ ), DOIS arquivos e ponha na MESMA pasta:
#     1) analise_estatistica.R     (este script)
#     2) dados_modelos.txt         (a base ja pronta, TAB-separada)
#   O arquivo de dados tambem ja vem versionado no repositorio em analise_R/.
#
# COMO RODAR
#   Opcao A (RStudio): abra este .R, defina o diretorio de trabalho para a pasta
#     onde estao os dois arquivos (Session > Set Working Directory > To Source File
#     Location) e rode (Ctrl+Shift+Enter / Source).
#   Opcao B (terminal): entre na pasta analise_R/ e rode:  Rscript analise_estatistica.R
#
# OBSERVACAO METODOLOGICA
#   Enquanto a validacao humana nao for ampla, "acerto" = IA x categoria HISTORICA
#   (concordancia preliminar, nao verdade validada). A normalidade NAO e o eixo
#   central: serve so como diagnostico que justifica a abordagem nao parametrica.
#
# NOTA DE ESTILO: por preferencia do autor, usa-se "=" para atribuicao (e nao "<-").
# ============================================================================


# ---------------------------------------------------------------------------
# 0) PACOTES NECESSARIOS  (instala automaticamente os que faltarem)
# ---------------------------------------------------------------------------
pacotes = c("ggplot2", "knitr", "irr")
faltando = pacotes[!(pacotes %in% rownames(installed.packages()))]
if (length(faltando) > 0) {
  message("Instalando pacotes faltantes: ", paste(faltando, collapse = ", "))
  install.packages(faltando, repos = "https://cloud.r-project.org")
}
invisible(lapply(pacotes, library, character.only = TRUE))


# ---------------------------------------------------------------------------
# 1) LEITURA DO ARQUIVO DE DADOS  (via getwd() + read.delim)
# ---------------------------------------------------------------------------
# O arquivo dados_modelos.txt deve estar na MESMA pasta deste script.
pasta = getwd()
arquivo = file.path(pasta, "dados_modelos.txt")
cat("Diretorio de trabalho:", pasta, "\n")
cat("Procurando dados em:  ", arquivo, "\n")

if (!file.exists(arquivo)) {
  stop(paste0("Arquivo 'dados_modelos.txt' nao encontrado em ", pasta,
              ".\n  -> Rode o script a partir da pasta analise_R/ (ou copie o .txt para ca)."))
}

dados = read.delim(arquivo, sep = "\t", header = TRUE,
                   stringsAsFactors = FALSE, check.names = FALSE,
                   encoding = "UTF-8", quote = "")
cat("Linhas lidas:", nrow(dados), " | Colunas:", ncol(dados), "\n\n")

# Pasta de saidas (graficos e tabelas)
dir_saida = file.path(pasta, "saidas")
if (!dir.exists(dir_saida)) dir.create(dir_saida)


# ---------------------------------------------------------------------------
# 2) ESTRUTURA: identificar modelos e montar matrizes de apoio
# ---------------------------------------------------------------------------
# As colunas seguem o padrao: pred_<modelo>, conf_<modelo>, acerto_<modelo>.
cols_acerto = grep("^acerto_", names(dados), value = TRUE)
modelos = sub("^acerto_", "", cols_acerto)
k = length(modelos)
n = nrow(dados)
cat("Modelos detectados (", k, "):", paste(modelos, collapse = ", "), "\n")
cat("Chamados (n):", n, "\n\n")

# Matriz de acerto (n x k), 0/1
A = as.matrix(dados[, paste0("acerto_", modelos)])
storage.mode(A) = "integer"
colnames(A) = modelos

# Matriz de confianca (n x k) e de previsoes (n x k)
CONF = as.matrix(dados[, paste0("conf_", modelos)])
PRED = as.matrix(dados[, paste0("pred_", modelos)])
historico = dados$categoria_historica


# ---------------------------------------------------------------------------
# 3) ACURACIA (concordancia vs historico) + IC95 POR BOOTSTRAP
# ---------------------------------------------------------------------------
bootstrap_ic = function(x, n_boot = 2000, seed = 42) {
  set.seed(seed)
  medias = numeric(n_boot)
  for (b in 1:n_boot) {
    idx = sample.int(length(x), length(x), replace = TRUE)
    medias[b] = mean(x[idx])
  }
  c(media = mean(x),
    ic95_min = as.numeric(quantile(medias, 0.025)),
    ic95_max = as.numeric(quantile(medias, 0.975)))
}

tab_acc = data.frame(modelo = character(), acuracia = numeric(),
                     ic95_min = numeric(), ic95_max = numeric(),
                     stringsAsFactors = FALSE)
for (m in modelos) {
  r = bootstrap_ic(A[, m])
  tab_acc = rbind(tab_acc, data.frame(modelo = m, acuracia = round(r["media"], 4),
                                      ic95_min = round(r["ic95_min"], 4),
                                      ic95_max = round(r["ic95_max"], 4)))
}
tab_acc = tab_acc[order(-tab_acc$acuracia), ]
rownames(tab_acc) = NULL
cat("\n===== ACURACIA vs HISTORICO (com IC95 bootstrap) =====\n")
print(kable(tab_acc, format = "simple", digits = 4))


# ---------------------------------------------------------------------------
# 4) COCHRAN'S Q  (as k IAs tem a mesma taxa de acerto nas mesmas linhas?)
#    Implementado pela formula classica (dados binarios pareados).
# ---------------------------------------------------------------------------
cochran_q = function(A) {
  k = ncol(A)
  Cj = colSums(A)         # acertos por modelo
  Ri = rowSums(A)         # acertos por linha (entre modelos)
  num = (k - 1) * (k * sum(Cj^2) - sum(Cj)^2)
  den = k * sum(Ri) - sum(Ri^2)
  Q = ifelse(den == 0, NA, num / den)
  p = ifelse(is.na(Q), NA, pchisq(Q, df = k - 1, lower.tail = FALSE))
  list(Q = Q, df = k - 1, p = p)
}
cq = cochran_q(A)
cat("\n===== COCHRAN'S Q =====\n")
cat(sprintf("Q = %.3f | df = %d | p = %.3e | conclusao: %s\n",
            cq$Q, cq$df, cq$p,
            ifelse(cq$p < 0.05, "acuracias DIFERENTES (p<0,05)", "sem diferenca significativa")))


# ---------------------------------------------------------------------------
# 5) McNEMAR PAR A PAR + CORRECAO DE HOLM-BONFERRONI
# ---------------------------------------------------------------------------
pares = combn(modelos, 2, simplify = FALSE)
mc = data.frame(modelo_a = character(), modelo_b = character(),
                b01 = integer(), b10 = integer(), p = numeric(),
                stringsAsFactors = FALSE)
for (par in pares) {
  a = A[, par[1]]; b = A[, par[2]]
  # discordancias: a acerta e b erra (b10) ; a erra e b acerta (b01)
  b10 = sum(a == 1 & b == 0)
  b01 = sum(a == 0 & b == 1)
  tab = matrix(c(0, b01, b10, 0), nrow = 2)
  p = tryCatch(mcnemar.test(tab, correct = TRUE)$p.value, error = function(e) NA)
  mc = rbind(mc, data.frame(modelo_a = par[1], modelo_b = par[2],
                            b01 = b01, b10 = b10, p = p))
}
# Correcao de Holm-Bonferroni (controla o erro familiar / FWER)
mc$p_holm = p.adjust(mc$p, method = "holm")
mc$significativo = ifelse(!is.na(mc$p_holm) & mc$p_holm < 0.05, "sim", "nao")
mc = mc[order(mc$p), ]
rownames(mc) = NULL
cat("\n===== McNEMAR PAR A PAR (+ Holm-Bonferroni) =====\n")
print(kable(mc, format = "simple", digits = 5))


# ---------------------------------------------------------------------------
# 6) KAPPA DE COHEN (IA x historico) e KAPPA DE FLEISS (entre as IAs)
# ---------------------------------------------------------------------------
tab_kappa = data.frame(modelo = character(), kappa_cohen = numeric(),
                       stringsAsFactors = FALSE)
for (m in modelos) {
  kc = tryCatch(irr::kappa2(data.frame(historico, PRED[, m]))$value,
                error = function(e) NA)
  tab_kappa = rbind(tab_kappa, data.frame(modelo = m, kappa_cohen = round(kc, 4)))
}
tab_kappa = tab_kappa[order(-tab_kappa$kappa_cohen), ]
rownames(tab_kappa) = NULL
cat("\n===== KAPPA DE COHEN (IA x historico) =====\n")
print(kable(tab_kappa, format = "simple", digits = 4))

fleiss = tryCatch(irr::kappam.fleiss(as.data.frame(PRED))$value, error = function(e) NA)
cat(sprintf("\nKappa de Fleiss entre as %d IAs: %.4f  (concordancia entre os classificadores)\n", k, fleiss))


# ---------------------------------------------------------------------------
# 7) JANELAS DA BASE -> FRIEDMAN + DIFERENCA CRITICA DE NEMENYI
#    Cada bloco = uma janela de chamados; mede-se a acuracia por modelo no bloco.
# ---------------------------------------------------------------------------
tam_janela = 1000
dados$janela = floor((seq_len(n) - 1) / tam_janela) + 1
janelas = sort(unique(dados$janela))
# matriz blocos (janelas) x modelos com a acuracia em cada janela
M_jan = sapply(modelos, function(m) {
  tapply(A[, m], dados$janela, mean)
})
M_jan = as.matrix(M_jan)   # linhas = janelas, colunas = modelos

cat("\n===== FRIEDMAN (blocos = janelas de", tam_janela, "chamados) =====\n")
fr = tryCatch(friedman.test(M_jan), error = function(e) NULL)
if (!is.null(fr)) {
  cat(sprintf("Friedman chi2 = %.3f | df = %d | p = %.3e\n",
              fr$statistic, fr$parameter, fr$p.value))
  # ranks medios (1 = melhor) por bloco e diferenca critica de Nemenyi (alpha=0,05)
  ranks = t(apply(M_jan, 1, function(linha) rank(-linha)))
  rank_medio = colMeans(ranks)
  Nb = nrow(M_jan)
  q_nemenyi = c("2"=1.960,"3"=2.343,"4"=2.569,"5"=2.728,"6"=2.850,
                "7"=2.949,"8"=3.031,"9"=3.102,"10"=3.164)
  qa = ifelse(as.character(k) %in% names(q_nemenyi), q_nemenyi[[as.character(k)]], 3.0)
  CD = qa * sqrt(k * (k + 1) / (6 * Nb))
  tab_rank = data.frame(modelo = names(sort(rank_medio)),
                        rank_medio = round(sort(rank_medio), 3))
  rownames(tab_rank) = NULL
  cat(sprintf("Diferenca critica de Nemenyi (CD) = %.3f  (diferenca de rank > CD => significativa)\n", CD))
  print(kable(tab_rank, format = "simple", digits = 3))
}


# ---------------------------------------------------------------------------
# 8) SHAPIRO-WILK  (apenas DIAGNOSTICO: a serie de acuracia por janela e normal?)
# ---------------------------------------------------------------------------
cat("\n===== NORMALIDADE (Shapiro-Wilk) - diagnostico, nao eixo central =====\n")
tab_norm = data.frame(modelo = character(), shapiro_W = numeric(),
                      p = numeric(), distribuicao = character(),
                      stringsAsFactors = FALSE)
for (m in modelos) {
  serie = M_jan[, m]
  if (length(serie) >= 3 && length(unique(serie)) > 1) {
    sw = shapiro.test(serie)
    tab_norm = rbind(tab_norm, data.frame(
      modelo = m, shapiro_W = round(as.numeric(sw$statistic), 4),
      p = signif(sw$p.value, 3),
      distribuicao = ifelse(sw$p.value > 0.05, "normal", "nao-normal")))
  }
}
rownames(tab_norm) = NULL
print(kable(tab_norm, format = "simple"))
cat("Conclusao: distribuicoes nao-normais -> a analise usa SO testes nao parametricos.\n")


# ---------------------------------------------------------------------------
# 9) CORRELACAO DE SPEARMAN (confianca x acerto) e MACRO-F1 por modelo
# ---------------------------------------------------------------------------
macro_f1 = function(y_true, y_pred) {
  cats = sort(unique(c(y_true, y_pred)))
  f1s = sapply(cats, function(c) {
    tp = sum(y_pred == c & y_true == c)
    fp = sum(y_pred == c & y_true != c)
    fn = sum(y_pred != c & y_true == c)
    prec = ifelse(tp + fp == 0, 0, tp / (tp + fp))
    rec  = ifelse(tp + fn == 0, 0, tp / (tp + fn))
    ifelse(prec + rec == 0, 0, 2 * prec * rec / (prec + rec))
  })
  mean(f1s)
}
tab_extra = data.frame(modelo = character(), spearman_conf_acerto = numeric(),
                       macro_f1 = numeric(), stringsAsFactors = FALSE)
for (m in modelos) {
  rho = suppressWarnings(cor(CONF[, m], A[, m], method = "spearman"))
  f1 = macro_f1(historico, PRED[, m])
  tab_extra = rbind(tab_extra, data.frame(modelo = m,
                                          spearman_conf_acerto = round(rho, 4),
                                          macro_f1 = round(f1, 4)))
}
tab_extra = tab_extra[order(-tab_extra$macro_f1), ]
rownames(tab_extra) = NULL
cat("\n===== SPEARMAN (confianca x acerto) e MACRO-F1 =====\n")
print(kable(tab_extra, format = "simple", digits = 4))


# ---------------------------------------------------------------------------
# 10) GRAFICOS  (ggplot2) -> salvos em analise_R/saidas/
# ---------------------------------------------------------------------------
tema = theme_minimal(base_size = 12) +
  theme(plot.title = element_text(face = "bold"),
        axis.text.x = element_text(angle = 30, hjust = 1))

# 10.1 Acuracia por modelo com IC95
g1 = ggplot(tab_acc, aes(x = reorder(modelo, acuracia), y = acuracia)) +
  geom_col(fill = "#1d4ed8") +
  geom_errorbar(aes(ymin = ic95_min, ymax = ic95_max), width = 0.25, color = "#16386e") +
  geom_text(aes(label = sprintf("%.1f%%", acuracia * 100)), hjust = -0.15, size = 3.3) +
  coord_flip() +
  labs(title = "Acuracia (concordancia vs historico) com IC95",
       x = "Modelo", y = "Acuracia") + tema
ggsave(file.path(dir_saida, "01_acuracia_ic95.png"), g1, width = 8, height = 5, dpi = 130)

# 10.2 Macro-F1 por modelo
g2 = ggplot(tab_extra, aes(x = reorder(modelo, macro_f1), y = macro_f1)) +
  geom_col(fill = "#2563eb") + coord_flip() +
  labs(title = "Macro-F1 por modelo (vs historico)", x = "Modelo", y = "Macro-F1") + tema
ggsave(file.path(dir_saida, "02_macro_f1.png"), g2, width = 8, height = 5, dpi = 130)

# 10.3 Evolucao da acuracia por janela (linhas)
df_jan = data.frame()
for (m in modelos) {
  df_jan = rbind(df_jan, data.frame(janela = janelas, acuracia = M_jan[, m], modelo = m))
}
g3 = ggplot(df_jan, aes(x = janela, y = acuracia, color = modelo)) +
  geom_line(linewidth = 0.7) +
  labs(title = sprintf("Acuracia por janela de %d chamados", tam_janela),
       x = "Janela", y = "Acuracia") + theme_minimal(base_size = 12)
ggsave(file.path(dir_saida, "03_acuracia_por_janela.png"), g3, width = 9, height = 5, dpi = 130)

# 10.4 Mapa de calor dos p-valores de McNemar (Holm)
mc_full = expand.grid(a = modelos, b = modelos, stringsAsFactors = FALSE)
mc_full$p_holm = NA_real_
for (i in seq_len(nrow(mc))) {
  mc_full$p_holm[mc_full$a == mc$modelo_a[i] & mc_full$b == mc$modelo_b[i]] = mc$p_holm[i]
  mc_full$p_holm[mc_full$b == mc$modelo_a[i] & mc_full$a == mc$modelo_b[i]] = mc$p_holm[i]
}
g4 = ggplot(mc_full, aes(x = a, y = b, fill = p_holm)) +
  geom_tile(color = "white") +
  scale_fill_gradient(low = "#1d4ed8", high = "#e6edfb", na.value = "grey90", name = "p (Holm)") +
  labs(title = "McNemar par a par (p ajustado por Holm-Bonferroni)", x = "", y = "") +
  theme_minimal(base_size = 11) + theme(axis.text.x = element_text(angle = 35, hjust = 1))
ggsave(file.path(dir_saida, "04_mcnemar_holm.png"), g4, width = 8, height = 6.5, dpi = 130)


# ---------------------------------------------------------------------------
# 11) SAIDAS EM ARQUIVO  (CSV das tabelas + log resumo)
# ---------------------------------------------------------------------------
write.csv(tab_acc,   file.path(dir_saida, "tab_acuracia.csv"),   row.names = FALSE)
write.csv(mc,        file.path(dir_saida, "tab_mcnemar_holm.csv"), row.names = FALSE)
write.csv(tab_kappa, file.path(dir_saida, "tab_kappa_cohen.csv"), row.names = FALSE)
write.csv(tab_extra, file.path(dir_saida, "tab_spearman_macrof1.csv"), row.names = FALSE)
write.csv(tab_norm,  file.path(dir_saida, "tab_normalidade.csv"), row.names = FALSE)

cat("\n============================================================\n")
cat("CONCLUIDO. Graficos e tabelas salvos em:", dir_saida, "\n")
cat("  - 01_acuracia_ic95.png / 02_macro_f1.png / 03_acuracia_por_janela.png / 04_mcnemar_holm.png\n")
cat("  - tab_*.csv (acuracia, mcnemar_holm, kappa_cohen, spearman_macrof1, normalidade)\n")
cat("LEMBRETE: 'acerto' aqui = IA x categoria HISTORICA (preliminar).\n")
cat("A verdade definitiva exige a validacao humana (colunas M/N/P da planilha).\n")
cat("============================================================\n")
