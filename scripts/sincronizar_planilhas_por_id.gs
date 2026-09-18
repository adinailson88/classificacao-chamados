/**
 * Sincronização segura das colunas A:F de CHAMADOS_ESQUELETO_REDUZIDO.
 *
 * Objetivo:
 * - eliminar IMPORTRANGE das colunas A:F;
 * - preservar G:Q sem qualquer escrita;
 * - reconstruir A:F por ID Chamado;
 * - usar SNAPSHOT_ETAPA_1 para preservar linha -> ID na migração inicial;
 * - manter sincronização futura idempotente e por ID.
 *
 * IMPORTANTE:
 * 1) Execute primeiro preflightMigracaoImportrange().
 * 2) Revise PREVIEW_SINCRONIZACAO_A_F.
 * 3) Só então escreva APLICAR_MIGRACAO em B1 da aba de preview.
 * 4) Execute aplicarMigracaoImportrange().
 * 5) Não instale gatilho antes de validar a migração.
 */

const SYNC_CFG = Object.freeze({
  // Fonte histórica MATERIALIZADA que originou os 14.336 IDs do experimento.
  // Pagina1 não depende de IMPORTRANGE; categoria completa = E + " > " + F.
  historicalSpreadsheetId: "1xnU5sDcEWrDjs_trU3tC0jOHCljp7o_SmRNvyJzqkUg",
  historicalSheetName: "Pagina1",
  historicalCols: Object.freeze({ id: 1, titulo: 2, categoria: 5, subcategoria: 6 }),

  // Espelho corrente do GLPI. Usado para descrição/solução e, após a migração,
  // para atualizar B:D e acrescentar chamados novos por ID.
  currentSpreadsheetId: "15_fsbXktpvRGJ3OTq2NsWvjMztF4IYiRQmgRASlVWIQ",
  currentSheetName: "GLPI",
  currentCols: Object.freeze({ id: 1, titulo: 2, categoria: 6, descricao: 17, solucao: 19 }),

  osSpreadsheetId: "1zTSo5oTFDyo3espWmYl1WjpFU57PwHDeZqnxUkrGQ2Y",
  osSheetName: "Ordens de Serviços",
  osCols: Object.freeze({ idChamado: 2, titulo: 3, descricao: 5 }),

  destSpreadsheetId: "1lohPUQOgxzt_DMxnNLKMxnieZq1sVmh4uwBLbbgvfiQ",
  destSheetName: "CHAMADOS_ESQUELETO_REDUZIDO",
  snapshotSheetName: "SNAPSHOT_ETAPA_1",

  previewSheetName: "PREVIEW_SINCRONIZACAO_A_F",
  logSheetName: "LOG_SINCRONIZACAO_A_F",
  backupPrefix: "BACKUP_PRE_MIGRACAO_AF_",

  authorizationCell: "B1",
  authorizationValue: "APLICAR_MIGRACAO",

  maxNewPerRun: 100,
  maxExistingUpdatesPerRun: 500,
  triggerEveryHours: 2,
  timeZone: "America/Bahia"
});

function preflightMigracaoImportrange() {
  return withScriptLock_(function () {
    const plano = montarPlanoMigracao_();
    escreverPreviewMigracao_(plano);
    Logger.log(JSON.stringify(plano.resumo));
    return plano.resumo;
  });
}

function aplicarMigracaoImportrange() {
  return withScriptLock_(function () {
    const ss = SpreadsheetApp.openById(SYNC_CFG.destSpreadsheetId);
    const preview = ss.getSheetByName(SYNC_CFG.previewSheetName);
    if (!preview) {
      throw new Error("PREVIEW_AUSENTE: execute preflightMigracaoImportrange() antes.");
    }
    const autorizacao = String(preview.getRange(SYNC_CFG.authorizationCell).getDisplayValue() || "").trim();
    if (autorizacao !== SYNC_CFG.authorizationValue) {
      throw new Error(
        "SEM_AUTORIZACAO: escreva " + SYNC_CFG.authorizationValue +
        " em " + SYNC_CFG.previewSheetName + "!" + SYNC_CFG.authorizationCell + "."
      );
    }

    // Recalcula tudo imediatamente antes da escrita; não confia em preview antigo.
    const plano = montarPlanoMigracao_();
    if (!plano.apto) {
      escreverPreviewMigracao_(plano);
      throw new Error("MIGRACAO_BLOQUEADA: preflight atual contém anomalias. Nenhuma coluna A:F foi alterada.");
    }

    const principal = ss.getSheetByName(SYNC_CFG.destSheetName);
    if (!principal) throw new Error("Aba destino não encontrada.");

    const backupName = criarBackupAba_(ss, principal);

    const quantidade = plano.matriz.length;
    const destino = principal.getRange(2, 1, quantidade, 6);
    destino.setNumberFormat("@");
    destino.setValues(plano.matriz.map(linha => linha.map(valorLiteral_)));

    // Depois que A2:D2 deixam de ser fórmulas matriciais, elimina qualquer
    // resíduo A:F abaixo da última linha coberta pelo snapshot. O preflight
    // só permite isso quando G:Q não possuem dados além dessa linha.
    const maxLinhaSnapshot = plano.mapaSnapshot.maxLinha;
    const ultimaAntesLimpeza = principal.getLastRow();
    let linhasResiduoLimpas = 0;
    if (ultimaAntesLimpeza > maxLinhaSnapshot) {
      linhasResiduoLimpas = ultimaAntesLimpeza - maxLinhaSnapshot;
      principal.getRange(maxLinhaSnapshot + 1, 1, linhasResiduoLimpas, 6).clearContent();
    }

    SpreadsheetApp.flush();

    const lido = principal.getRange(2, 1, quantidade, 6).getDisplayValues();
    const divergencias = compararMatrizes_(plano.matriz, lido, 20);
    if (divergencias.length) {
      anexarLogResumo_(
        ss, "MIGRACAO_FALHA_READBACK", "", "", "",
        "backup=" + backupName + "; divergencias=" + JSON.stringify(divergencias)
      );
      throw new Error(
        "READBACK_DIVERGENTE: A:F não coincidem integralmente com o plano. " +
        "Backup preservado em " + backupName + ". G:Q não foram alteradas."
      );
    }

    anexarLogResumo_(
      ss,
      "MIGRACAO_CONCLUIDA",
      "",
      "IMPORTRANGE",
      "VALORES_MATERIALIZADOS",
      "linhas=" + quantidade + "; residuos_A_F_limpos=" + linhasResiduoLimpas + "; backup=" + backupName
    );

    preview.getRange(SYNC_CFG.authorizationCell).clearContent();
    preview.getRange("B3").setValue("CONCLUIDA");
    preview.getRange("B4").setValue(agora_());
    preview.getRange("B5").setValue(backupName);

    return {
      status: "CONCLUIDA",
      linhasMaterializadas: quantidade,
      backup: backupName
    };
  });
}

function simularSincronizacaoPorId() {
  return withScriptLock_(function () {
    const plano = montarPlanoSincronizacao_();
    escreverPreviewSincronizacao_(plano);
    Logger.log(JSON.stringify(plano.resumo));
    return plano.resumo;
  });
}

function sincronizarChamadosPorId() {
  return withScriptLock_(function () {
    const plano = montarPlanoSincronizacao_();
    if (!plano.apto) {
      escreverPreviewSincronizacao_(plano);
      throw new Error("SINCRONIZACAO_BLOQUEADA: " + plano.bloqueios.join(" | "));
    }

    const ss = SpreadsheetApp.openById(SYNC_CFG.destSpreadsheetId);
    const principal = ss.getSheetByName(SYNC_CFG.destSheetName);
    const log = obterLog_(ss);

    const atualizacoes = plano.atualizacoes.slice().sort((a, b) => a.linha - b.linha);
    for (const item of atualizacoes) {
      const range = principal.getRange(item.linha, 2, 1, 5); // B:F; A é chave imutável.
      range.setNumberFormat("@");
      range.setValues([item.depois.map(valorLiteral_)]);
      log.appendRow([
        agora_(), "ATUALIZADO", item.id, item.linha,
        item.antes[2], item.depois[1],
        "campos=" + item.camposAlterados.join(",")
      ]);
    }

    if (plano.novos.length) {
      const ultimaLinha = plano.ultimaLinhaDestino;
      const primeiraNova = ultimaLinha + 1;
      const linhasNecessarias = primeiraNova + plano.novos.length - 1;
      if (linhasNecessarias > principal.getMaxRows()) {
        principal.insertRowsAfter(
          principal.getMaxRows(),
          linhasNecessarias - principal.getMaxRows()
        );
      }

      const valores = plano.novos.map(x => x.valores.map(valorLiteral_));
      const rangeNovos = principal.getRange(primeiraNova, 1, valores.length, 6);
      rangeNovos.setNumberFormat("@");
      rangeNovos.setValues(valores);

      plano.novos.forEach((item, i) => {
        log.appendRow([
          agora_(), "NOVO", item.id, primeiraNova + i,
          "", item.valores[2], "A:F materializados; G:Q preservados em branco"
        ]);
      });
    }

    SpreadsheetApp.flush();

    // Pós-condição: nenhum ID foi deslocado e os novos IDs estão onde deveriam.
    validarIdsDestino_(principal);

    return {
      status: "APLICADO",
      atualizados: plano.atualizacoes.length,
      novos: plano.novos.length
    };
  });
}

function instalarGatilhoSincronizacao() {
  removerGatilhosSincronizacao();
  ScriptApp.newTrigger("sincronizarChamadosPorId")
    .timeBased()
    .everyHours(SYNC_CFG.triggerEveryHours)
    .create();
}

function removerGatilhosSincronizacao() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === "sincronizarChamadosPorId")
    .forEach(t => ScriptApp.deleteTrigger(t));
}

function montarPlanoMigracao_() {
  const ss = SpreadsheetApp.openById(SYNC_CFG.destSpreadsheetId);
  const principal = ss.getSheetByName(SYNC_CFG.destSheetName);
  const snapshot = ss.getSheetByName(SYNC_CFG.snapshotSheetName);
  if (!principal || !snapshot) throw new Error("Aba principal ou SNAPSHOT_ETAPA_1 não encontrada.");

  const historica = lerFonteHistorica_();
  const atual = lerFonteAtualGlpi_();
  const osm = lerOrdensServico_();
  const mapaSnapshot = lerMapaAtualSnapshot_(snapshot);
  const ultimaLinhaFisicaComConteudo = Math.max(principal.getLastRow(), mapaSnapshot.maxLinha);
  const formulas = auditarFormulasImportacao_(principal, ultimaLinhaFisicaComConteudo);
  const ultimaCritica = ultimaLinhaComDados_(principal, 7, 11); // G:Q

  const faltantesHistorico = [];
  const semDescricaoAtual = [];
  const matriz = [];
  const idsSnapshot = new Set();

  for (let linha = 2; linha <= mapaSnapshot.maxLinha; linha++) {
    const id = mapaSnapshot.porLinha.get(linha);
    idsSnapshot.add(id);

    const hist = historica.porId.get(id);
    if (!hist) {
      faltantesHistorico.push({ linha: linha, id: id });
      continue;
    }

    const live = atual.porId.get(id);
    if (!live) semDescricaoAtual.push({ linha: linha, id: id });

    const os = osm.porId.get(id) || { titulo: "", descricao: "" };
    matriz.push([
      id,
      hist.titulo,
      hist.categoria,
      live ? live.descricaoComposta : "",
      os.titulo,
      os.descricao
    ]);
  }

  const presentesSomenteAtual = [];
  atual.ordemIds.forEach(id => {
    if (!idsSnapshot.has(id)) presentesSomenteAtual.push(id);
  });

  const bloqueios = [];
  if (mapaSnapshot.erros.length) bloqueios.push("snapshot_invalido=" + mapaSnapshot.erros.length);
  if (historica.erros.length) bloqueios.push("fonte_historica_invalida=" + historica.erros.length);
  if (atual.erros.length) bloqueios.push("fonte_glpi_atual_invalida=" + atual.erros.length);
  if (osm.erros.length) bloqueios.push("fonte_os_invalida=" + osm.erros.length);
  if (faltantesHistorico.length) {
    bloqueios.push("ids_snapshot_ausentes_fonte_historica=" + faltantesHistorico.length);
  }
  if (semDescricaoAtual.length) {
    bloqueios.push("descricoes_historicas_nao_recuperadas=" + semDescricaoAtual.length);
  }
  if (ultimaCritica > mapaSnapshot.maxLinha) {
    bloqueios.push("dados_G_Q_sem_snapshot_ate_linha=" + ultimaCritica);
  }
  if (formulas.formulasInesperadas.length) {
    bloqueios.push("formulas_inesperadas_A_F=" + formulas.formulasInesperadas.length);
  }
  if (formulas.importrange === 0) {
    bloqueios.push("nenhum_IMPORTRANGE_encontrado_A_F");
  }
  if (matriz.length !== (mapaSnapshot.maxLinha - 1)) {
    bloqueios.push("matriz_incompleta=" + matriz.length);
  }

  return {
    apto: bloqueios.length === 0,
    bloqueios: bloqueios,
    matriz: matriz,
    faltantesHistorico: faltantesHistorico,
    semDescricaoAtual: semDescricaoAtual,
    presentesSomenteAtual: presentesSomenteAtual,
    historica: historica,
    atual: atual,
    osm: osm,
    mapaSnapshot: mapaSnapshot,
    formulas: formulas,
    ultimaCritica: ultimaCritica,
    resumo: {
      status: bloqueios.length ? "BLOQUEADA" : "APTA",
      linhasSnapshot: mapaSnapshot.maxLinha - 1,
      idsSnapshotUnicos: mapaSnapshot.idsUnicos,
      idsFonteHistorica: historica.porId.size,
      idsFonteGlpiAtual: atual.porId.size,
      idsFonteOrdensServico: osm.porId.size,
      idsSnapshotAusentesHistorico: faltantesHistorico.length,
      idsSnapshotSemDescricaoGlpiAtual: semDescricaoAtual.length,
      idsPresentesSomenteGlpiAtual: presentesSomenteAtual.length,
      formulasImportrangeAF: formulas.importrange,
      formulasInesperadasAF: formulas.formulasInesperadas.length,
      ultimaLinhaComDadosGQ: ultimaCritica,
      ultimaLinhaFisicaComConteudo: ultimaLinhaFisicaComConteudo,
      linhasResiduoAFAbaixoSnapshot: Math.max(0, ultimaLinhaFisicaComConteudo - mapaSnapshot.maxLinha),
      bloqueios: bloqueios
    }
  };
}

function montarPlanoSincronizacao_() {
  const ss = SpreadsheetApp.openById(SYNC_CFG.destSpreadsheetId);
  const principal = ss.getSheetByName(SYNC_CFG.destSheetName);
  if (!principal) throw new Error("Aba destino não encontrada.");

  const formulas = auditarFormulasImportacao_(principal, Math.max(principal.getLastRow(), 2));
  const atual = lerFonteAtualGlpi_();
  const osm = lerOrdensServico_();

  const ultimaLinha = principal.getLastRow();
  const quantidade = Math.max(ultimaLinha - 1, 0);
  const destino = quantidade ? principal.getRange(2, 1, quantidade, 6).getDisplayValues() : [];

  const porIdDestino = new Map();
  const duplicadosDestino = [];
  destino.forEach((linha, i) => {
    const id = normalizarId_(linha[0]);
    if (!id) return;
    const numeroLinha = i + 2;
    if (porIdDestino.has(id)) {
      duplicadosDestino.push({ id: id, linhas: [porIdDestino.get(id).linha, numeroLinha] });
      return;
    }
    porIdDestino.set(id, { linha: numeroLinha, valores: linha.map(texto_) });
  });

  // IDs históricos que não aparecem mais no espelho atual são PRESERVADOS.
  // Nunca excluir ou deslocar essas linhas.
  const preservadosAusentesAtual = [];
  porIdDestino.forEach((info, id) => {
    if (!atual.porId.has(id)) preservadosAusentesAtual.push(id);
  });

  const atualizacoes = [];
  const novos = [];

  atual.ordemIds.forEach(id => {
    const src = atual.porId.get(id);
    const os = osm.porId.get(id) || { titulo: "", descricao: "" };
    const desejado = [id, src.titulo, src.categoria, src.descricaoComposta, os.titulo, os.descricao];
    const existente = porIdDestino.get(id);

    if (!existente) {
      novos.push({ id: id, valores: desejado });
      return;
    }

    const antes = existente.valores;
    const depoisBF = desejado.slice(1);
    const campos = ["B", "C", "D", "E", "F"];
    const alterados = [];
    for (let i = 0; i < 5; i++) {
      if (texto_(antes[i + 1]) !== texto_(depoisBF[i])) alterados.push(campos[i]);
    }
    if (alterados.length) {
      atualizacoes.push({
        id: id,
        linha: existente.linha,
        antes: antes,
        depois: depoisBF,
        camposAlterados: alterados
      });
    }
  });

  const bloqueios = [];
  if (formulas.importrange > 0) bloqueios.push("IMPORTRANGE_ainda_presente_A_F=" + formulas.importrange);
  if (formulas.formulasInesperadas.length) bloqueios.push("formulas_inesperadas_A_F=" + formulas.formulasInesperadas.length);
  if (atual.erros.length) bloqueios.push("fonte_glpi_atual_invalida=" + atual.erros.length);
  if (osm.erros.length) bloqueios.push("fonte_os_invalida=" + osm.erros.length);
  if (duplicadosDestino.length) bloqueios.push("ids_duplicados_destino=" + duplicadosDestino.length);
  if (novos.length) bloqueios.push("inclusao_automatica_desabilitada_ids_somente_fonte_atual=" + novos.length);
  if (atualizacoes.length > SYNC_CFG.maxExistingUpdatesPerRun) {
    bloqueios.push("atualizacoes_excedem_limite=" + atualizacoes.length);
  }

  return {
    apto: bloqueios.length === 0,
    bloqueios: bloqueios,
    atualizacoes: atualizacoes,
    novos: novos,
    ultimaLinhaDestino: ultimaLinha,
    preservadosAusentesAtual: preservadosAusentesAtual,
    duplicadosDestino: duplicadosDestino,
    resumo: {
      status: bloqueios.length ? "BLOQUEADA" : "APTA",
      idsDestino: porIdDestino.size,
      idsFonteGlpiAtual: atual.porId.size,
      atualizacoes: atualizacoes.length,
      presentesSomenteFonteAtual: novos.length,
      idsHistoricosPreservadosAusentesAtual: preservadosAusentesAtual.length,
      idsDuplicadosDestino: duplicadosDestino.length,
      bloqueios: bloqueios
    }
  };
}

function lerFonteHistorica_() {
  const ss = SpreadsheetApp.openById(SYNC_CFG.historicalSpreadsheetId);
  const sh = ss.getSheetByName(SYNC_CFG.historicalSheetName);
  if (!sh) throw new Error("Aba histórica Pagina1 não encontrada.");

  const ultima = sh.getLastRow();
  if (ultima < 2) throw new Error("Fonte histórica sem dados.");
  const n = ultima - 1;

  const ids = sh.getRange(2, SYNC_CFG.historicalCols.id, n, 1).getDisplayValues();
  const titulos = sh.getRange(2, SYNC_CFG.historicalCols.titulo, n, 1).getDisplayValues();
  const categorias = sh.getRange(2, SYNC_CFG.historicalCols.categoria, n, 1).getDisplayValues();
  const subcategorias = sh.getRange(2, SYNC_CFG.historicalCols.subcategoria, n, 1).getDisplayValues();

  const porId = new Map();
  const ordemIds = [];
  const erros = [];

  for (let i = 0; i < n; i++) {
    const linha = i + 2;
    const id = normalizarId_(ids[i][0]);
    const titulo = texto_(titulos[i][0]);
    const categoriaBase = texto_(categorias[i][0]).trim();
    const subcategoria = texto_(subcategorias[i][0]).trim();

    if (!id) {
      if (titulo || categoriaBase || subcategoria) {
        erros.push("linha histórica " + linha + " contém dados sem ID");
      }
      continue;
    }
    if (porId.has(id)) {
      erros.push("ID histórico duplicado " + id + " nas linhas " + porId.get(id).linhaFonte + " e " + linha);
      continue;
    }

    const categoria = subcategoria ? categoriaBase + " > " + subcategoria : categoriaBase;
    porId.set(id, {
      id: id,
      titulo: titulo,
      categoria: categoria,
      linhaFonte: linha
    });
    ordemIds.push(id);
  }

  return { porId: porId, ordemIds: ordemIds, erros: erros, ultimaLinha: ultima };
}

function lerFonteAtualGlpi_() {
  const ss = SpreadsheetApp.openById(SYNC_CFG.currentSpreadsheetId);
  const sh = ss.getSheetByName(SYNC_CFG.currentSheetName);
  if (!sh) throw new Error("Aba GLPI atual não encontrada.");

  const ultima = sh.getLastRow();
  if (ultima < 2) throw new Error("Fonte GLPI atual sem dados.");
  const n = ultima - 1;

  const ids = sh.getRange(2, SYNC_CFG.currentCols.id, n, 1).getDisplayValues();
  const titulos = sh.getRange(2, SYNC_CFG.currentCols.titulo, n, 1).getDisplayValues();
  const categorias = sh.getRange(2, SYNC_CFG.currentCols.categoria, n, 1).getDisplayValues();
  const descricoes = sh.getRange(2, SYNC_CFG.currentCols.descricao, n, 1).getDisplayValues();
  const solucoes = sh.getRange(2, SYNC_CFG.currentCols.solucao, n, 1).getDisplayValues();

  const porId = new Map();
  const ordemIds = [];
  const erros = [];

  for (let i = 0; i < n; i++) {
    const linha = i + 2;
    const id = normalizarId_(ids[i][0]);
    const titulo = texto_(titulos[i][0]);
    const categoria = texto_(categorias[i][0]);
    const descricao = texto_(descricoes[i][0]);
    const solucao = texto_(solucoes[i][0]);

    if (!id) {
      if (titulo || categoria || descricao || solucao) {
        erros.push("linha GLPI atual " + linha + " contém dados sem ID");
      }
      continue;
    }
    if (porId.has(id)) {
      erros.push("ID GLPI atual duplicado " + id + " nas linhas " + porId.get(id).linhaFonte + " e " + linha);
      continue;
    }

    porId.set(id, {
      id: id,
      titulo: titulo,
      categoria: categoria,
      descricao: descricao,
      solucao: solucao,
      descricaoComposta: montarDescricaoGlpi_(descricao, solucao),
      linhaFonte: linha
    });
    ordemIds.push(id);
  }

  return { porId: porId, ordemIds: ordemIds, erros: erros, ultimaLinha: ultima };
}

function montarDescricaoGlpi_(descricao, solucao) {
  return "Descrição - " + texto_(descricao) + "\n\nSolução - " + texto_(solucao);
}

function lerOrdensServico_() {
  const ss = SpreadsheetApp.openById(SYNC_CFG.osSpreadsheetId);
  const sh = ss.getSheetByName(SYNC_CFG.osSheetName);
  if (!sh) throw new Error("Aba Ordens de Serviços não encontrada.");

  const ultima = sh.getLastRow();
  if (ultima < 2) return { porId: new Map(), erros: [], ultimaLinha: ultima };
  const n = ultima - 1;

  const ids = sh.getRange(2, SYNC_CFG.osCols.idChamado, n, 1).getDisplayValues();
  const titulos = sh.getRange(2, SYNC_CFG.osCols.titulo, n, 1).getDisplayValues();
  const descricoes = sh.getRange(2, SYNC_CFG.osCols.descricao, n, 1).getDisplayValues();

  const acumulado = new Map();
  const erros = [];

  for (let i = 0; i < n; i++) {
    const id = normalizarId_(ids[i][0]);
    if (!id) continue; // OS sem chamado vinculado é permitida.
    if (!acumulado.has(id)) acumulado.set(id, { titulos: [], descricoes: [] });
    const item = acumulado.get(id);
    const titulo = texto_(titulos[i][0]);
    const descricao = texto_(descricoes[i][0]);
    if (titulo) item.titulos.push(titulo);
    if (descricao) item.descricoes.push(descricao);
  }

  const porId = new Map();
  acumulado.forEach((item, id) => {
    const titulo = item.titulos.join("; ");
    const descricao = item.descricoes.join("; ");
    if (titulo.length > 49000 || descricao.length > 49000) {
      erros.push("ID " + id + " excede limite seguro de tamanho de célula em E/F");
      return;
    }
    porId.set(id, { titulo: titulo, descricao: descricao });
  });

  return { porId: porId, erros: erros, ultimaLinha: ultima };
}

function lerMapaAtualSnapshot_(snapshot) {
  const ultima = snapshot.getLastRow();
  if (ultima < 2) throw new Error("SNAPSHOT_ETAPA_1 vazio.");

  const valores = snapshot.getRange(2, 2, ultima - 1, 2).getDisplayValues(); // B:C
  const porLinha = new Map();
  const erros = [];

  valores.forEach((linha, i) => {
    const nLinha = Number(String(linha[0] || "").trim());
    const id = normalizarId_(linha[1]);
    if (!nLinha && !id) return;
    if (!Number.isInteger(nLinha) || nLinha < 2 || !id) {
      erros.push("snapshot linha física " + (i + 2) + " inválida");
      return;
    }
    // Histórico append-only: a ocorrência mais recente prevalece.
    porLinha.set(nLinha, id);
  });

  const linhas = Array.from(porLinha.keys()).sort((a, b) => a - b);
  if (!linhas.length) throw new Error("SNAPSHOT_ETAPA_1 sem mapeamento utilizável.");
  const maxLinha = linhas[linhas.length - 1];

  for (let linha = 2; linha <= maxLinha; linha++) {
    if (!porLinha.has(linha)) erros.push("linha experimental sem ID no snapshot: " + linha);
  }

  const idParaLinha = new Map();
  for (let linha = 2; linha <= maxLinha; linha++) {
    const id = porLinha.get(linha);
    if (!id) continue;
    if (idParaLinha.has(id)) {
      erros.push("ID " + id + " associado a duas linhas atuais: " + idParaLinha.get(id) + " e " + linha);
    } else {
      idParaLinha.set(id, linha);
    }
  }

  return {
    porLinha: porLinha,
    maxLinha: maxLinha,
    idsUnicos: idParaLinha.size,
    erros: erros
  };
}

function auditarFormulasImportacao_(principal, maxLinha) {
  const quantidade = Math.max(maxLinha - 1, 1);
  const formulas = principal.getRange(2, 1, quantidade, 6).getFormulas();
  let importrange = 0;
  const formulasInesperadas = [];

  formulas.forEach((linha, i) => {
    linha.forEach((formula, j) => {
      if (!formula) return;
      if (/IMPORTRANGE\s*\(/i.test(formula)) {
        importrange++;
      } else {
        formulasInesperadas.push({
          celula: colunaLetra_(j + 1) + (i + 2),
          formula: formula.slice(0, 200)
        });
      }
    });
  });

  return { importrange: importrange, formulasInesperadas: formulasInesperadas };
}

function ultimaLinhaComDados_(sheet, colunaInicial, quantidadeColunas) {
  const ultima = sheet.getLastRow();
  if (ultima < 2) return 1;
  const valores = sheet.getRange(2, colunaInicial, ultima - 1, quantidadeColunas).getDisplayValues();
  for (let i = valores.length - 1; i >= 0; i--) {
    if (valores[i].some(v => String(v || "").trim() !== "")) return i + 2;
  }
  return 1;
}

function validarIdsDestino_(principal) {
  const ultima = principal.getLastRow();
  if (ultima < 2) return;
  const ids = principal.getRange(2, 1, ultima - 1, 1).getDisplayValues();
  const vistos = new Set();
  for (let i = 0; i < ids.length; i++) {
    const id = normalizarId_(ids[i][0]);
    if (!id) continue;
    if (vistos.has(id)) {
      throw new Error("PÓS-CONDIÇÃO FALHOU: ID duplicado no destino: " + id);
    }
    vistos.add(id);
  }
}

function escreverPreviewMigracao_(plano) {
  const ss = SpreadsheetApp.openById(SYNC_CFG.destSpreadsheetId);
  const sh = obterOuCriarAba_(ss, SYNC_CFG.previewSheetName);
  sh.clearContents();

  const linhas = [
    ["AUTORIZACAO", ""],
    ["INSTRUCAO", "Somente se STATUS=APTA, escreva " + SYNC_CFG.authorizationValue + " em B1 para permitir a migração."],
    ["STATUS", plano.apto ? "APTA" : "BLOQUEADA"],
    ["DATA_PREFLIGHT", agora_()],
    ["LINHAS_SNAPSHOT", plano.resumo.linhasSnapshot],
    ["IDS_SNAPSHOT_UNICOS", plano.resumo.idsSnapshotUnicos],
    ["IDS_FONTE_HISTORICA", plano.resumo.idsFonteHistorica],
    ["IDS_FONTE_GLPI_ATUAL", plano.resumo.idsFonteGlpiAtual],
    ["IDS_FONTE_OS", plano.resumo.idsFonteOrdensServico],
    ["IDS_SNAPSHOT_AUSENTES_HISTORICO", plano.resumo.idsSnapshotAusentesHistorico],
    ["IDS_SNAPSHOT_SEM_DESCRICAO_GLPI_ATUAL", plano.resumo.idsSnapshotSemDescricaoGlpiAtual],
    ["IDS_PRESENTES_SOMENTE_GLPI_ATUAL", plano.resumo.idsPresentesSomenteGlpiAtual],
    ["FORMULAS_IMPORTRANGE_A_F", plano.resumo.formulasImportrangeAF],
    ["FORMULAS_INESPERADAS_A_F", plano.resumo.formulasInesperadasAF],
    ["ULTIMA_LINHA_DADOS_G_Q", plano.resumo.ultimaLinhaComDadosGQ],
    ["ULTIMA_LINHA_FISICA_COM_CONTEUDO", plano.resumo.ultimaLinhaFisicaComConteudo],
    ["LINHAS_RESIDUO_A_F_ABAIXO_SNAPSHOT", plano.resumo.linhasResiduoAFAbaixoSnapshot],
    ["BLOQUEIOS", plano.bloqueios.join(" | ")]
  ];
  sh.getRange(1, 1, linhas.length, 2).setValues(linhas);
  sh.setFrozenRows(2);

  let row = linhas.length + 2;
  sh.getRange(row, 1, 1, 3).setValues([["TIPO", "LINHA/ID", "DETALHE"]]);
  row++;

  plano.faltantesHistorico.slice(0, 200).forEach(x => {
    sh.getRange(row++, 1, 1, 3).setValues([["FALTANTE_HISTORICO", x.linha + "/" + x.id, "bloqueia migração"]]);
  });
  plano.semDescricaoAtual.slice(0, 200).forEach(x => {
    sh.getRange(row++, 1, 1, 3).setValues([["SEM_DESCRICAO_GLPI_ATUAL", x.linha + "/" + x.id, "linha preservada; D ficará vazio"]]);
  });
  plano.presentesSomenteAtual.slice(0, 200).forEach(id => {
    sh.getRange(row++, 1, 1, 3).setValues([["PRESENTE_SOMENTE_GLPI_ATUAL", id, "não entra na migração e não será incluído automaticamente; exige revisão da origem"]]);
  });
  plano.formulas.formulasInesperadas.slice(0, 100).forEach(x => {
    sh.getRange(row++, 1, 1, 3).setValues([["FORMULA_INESPERADA", x.celula, x.formula]]);
  });

  sh.autoResizeColumns(1, 3);
}

function escreverPreviewSincronizacao_(plano) {
  const ss = SpreadsheetApp.openById(SYNC_CFG.destSpreadsheetId);
  const sh = obterOuCriarAba_(ss, SYNC_CFG.previewSheetName);
  sh.clearContents();

  const linhas = [
    ["MODO", "SIMULACAO_SINCRONIZACAO"],
    ["STATUS", plano.apto ? "APTA" : "BLOQUEADA"],
    ["DATA", agora_()],
    ["IDS_DESTINO", plano.resumo.idsDestino],
    ["IDS_FONTE_GLPI_ATUAL", plano.resumo.idsFonteGlpiAtual],
    ["ATUALIZACOES", plano.resumo.atualizacoes],
    ["PRESENTES_SOMENTE_FONTE_ATUAL", plano.resumo.presentesSomenteFonteAtual],
    ["IDS_HISTORICOS_PRESERVADOS_AUSENTES_ATUAL", plano.resumo.idsHistoricosPreservadosAusentesAtual],
    ["IDS_DUPLICADOS_DESTINO", plano.resumo.idsDuplicadosDestino],
    ["BLOQUEIOS", plano.bloqueios.join(" | ")]
  ];
  sh.getRange(1, 1, linhas.length, 2).setValues(linhas);

  let row = linhas.length + 2;
  sh.getRange(row++, 1, 1, 4).setValues([["TIPO", "ID", "LINHA", "CAMPOS"]]);
  plano.atualizacoes.slice(0, 200).forEach(x => {
    sh.getRange(row++, 1, 1, 4).setValues([["ATUALIZAR", x.id, x.linha, x.camposAlterados.join(",")]]);
  });
  plano.novos.slice(0, 200).forEach(x => {
    sh.getRange(row++, 1, 1, 4).setValues([["NOVO", x.id, "", "A:F"]]);
  });
  sh.autoResizeColumns(1, 4);
}

function criarBackupAba_(ss, principal) {
  const nome = SYNC_CFG.backupPrefix + Utilities.formatDate(new Date(), SYNC_CFG.timeZone, "yyyyMMdd_HHmmss");
  if (ss.getSheetByName(nome)) throw new Error("Já existe backup com o nome " + nome);
  const backup = principal.copyTo(ss).setName(nome);
  backup.hideSheet();
  return nome;
}

function obterLog_(ss) {
  let sh = ss.getSheetByName(SYNC_CFG.logSheetName);
  if (!sh) {
    sh = ss.insertSheet(SYNC_CFG.logSheetName);
    sh.getRange(1, 1, 1, 7).setValues([[
      "data_hora", "operacao", "id_chamado", "linha_destino",
      "categoria_antes", "categoria_depois", "detalhe"
    ]]);
    sh.setFrozenRows(1);
  }
  return sh;
}

function anexarLogResumo_(ss, operacao, id, antes, depois, detalhe) {
  obterLog_(ss).appendRow([agora_(), operacao, id, "", antes, depois, detalhe]);
}

function obterOuCriarAba_(ss, nome) {
  return ss.getSheetByName(nome) || ss.insertSheet(nome);
}

function compararMatrizes_(esperado, lido, limite) {
  const divergencias = [];
  for (let i = 0; i < esperado.length; i++) {
    for (let j = 0; j < esperado[i].length; j++) {
      if (texto_(esperado[i][j]) !== texto_(lido[i][j])) {
        divergencias.push({
          linha: i + 2,
          coluna: colunaLetra_(j + 1),
          esperado: texto_(esperado[i][j]).slice(0, 120),
          lido: texto_(lido[i][j]).slice(0, 120)
        });
        if (divergencias.length >= limite) return divergencias;
      }
    }
  }
  return divergencias;
}

function normalizarId_(valor) {
  const s = String(valor == null ? "" : valor).trim();
  return s.replace(/\.0$/, "");
}

function texto_(valor) {
  return String(valor == null ? "" : valor);
}

function valorLiteral_(valor) {
  const s = texto_(valor);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function agora_() {
  return Utilities.formatDate(new Date(), SYNC_CFG.timeZone, "yyyy-MM-dd HH:mm:ss");
}

function colunaLetra_(n) {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function withScriptLock_(fn) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    throw new Error("LOCK_OCUPADO: outra execução de sincronização está em andamento.");
  }
  try {
    return fn();
  } finally {
    lock.releaseLock();
  }
}
