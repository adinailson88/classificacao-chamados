/**
 * PILOTO SEGURO — elimina IMPORTRANGE de COPIA!A:F.
 *
 * Escopo rígido:
 * - destino: somente aba COPIA;
 * - escrita: somente A:F;
 * - G:Q são lidas antes/depois e devem permanecer idênticas;
 * - chave lógica: ID Chamado;
 * - migração inicial usa SNAPSHOT_ETAPA_1 para preservar linha -> ID;
 * - 69 descrições recuperadas do GLPI ficam em aba privada/oculta
 *   COPIA_GLPI_FALLBACK, nunca versionadas neste repositório.
 *
 * Fluxo:
 *   1) preflightCopiaSemImportrange()
 *   2) revisar PREVIEW_COPIA_A_F
 *   3) escrever APLICAR_COPIA em PREVIEW_COPIA_A_F!B1
 *   4) aplicarCopiaSemImportrange()
 *   5) somente depois: simularSincronizacaoCopiaPorId()
 */

const COPIA_SYNC_CFG = Object.freeze({
  historicalSpreadsheetId: "1xnU5sDcEWrDjs_trU3tC0jOHCljp7o_SmRNvyJzqkUg",
  historicalSheetName: "Pagina1",
  historicalCols: Object.freeze({ id: 1, titulo: 2, categoria: 5, subcategoria: 6 }),

  currentSpreadsheetId: "15_fsbXktpvRGJ3OTq2NsWvjMztF4IYiRQmgRASlVWIQ",
  currentSheetName: "GLPI",
  currentCols: Object.freeze({
    id: 1,
    titulo: 2,
    categoria: 6,
    descricao: 17,
    solucao: 19
  }),

  osSpreadsheetId: "1zTSo5oTFDyo3espWmYl1WjpFU57PwHDeZqnxUkrGQ2Y",
  osSheetName: "Ordens de Serviços",
  osCols: Object.freeze({ idChamado: 2, titulo: 3, descricao: 5 }),

  destSpreadsheetId: "1lohPUQOgxzt_DMxnNLKMxnieZq1sVmh4uwBLbbgvfiQ",
  destSheetName: "COPIA",
  snapshotSheetName: "SNAPSHOT_ETAPA_1",
  fallbackSheetName: "COPIA_GLPI_FALLBACK",

  previewSheetName: "PREVIEW_COPIA_A_F",
  logSheetName: "LOG_COPIA_A_F",
  backupPrefix: "BACKUP_COPIA_AF_",

  authorizationCell: "B1",
  authorizationValue: "APLICAR_COPIA",

  // Inclusão automática de IDs que existem apenas no espelho atual permanece
  // desabilitada enquanto a origem dos 55 IDs divergentes não estiver validada.
  allowNewIds: false,

  maxExistingUpdatesPerRun: 1000,
  triggerEveryHours: 2,
  timeZone: "America/Bahia"
});


function preflightCopiaSemImportrange() {
  return copia_withLock_(function () {
    const plano = copia_montarPlanoMigracao_();
    copia_escreverPreviewMigracao_(plano);
    Logger.log(JSON.stringify(plano.resumo));
    return plano.resumo;
  });
}


function aplicarCopiaSemImportrange() {
  return copia_withLock_(function () {
    const ss = SpreadsheetApp.openById(COPIA_SYNC_CFG.destSpreadsheetId);
    const preview = ss.getSheetByName(COPIA_SYNC_CFG.previewSheetName);
    if (!preview) {
      throw new Error("PREVIEW_AUSENTE: execute preflightCopiaSemImportrange() antes.");
    }

    const autorizacao = String(
      preview.getRange(COPIA_SYNC_CFG.authorizationCell).getDisplayValue() || ""
    ).trim();

    if (autorizacao !== COPIA_SYNC_CFG.authorizationValue) {
      throw new Error(
        "SEM_AUTORIZACAO: escreva " + COPIA_SYNC_CFG.authorizationValue +
        " em " + COPIA_SYNC_CFG.previewSheetName + "!" +
        COPIA_SYNC_CFG.authorizationCell + "."
      );
    }

    // Nunca aplica com base em preview antigo.
    const plano = copia_montarPlanoMigracao_();
    copia_escreverPreviewMigracao_(plano);

    if (!plano.apto) {
      throw new Error(
        "MIGRACAO_COPIA_BLOQUEADA: " + plano.bloqueios.join(" | ")
      );
    }

    const destino = ss.getSheetByName(COPIA_SYNC_CFG.destSheetName);
    if (!destino) throw new Error("Aba COPIA não encontrada.");

    const ultimaAntes = Math.max(destino.getLastRow(), plano.maxLinha);
    const quantidadeGQ = Math.max(ultimaAntes - 1, 0);
    const gqAntes = quantidadeGQ
      ? destino.getRange(2, 7, quantidadeGQ, 11).getDisplayValues()
      : [];

    const backupName = copia_criarBackup_(ss, destino);

    const rangeAF = destino.getRange(2, 1, plano.matriz.length, 6);
    rangeAF.setNumberFormat("@");
    rangeAF.setValues(
      plano.matriz.map(function (linha) {
        return linha.map(copia_valorLiteral_);
      })
    );

    // Elimina resíduos/fórmulas A:F abaixo do universo validado do snapshot,
    // somente porque o preflight já garantiu ausência de dados G:Q nessa área.
    let linhasResiduoLimpas = 0;
    if (ultimaAntes > plano.maxLinha) {
      linhasResiduoLimpas = ultimaAntes - plano.maxLinha;
      destino
        .getRange(plano.maxLinha + 1, 1, linhasResiduoLimpas, 6)
        .clearContent();
    }

    SpreadsheetApp.flush();

    const afDepois = destino
      .getRange(2, 1, plano.matriz.length, 6)
      .getDisplayValues();

    const divergenciasAF = copia_compararMatrizes_(
      plano.matriz,
      afDepois,
      30
    );

    const gqDepois = quantidadeGQ
      ? destino.getRange(2, 7, quantidadeGQ, 11).getDisplayValues()
      : [];

    const divergenciasGQ = copia_compararMatrizes_(
      gqAntes,
      gqDepois,
      10
    );

    const auditoriaFormulas = copia_auditarFormulasAF_(
      destino,
      Math.max(destino.getLastRow(), plano.maxLinha)
    );

    if (
      divergenciasAF.length ||
      divergenciasGQ.length ||
      auditoriaFormulas.total > 0
    ) {
      copia_anexarLog_(
        ss,
        "MIGRACAO_FALHA_READBACK",
        "",
        "",
        "",
        "backup=" + backupName +
          "; divergencias_AF=" + JSON.stringify(divergenciasAF) +
          "; divergencias_GQ=" + JSON.stringify(divergenciasGQ) +
          "; formulas_AF=" + auditoriaFormulas.total
      );

      throw new Error(
        "READBACK_DIVERGENTE: a validação pós-escrita falhou. " +
        "Backup preservado em " + backupName + "."
      );
    }

    copia_anexarLog_(
      ss,
      "MIGRACAO_COPIA_CONCLUIDA",
      "",
      "FORMULAS",
      "VALORES",
      "linhas=" + plano.matriz.length +
        "; residuos_A_F_limpos=" + linhasResiduoLimpas +
        "; backup=" + backupName
    );

    preview.getRange(COPIA_SYNC_CFG.authorizationCell).clearContent();
    preview.getRange("B3").setValue("CONCLUIDA");
    preview.getRange("B4").setValue(copia_agora_());
    preview.getRange("A5").setValue("BACKUP");
    preview.getRange("B5").setValue(backupName);

    return {
      status: "CONCLUIDA",
      linhasMaterializadas: plano.matriz.length,
      formulasAFDepois: auditoriaFormulas.total,
      divergenciasGQ: divergenciasGQ.length,
      backup: backupName
    };
  });
}


function simularSincronizacaoCopiaPorId() {
  return copia_withLock_(function () {
    const plano = copia_montarPlanoSincronizacao_();
    copia_escreverPreviewSincronizacao_(plano);
    Logger.log(JSON.stringify(plano.resumo));
    return plano.resumo;
  });
}


function sincronizarCopiaPorId() {
  return copia_withLock_(function () {
    const plano = copia_montarPlanoSincronizacao_();
    copia_escreverPreviewSincronizacao_(plano);

    if (!plano.apto) {
      throw new Error(
        "SINCRONIZACAO_COPIA_BLOQUEADA: " + plano.bloqueios.join(" | ")
      );
    }

    const ss = SpreadsheetApp.openById(COPIA_SYNC_CFG.destSpreadsheetId);
    const destino = ss.getSheetByName(COPIA_SYNC_CFG.destSheetName);
    if (!destino) throw new Error("Aba COPIA não encontrada.");

    const ultima = destino.getLastRow();
    const qtdGQ = Math.max(ultima - 1, 0);
    const gqAntes = qtdGQ
      ? destino.getRange(2, 7, qtdGQ, 11).getDisplayValues()
      : [];

    const log = copia_obterLog_(ss);

    plano.atualizacoes
      .slice()
      .sort(function (a, b) { return a.linha - b.linha; })
      .forEach(function (item) {
        // A é a chave e não é alterada.
        const range = destino.getRange(item.linha, 2, 1, 5);
        range.setNumberFormat("@");
        range.setValues([item.depois.map(copia_valorLiteral_)]);
        log.appendRow([
          copia_agora_(),
          "ATUALIZADO",
          item.id,
          item.linha,
          item.antes[2],
          item.depois[1],
          "campos=" + item.camposAlterados.join(",")
        ]);
      });

    // Por decisão de segurança, IDs somente na fonte atual não são inseridos
    // enquanto allowNewIds=false.
    if (COPIA_SYNC_CFG.allowNewIds && plano.novos.length) {
      const primeira = destino.getLastRow() + 1;
      const necessario = primeira + plano.novos.length - 1;
      if (necessario > destino.getMaxRows()) {
        destino.insertRowsAfter(
          destino.getMaxRows(),
          necessario - destino.getMaxRows()
        );
      }

      const valores = plano.novos.map(function (x) {
        return x.valores.map(copia_valorLiteral_);
      });
      destino
        .getRange(primeira, 1, valores.length, 6)
        .setNumberFormat("@")
        .setValues(valores);

      plano.novos.forEach(function (item, i) {
        log.appendRow([
          copia_agora_(),
          "NOVO",
          item.id,
          primeira + i,
          "",
          item.valores[2],
          "A:F inseridos; G:Q permaneceram vazios"
        ]);
      });
    }

    SpreadsheetApp.flush();

    const gqDepois = qtdGQ
      ? destino.getRange(2, 7, qtdGQ, 11).getDisplayValues()
      : [];

    const divergenciasGQ = copia_compararMatrizes_(
      gqAntes,
      gqDepois,
      10
    );
    if (divergenciasGQ.length) {
      throw new Error(
        "PÓS-CONDIÇÃO FALHOU: G:Q mudaram durante a sincronização: " +
        JSON.stringify(divergenciasGQ)
      );
    }

    copia_validarIdsDestino_(destino);

    return {
      status: "APLICADO",
      atualizados: plano.atualizacoes.length,
      novosInseridos: COPIA_SYNC_CFG.allowNewIds ? plano.novos.length : 0,
      novosIgnorados: COPIA_SYNC_CFG.allowNewIds ? 0 : plano.novos.length
    };
  });
}


function instalarGatilhoCopiaPorId() {
  removerGatilhoCopiaPorId();
  ScriptApp.newTrigger("sincronizarCopiaPorId")
    .timeBased()
    .everyHours(COPIA_SYNC_CFG.triggerEveryHours)
    .create();
}


function removerGatilhoCopiaPorId() {
  ScriptApp.getProjectTriggers()
    .filter(function (t) {
      return t.getHandlerFunction() === "sincronizarCopiaPorId";
    })
    .forEach(function (t) {
      ScriptApp.deleteTrigger(t);
    });
}


function copia_montarPlanoMigracao_() {
  const ss = SpreadsheetApp.openById(COPIA_SYNC_CFG.destSpreadsheetId);
  const destino = ss.getSheetByName(COPIA_SYNC_CFG.destSheetName);
  const snapshot = ss.getSheetByName(COPIA_SYNC_CFG.snapshotSheetName);
  if (!destino || !snapshot) {
    throw new Error("Aba COPIA ou SNAPSHOT_ETAPA_1 não encontrada.");
  }

  const mapaSnapshot = copia_lerMapaSnapshot_(snapshot);
  const historica = copia_lerFonteHistorica_();

  // As fontes abaixo são auditadas agora para garantir que a sincronização
  // posterior por ID está disponível, mas NÃO substituem valores na migração
  // inicial. A primeira migração apenas materializa exatamente o que já está
  // visível em COPIA!A:F.
  const atual = copia_lerFonteGlpiAtual_();
  const osm = copia_lerOrdensServico_();
  const fallback = copia_lerFallback_(ss);

  const quantidade = mapaSnapshot.maxLinha - 1;
  const atualAF = destino
    .getRange(2, 1, quantidade, 6)
    .getDisplayValues();

  const ultimaFisica = Math.max(destino.getLastRow(), mapaSnapshot.maxLinha);
  const formulas = copia_auditarFormulasAF_(destino, ultimaFisica);
  const ultimaGQ = copia_ultimaLinhaComDados_(destino, 7, 11);

  const idsSnapshot = new Set();
  const faltantesHistorico = [];
  const idsLinhaDivergente = [];
  const divergenciasTitulo = [];
  const divergenciasCategoria = [];
  const errosVisiveisAF = [];
  const ausentesGlpiSemFallback = [];
  const descricoesVaziasFinais = [];
  const matriz = [];

  for (let linha = 2; linha <= mapaSnapshot.maxLinha; linha++) {
    const idx = linha - 2;
    const id = mapaSnapshot.porLinha.get(linha);
    idsSnapshot.add(id);

    const existente = atualAF[idx] || ["", "", "", "", "", ""];
    const idExistente = copia_normalizarId_(existente[0]);

    if (idExistente !== id) {
      idsLinhaDivergente.push({
        linha: linha,
        snapshot: id,
        copia: idExistente
      });
    }

    const hist = historica.porId.get(id);
    if (!hist) {
      faltantesHistorico.push({ linha: linha, id: id });
    } else {
      if (copia_texto_(existente[1]) !== copia_texto_(hist.titulo)) {
        divergenciasTitulo.push({
          linha: linha,
          id: id,
          copia: copia_texto_(existente[1]),
          fonte: copia_texto_(hist.titulo)
        });
      }

      if (copia_texto_(existente[2]) !== copia_texto_(hist.categoria)) {
        divergenciasCategoria.push({
          linha: linha,
          id: id,
          copia: copia_texto_(existente[2]),
          fonte: copia_texto_(hist.categoria)
        });
      }
    }

    for (let col = 0; col < 6; col++) {
      const valor = copia_texto_(existente[col]);
      if (copia_eErroPlanilha_(valor)) {
        errosVisiveisAF.push({
          linha: linha,
          coluna: copia_colunaLetra_(col + 1),
          id: id,
          valor: valor
        });
      }
    }

    const live = atual.porId.get(id);
    const fallbackD = fallback.porId.get(id) || "";
    if (!live && !fallbackD) {
      ausentesGlpiSemFallback.push({ linha: linha, id: id });
    }

    if (!copia_texto_(existente[3]).trim()) {
      descricoesVaziasFinais.push({ linha: linha, id: id });
    }

    // Materialização estritamente conservadora:
    // A vem do snapshot (já validado contra a COPIA);
    // B:F são exatamente os valores atualmente exibidos.
    matriz.push([
      id,
      copia_texto_(existente[1]),
      copia_texto_(existente[2]),
      copia_texto_(existente[3]),
      copia_texto_(existente[4]),
      copia_texto_(existente[5])
    ]);
  }

  const somenteAtual = [];
  atual.ordemIds.forEach(function (id) {
    if (!idsSnapshot.has(id)) somenteAtual.push(id);
  });

  const bloqueios = [];
  if (mapaSnapshot.erros.length) {
    bloqueios.push("snapshot_invalido=" + mapaSnapshot.erros.length);
  }
  if (historica.erros.length) {
    bloqueios.push("fonte_historica_invalida=" + historica.erros.length);
  }
  if (faltantesHistorico.length) {
    bloqueios.push(
      "ids_snapshot_ausentes_fonte_historica=" + faltantesHistorico.length
    );
  }
  if (idsLinhaDivergente.length) {
    bloqueios.push(
      "ids_COPIA_divergem_snapshot=" + idsLinhaDivergente.length
    );
  }
  if (divergenciasTitulo.length) {
    bloqueios.push(
      "titulos_COPIA_divergem_fonte_historica=" +
      divergenciasTitulo.length
    );
  }
  if (divergenciasCategoria.length) {
    bloqueios.push(
      "categorias_COPIA_divergem_fonte_historica=" +
      divergenciasCategoria.length
    );
  }
  if (errosVisiveisAF.length) {
    bloqueios.push(
      "erros_visiveis_A_F=" + errosVisiveisAF.length
    );
  }
  if (ultimaGQ > mapaSnapshot.maxLinha) {
    bloqueios.push("dados_G_Q_sem_snapshot_ate_linha=" + ultimaGQ);
  }
  if (matriz.length !== quantidade) {
    bloqueios.push("matriz_incompleta=" + matriz.length);
  }

  return {
    apto: bloqueios.length === 0,
    bloqueios: bloqueios,
    matriz: matriz,
    maxLinha: mapaSnapshot.maxLinha,
    mapaSnapshot: mapaSnapshot,
    historica: historica,
    atual: atual,
    osm: osm,
    fallback: fallback,
    formulas: formulas,
    faltantesHistorico: faltantesHistorico,
    idsLinhaDivergente: idsLinhaDivergente,
    divergenciasTitulo: divergenciasTitulo,
    divergenciasCategoria: divergenciasCategoria,
    errosVisiveisAF: errosVisiveisAF,
    ausentesGlpiSemFallback: ausentesGlpiSemFallback,
    descricoesVaziasFinais: descricoesVaziasFinais,
    somenteAtual: somenteAtual,
    diferencas: [],
    ultimaGQ: ultimaGQ,
    ultimaFisica: ultimaFisica,
    resumo: {
      status: bloqueios.length ? "BLOQUEADA" : "APTA",
      linhasSnapshot: quantidade,
      idsSnapshotUnicos: mapaSnapshot.idsUnicos,
      idsFonteHistorica: historica.porId.size,
      idsFonteGlpiAtual: atual.porId.size,
      idsFonteOS: osm.porId.size,
      idsFallbackDescricao: fallback.porId.size,
      idsSnapshotAusentesHistorico: faltantesHistorico.length,
      idsCopiaDivergemSnapshot: idsLinhaDivergente.length,
      titulosDivergemHistorico: divergenciasTitulo.length,
      categoriasDivergemHistorico: divergenciasCategoria.length,
      errosVisiveisAF: errosVisiveisAF.length,
      idsSemGlpiESemFallback: ausentesGlpiSemFallback.length,
      descricoesVaziasFinais: descricoesVaziasFinais.length,
      idsSomenteFonteAtual: somenteAtual.length,
      formulasAF: formulas.total,
      importrangeAF: formulas.importrange,
      formulasLocaisAF: formulas.locais,
      ultimaLinhaDadosGQ: ultimaGQ,
      ultimaLinhaFisica: ultimaFisica,
      linhasResiduoAFAbaixoSnapshot: Math.max(
        0,
        ultimaFisica - mapaSnapshot.maxLinha
      ),
      diferencasAFDetectadas: 0,
      bloqueios: bloqueios
    }
  };
}


function copia_montarPlanoSincronizacao_() {
  const ss = SpreadsheetApp.openById(COPIA_SYNC_CFG.destSpreadsheetId);
  const destino = ss.getSheetByName(COPIA_SYNC_CFG.destSheetName);
  if (!destino) throw new Error("Aba COPIA não encontrada.");

  const formulas = copia_auditarFormulasAF_(
    destino,
    Math.max(destino.getLastRow(), 2)
  );

  const historica = copia_lerFonteHistorica_();
  const atual = copia_lerFonteGlpiAtual_();
  const osm = copia_lerOrdensServico_();
  const fallback = copia_lerFallback_(ss);

  const ultima = destino.getLastRow();
  const quantidade = Math.max(ultima - 1, 0);
  const valores = quantidade
    ? destino.getRange(2, 1, quantidade, 6).getDisplayValues()
    : [];

  const porIdDestino = new Map();
  const duplicados = [];

  valores.forEach(function (linha, i) {
    const id = copia_normalizarId_(linha[0]);
    if (!id) return;
    const nLinha = i + 2;
    if (porIdDestino.has(id)) {
      duplicados.push({
        id: id,
        linhas: [porIdDestino.get(id).linha, nLinha]
      });
      return;
    }
    porIdDestino.set(id, {
      linha: nLinha,
      valores: linha.map(copia_texto_)
    });
  });

  const atualizacoes = [];
  const novos = [];

  atual.ordemIds.forEach(function (id) {
    const live = atual.porId.get(id);
    const hist = historica.porId.get(id);
    const os = osm.porId.get(id) || { titulo: "", descricao: "" };

    const titulo = live && live.titulo
      ? live.titulo
      : (hist ? hist.titulo : "");

    const categoria = live && live.categoria
      ? live.categoria
      : (hist ? hist.categoria : "");

    const existente = porIdDestino.get(id);
    const descricao = copia_resolverDescricaoSincronizacao_(
      live,
      existente,
      fallback.porId.get(id) || ""
    );

    const desejado = [
      id,
      titulo,
      categoria,
      descricao,
      os.titulo,
      os.descricao
    ];

    if (!existente) {
      novos.push({ id: id, valores: desejado });
      return;
    }

    const campos = ["B", "C", "D", "E", "F"];
    const depois = desejado.slice(1);
    const alterados = [];

    for (let i = 0; i < 5; i++) {
      const antesComparavel = i === 1
        ? copia_texto_(existente.valores[i + 1])
        : copia_textoComparavel_(existente.valores[i + 1]);
      const depoisComparavel = i === 1
        ? copia_texto_(depois[i])
        : copia_textoComparavel_(depois[i]);

      if (antesComparavel !== depoisComparavel) {
        alterados.push(campos[i]);
      }
    }

    if (alterados.length) {
      atualizacoes.push({
        id: id,
        linha: existente.linha,
        antes: existente.valores,
        depois: depois,
        camposAlterados: alterados
      });
    }
  });

  const preservadosAusentesAtual = [];
  porIdDestino.forEach(function (info, id) {
    if (!atual.porId.has(id)) {
      preservadosAusentesAtual.push(id);
    }
  });

  const bloqueios = [];
  if (formulas.total > 0) {
    bloqueios.push("formulas_ainda_presentes_A_F=" + formulas.total);
  }
  if (historica.erros.length) {
    bloqueios.push("fonte_historica_invalida=" + historica.erros.length);
  }
  if (atual.erros.length) {
    bloqueios.push("fonte_glpi_atual_invalida=" + atual.erros.length);
  }
  if (osm.erros.length) {
    bloqueios.push("fonte_os_invalida=" + osm.erros.length);
  }
  if (fallback.erros.length) {
    bloqueios.push("fallback_invalido=" + fallback.erros.length);
  }
  if (duplicados.length) {
    bloqueios.push("ids_duplicados_COPIA=" + duplicados.length);
  }
  if (atualizacoes.length > COPIA_SYNC_CFG.maxExistingUpdatesPerRun) {
    bloqueios.push(
      "atualizacoes_excedem_limite=" + atualizacoes.length
    );
  }
  if (COPIA_SYNC_CFG.allowNewIds && novos.length > 100) {
    bloqueios.push("novos_ids_excedem_limite=" + novos.length);
  }

  return {
    apto: bloqueios.length === 0,
    bloqueios: bloqueios,
    atualizacoes: atualizacoes,
    novos: novos,
    preservadosAusentesAtual: preservadosAusentesAtual,
    duplicados: duplicados,
    resumo: {
      status: bloqueios.length ? "BLOQUEADA" : "APTA",
      idsDestino: porIdDestino.size,
      idsFonteGlpiAtual: atual.porId.size,
      atualizacoes: atualizacoes.length,
      idsSomenteFonteAtual: novos.length,
      inclusaoNovosHabilitada: COPIA_SYNC_CFG.allowNewIds,
      idsHistoricosPreservadosAusentesAtual:
        preservadosAusentesAtual.length,
      idsDuplicadosDestino: duplicados.length,
      formulasAF: formulas.total,
      bloqueios: bloqueios
    }
  };
}


function copia_lerFonteHistorica_() {
  const ss = SpreadsheetApp.openById(
    COPIA_SYNC_CFG.historicalSpreadsheetId
  );
  const sh = ss.getSheetByName(COPIA_SYNC_CFG.historicalSheetName);
  if (!sh) throw new Error("Aba histórica Pagina1 não encontrada.");

  const ultima = sh.getLastRow();
  if (ultima < 2) throw new Error("Fonte histórica sem dados.");

  const valores = sh.getRange(2, 1, ultima - 1, 6).getDisplayValues();
  const porId = new Map();
  const ordemIds = [];
  const erros = [];

  valores.forEach(function (linha, i) {
    const nLinha = i + 2;
    const id = copia_normalizarId_(
      linha[COPIA_SYNC_CFG.historicalCols.id - 1]
    );
    const titulo = copia_texto_(
      linha[COPIA_SYNC_CFG.historicalCols.titulo - 1]
    );
    const cat = copia_texto_(
      linha[COPIA_SYNC_CFG.historicalCols.categoria - 1]
    ).trim();
    const sub = copia_texto_(
      linha[COPIA_SYNC_CFG.historicalCols.subcategoria - 1]
    ).trim();

    if (!id) {
      if (titulo || cat || sub) {
        erros.push("linha histórica " + nLinha + " com dados sem ID");
      }
      return;
    }

    if (porId.has(id)) {
      erros.push(
        "ID histórico duplicado " + id + " nas linhas " +
        porId.get(id).linhaFonte + " e " + nLinha
      );
      return;
    }

    const categoria = sub ? cat + " > " + sub : cat;
    porId.set(id, {
      id: id,
      titulo: titulo,
      categoria: categoria,
      linhaFonte: nLinha
    });
    ordemIds.push(id);
  });

  return {
    porId: porId,
    ordemIds: ordemIds,
    erros: erros,
    ultimaLinha: ultima
  };
}


function copia_lerFonteGlpiAtual_() {
  const ss = SpreadsheetApp.openById(COPIA_SYNC_CFG.currentSpreadsheetId);
  const sh = ss.getSheetByName(COPIA_SYNC_CFG.currentSheetName);
  if (!sh) throw new Error("Aba GLPI atual não encontrada.");

  const ultima = sh.getLastRow();
  if (ultima < 2) throw new Error("Fonte GLPI atual sem dados.");

  const valores = sh.getRange(2, 1, ultima - 1, 19).getDisplayValues();
  const porId = new Map();
  const ordemIds = [];
  const erros = [];

  valores.forEach(function (linha, i) {
    const nLinha = i + 2;
    const id = copia_normalizarId_(
      linha[COPIA_SYNC_CFG.currentCols.id - 1]
    );
    const titulo = copia_texto_(
      linha[COPIA_SYNC_CFG.currentCols.titulo - 1]
    );
    const categoria = copia_texto_(
      linha[COPIA_SYNC_CFG.currentCols.categoria - 1]
    );
    const descricao = copia_texto_(
      linha[COPIA_SYNC_CFG.currentCols.descricao - 1]
    );
    const solucao = copia_texto_(
      linha[COPIA_SYNC_CFG.currentCols.solucao - 1]
    );

    if (!id) {
      if (titulo || categoria || descricao || solucao) {
        erros.push("linha GLPI " + nLinha + " com dados sem ID");
      }
      return;
    }

    if (porId.has(id)) {
      erros.push(
        "ID GLPI duplicado " + id + " nas linhas " +
        porId.get(id).linhaFonte + " e " + nLinha
      );
      return;
    }

    porId.set(id, {
      id: id,
      titulo: titulo,
      categoria: categoria,
      descricao: descricao,
      solucao: solucao,
      descricaoComposta: copia_montarDescricaoGlpi_(descricao, solucao),
      linhaFonte: nLinha
    });
    ordemIds.push(id);
  });

  return {
    porId: porId,
    ordemIds: ordemIds,
    erros: erros,
    ultimaLinha: ultima
  };
}


function copia_lerOrdensServico_() {
  const ss = SpreadsheetApp.openById(COPIA_SYNC_CFG.osSpreadsheetId);
  const sh = ss.getSheetByName(COPIA_SYNC_CFG.osSheetName);
  if (!sh) throw new Error("Aba Ordens de Serviços não encontrada.");

  const ultima = sh.getLastRow();
  if (ultima < 2) {
    return { porId: new Map(), erros: [], ultimaLinha: ultima };
  }

  const valores = sh.getRange(2, 1, ultima - 1, 5).getDisplayValues();
  const acumulado = new Map();
  const erros = [];

  valores.forEach(function (linha) {
    const id = copia_normalizarId_(
      linha[COPIA_SYNC_CFG.osCols.idChamado - 1]
    );
    if (!id) return;

    const titulo = copia_texto_(
      linha[COPIA_SYNC_CFG.osCols.titulo - 1]
    ).trim();
    const descricao = copia_texto_(
      linha[COPIA_SYNC_CFG.osCols.descricao - 1]
    ).trim();

    if (!acumulado.has(id)) {
      acumulado.set(id, { titulos: [], descricoes: [] });
    }

    const item = acumulado.get(id);
    if (titulo) item.titulos.push(titulo);
    if (descricao) item.descricoes.push(descricao);
  });

  const porId = new Map();
  acumulado.forEach(function (item, id) {
    const titulo = item.titulos.join("; ");
    const descricao = item.descricoes.join("; ");

    if (titulo.length > 49000 || descricao.length > 49000) {
      erros.push(
        "ID " + id + " excede limite de tamanho seguro em E/F"
      );
      return;
    }

    porId.set(id, {
      titulo: titulo,
      descricao: descricao
    });
  });

  return {
    porId: porId,
    erros: erros,
    ultimaLinha: ultima
  };
}


function copia_lerFallback_(ss) {
  const sh = ss.getSheetByName(COPIA_SYNC_CFG.fallbackSheetName);
  if (!sh) {
    return {
      porId: new Map(),
      erros: ["aba " + COPIA_SYNC_CFG.fallbackSheetName + " ausente"]
    };
  }

  const ultima = sh.getLastRow();
  const porId = new Map();
  const erros = [];

  if (ultima < 2) {
    return {
      porId: porId,
      erros: ["fallback sem dados"]
    };
  }

  const valores = sh.getRange(2, 1, ultima - 1, 2).getDisplayValues();
  valores.forEach(function (linha, i) {
    const id = copia_normalizarId_(linha[0]);
    const descricao = copia_texto_(linha[1]);

    if (!id && !descricao) return;
    if (!id || !descricao) {
      erros.push("fallback linha " + (i + 2) + " incompleta");
      return;
    }
    if (porId.has(id)) {
      erros.push("fallback ID duplicado " + id);
      return;
    }
    porId.set(id, descricao);
  });

  return { porId: porId, erros: erros };
}


function copia_lerMapaSnapshot_(snapshot) {
  const ultima = snapshot.getLastRow();
  if (ultima < 2) throw new Error("SNAPSHOT_ETAPA_1 vazio.");

  const valores = snapshot
    .getRange(2, 2, ultima - 1, 2)
    .getDisplayValues();

  const porLinha = new Map();
  const erros = [];

  valores.forEach(function (linha, i) {
    const nLinha = Number(String(linha[0] || "").trim());
    const id = copia_normalizarId_(linha[1]);

    if (!nLinha && !id) return;

    if (!Number.isInteger(nLinha) || nLinha < 2 || !id) {
      erros.push("snapshot linha física " + (i + 2) + " inválida");
      return;
    }

    // Snapshot é append-only: a ocorrência mais recente prevalece.
    porLinha.set(nLinha, id);
  });

  const linhas = Array.from(porLinha.keys()).sort(function (a, b) {
    return a - b;
  });
  if (!linhas.length) {
    throw new Error("SNAPSHOT_ETAPA_1 sem mapeamento utilizável.");
  }

  const maxLinha = linhas[linhas.length - 1];

  for (let linha = 2; linha <= maxLinha; linha++) {
    if (!porLinha.has(linha)) {
      erros.push("linha experimental sem ID no snapshot: " + linha);
    }
  }

  const idParaLinha = new Map();
  for (let linha = 2; linha <= maxLinha; linha++) {
    const id = porLinha.get(linha);
    if (!id) continue;

    if (idParaLinha.has(id)) {
      erros.push(
        "ID " + id + " em duas linhas: " +
        idParaLinha.get(id) + " e " + linha
      );
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


function copia_auditarFormulasAF_(sheet, maxLinha) {
  const quantidade = Math.max(maxLinha - 1, 1);
  const formulas = sheet
    .getRange(2, 1, quantidade, 6)
    .getFormulas();

  let total = 0;
  let importrange = 0;
  let locais = 0;
  const exemplos = [];

  formulas.forEach(function (linha, i) {
    linha.forEach(function (formula, j) {
      if (!formula) return;
      total++;

      if (/IMPORTRANGE\s*\(/i.test(formula)) {
        importrange++;
      } else {
        locais++;
      }

      if (exemplos.length < 40) {
        exemplos.push({
          celula: copia_colunaLetra_(j + 1) + (i + 2),
          formula: formula.slice(0, 240)
        });
      }
    });
  });

  return {
    total: total,
    importrange: importrange,
    locais: locais,
    exemplos: exemplos
  };
}


function copia_ultimaLinhaComDados_(sheet, colunaInicial, quantidadeColunas) {
  const ultima = sheet.getLastRow();
  if (ultima < 2) return 1;

  const valores = sheet
    .getRange(2, colunaInicial, ultima - 1, quantidadeColunas)
    .getDisplayValues();

  for (let i = valores.length - 1; i >= 0; i--) {
    if (
      valores[i].some(function (v) {
        return String(v || "").trim() !== "";
      })
    ) {
      return i + 2;
    }
  }
  return 1;
}


function copia_escreverPreviewMigracao_(plano) {
  const ss = SpreadsheetApp.openById(COPIA_SYNC_CFG.destSpreadsheetId);
  const sh = copia_obterOuCriarAba_(
    ss,
    COPIA_SYNC_CFG.previewSheetName
  );

  sh.clearContents();

  const linhas = [
    ["AUTORIZACAO", ""],
    [
      "INSTRUCAO",
      "Somente se STATUS=APTA, escreva " +
        COPIA_SYNC_CFG.authorizationValue +
        " em B1 e execute aplicarCopiaSemImportrange()."
    ],
    ["STATUS", plano.apto ? "APTA" : "BLOQUEADA"],
    ["DATA_PREFLIGHT", copia_agora_()],
    ["LINHAS_SNAPSHOT", plano.resumo.linhasSnapshot],
    ["IDS_SNAPSHOT_UNICOS", plano.resumo.idsSnapshotUnicos],
    ["IDS_FONTE_HISTORICA", plano.resumo.idsFonteHistorica],
    ["IDS_FONTE_GLPI_ATUAL", plano.resumo.idsFonteGlpiAtual],
    ["IDS_FONTE_OS", plano.resumo.idsFonteOS],
    ["IDS_FALLBACK_DESCRICAO", plano.resumo.idsFallbackDescricao],
    [
      "IDS_SNAPSHOT_AUSENTES_HISTORICO",
      plano.resumo.idsSnapshotAusentesHistorico
    ],
    [
      "IDS_COPIA_DIVERGEM_SNAPSHOT",
      plano.resumo.idsCopiaDivergemSnapshot
    ],
    [
      "TITULOS_DIVERGEM_HISTORICO",
      plano.resumo.titulosDivergemHistorico
    ],
    [
      "CATEGORIAS_DIVERGEM_HISTORICO",
      plano.resumo.categoriasDivergemHistorico
    ],
    [
      "ERROS_VISIVEIS_A_F",
      plano.resumo.errosVisiveisAF
    ],
    [
      "IDS_SEM_GLPI_E_SEM_FALLBACK",
      plano.resumo.idsSemGlpiESemFallback
    ],
    ["DESCRICOES_VAZIAS_FINAIS", plano.resumo.descricoesVaziasFinais],
    ["IDS_SOMENTE_FONTE_ATUAL", plano.resumo.idsSomenteFonteAtual],
    ["FORMULAS_A_F", plano.resumo.formulasAF],
    ["IMPORTRANGE_A_F", plano.resumo.importrangeAF],
    ["FORMULAS_LOCAIS_A_F", plano.resumo.formulasLocaisAF],
    ["ULTIMA_LINHA_DADOS_G_Q", plano.resumo.ultimaLinhaDadosGQ],
    ["ULTIMA_LINHA_FISICA", plano.resumo.ultimaLinhaFisica],
    [
      "LINHAS_RESIDUO_A_F_ABAIXO_SNAPSHOT",
      plano.resumo.linhasResiduoAFAbaixoSnapshot
    ],
    ["DIFERENCAS_A_F_AMOSTRADAS", plano.resumo.diferencasAFDetectadas],
    ["BLOQUEIOS", plano.bloqueios.join(" | ")]
  ];

  sh.getRange(1, 1, linhas.length, 2).setValues(linhas);
  sh.setFrozenRows(2);

  const detalhes = [["TIPO", "LINHA/ID", "DETALHE"]];

  plano.idsLinhaDivergente.slice(0, 200).forEach(function (x) {
    detalhes.push([
      "ID_DIVERGENTE",
      x.linha + "/" + x.snapshot,
      "COPIA=" + x.copia
    ]);
  });

  plano.ausentesGlpiSemFallback.slice(0, 200).forEach(function (x) {
    detalhes.push([
      "SEM_GLPI_SEM_FALLBACK",
      x.linha + "/" + x.id,
      "informativo; valor atual de D é preservado na migração"
    ]);
  });

  plano.divergenciasTitulo.slice(0, 100).forEach(function (x) {
    detalhes.push([
      "TITULO_DIVERGENTE",
      x.linha + "/" + x.id,
      "COPIA=" + x.copia.slice(0, 120) + " | HIST=" + x.fonte.slice(0, 120)
    ]);
  });

  plano.divergenciasCategoria.slice(0, 100).forEach(function (x) {
    detalhes.push([
      "CATEGORIA_DIVERGENTE",
      x.linha + "/" + x.id,
      "COPIA=" + x.copia.slice(0, 120) + " | HIST=" + x.fonte.slice(0, 120)
    ]);
  });

  plano.errosVisiveisAF.slice(0, 100).forEach(function (x) {
    detalhes.push([
      "ERRO_VISIVEL_AF",
      x.linha + "/" + x.id + "/" + x.coluna,
      x.valor
    ]);
  });

  plano.descricoesVaziasFinais.slice(0, 100).forEach(function (x) {
    detalhes.push([
      "DESCRICAO_VAZIA",
      x.linha + "/" + x.id,
      "não bloqueia; pode ser vazio legítimo"
    ]);
  });

  plano.somenteAtual.slice(0, 100).forEach(function (id) {
    detalhes.push([
      "SOMENTE_FONTE_ATUAL",
      id,
      "não será inserido automaticamente"
    ]);
  });

  plano.diferencas.slice(0, 300).forEach(function (x) {
    detalhes.push([
      "DIFERENCA_AF",
      x.linha + "/" + x.id + "/" + x.coluna,
      "antes=" + x.antes + " | depois=" + x.depois
    ]);
  });

  plano.formulas.exemplos.slice(0, 40).forEach(function (x) {
    detalhes.push([
      "FORMULA_ATUAL",
      x.celula,
      x.formula
    ]);
  });

  if (detalhes.length > 1) {
    sh.getRange(
      linhas.length + 2,
      1,
      detalhes.length,
      3
    ).setValues(detalhes);
  }

  sh.autoResizeColumns(1, 3);
}


function copia_escreverPreviewSincronizacao_(plano) {
  const ss = SpreadsheetApp.openById(COPIA_SYNC_CFG.destSpreadsheetId);
  const sh = copia_obterOuCriarAba_(
    ss,
    COPIA_SYNC_CFG.previewSheetName
  );

  sh.clearContents();

  const linhas = [
    ["MODO", "SIMULACAO_SINCRONIZACAO_COPIA"],
    ["STATUS", plano.apto ? "APTA" : "BLOQUEADA"],
    ["DATA", copia_agora_()],
    ["IDS_DESTINO", plano.resumo.idsDestino],
    ["IDS_FONTE_GLPI_ATUAL", plano.resumo.idsFonteGlpiAtual],
    ["ATUALIZACOES", plano.resumo.atualizacoes],
    ["IDS_SOMENTE_FONTE_ATUAL", plano.resumo.idsSomenteFonteAtual],
    [
      "INCLUSAO_NOVOS_HABILITADA",
      plano.resumo.inclusaoNovosHabilitada
    ],
    [
      "IDS_HISTORICOS_PRESERVADOS_AUSENTES_ATUAL",
      plano.resumo.idsHistoricosPreservadosAusentesAtual
    ],
    ["IDS_DUPLICADOS_DESTINO", plano.resumo.idsDuplicadosDestino],
    ["FORMULAS_A_F", plano.resumo.formulasAF],
    ["BLOQUEIOS", plano.bloqueios.join(" | ")]
  ];

  // clearContents() preserva a formatação anterior; força texto no resumo
  // para evitar que contagens sejam exibidas como datas.
  sh.getRange(1, 2, linhas.length, 1).setNumberFormat("@");
  sh.getRange(1, 1, linhas.length, 2).setValues(linhas);

  const detalhes = [["TIPO", "ID", "LINHA", "CAMPOS"]];

  plano.atualizacoes.slice(0, 300).forEach(function (x) {
    detalhes.push([
      "ATUALIZAR",
      x.id,
      x.linha,
      x.camposAlterados.join(",")
    ]);
  });

  plano.novos.slice(0, 200).forEach(function (x) {
    detalhes.push([
      "SOMENTE_FONTE_ATUAL",
      x.id,
      "",
      COPIA_SYNC_CFG.allowNewIds ? "A:F" : "IGNORADO"
    ]);
  });

  if (detalhes.length > 1) {
    sh.getRange(
      linhas.length + 2,
      1,
      detalhes.length,
      4
    ).setValues(detalhes);
  }

  sh.autoResizeColumns(1, 4);
}


function copia_criarBackup_(ss, destino) {
  const nome = COPIA_SYNC_CFG.backupPrefix +
    Utilities.formatDate(
      new Date(),
      COPIA_SYNC_CFG.timeZone,
      "yyyyMMdd_HHmmss"
    );

  if (ss.getSheetByName(nome)) {
    throw new Error("Backup já existe: " + nome);
  }

  const backup = destino.copyTo(ss).setName(nome);
  backup.hideSheet();
  return nome;
}


function copia_obterLog_(ss) {
  let sh = ss.getSheetByName(COPIA_SYNC_CFG.logSheetName);
  if (!sh) {
    sh = ss.insertSheet(COPIA_SYNC_CFG.logSheetName);
    sh.getRange(1, 1, 1, 7).setValues([[
      "data_hora",
      "operacao",
      "id_chamado",
      "linha_destino",
      "categoria_antes",
      "categoria_depois",
      "detalhe"
    ]]);
    sh.setFrozenRows(1);
  }
  return sh;
}


function copia_anexarLog_(ss, operacao, id, antes, depois, detalhe) {
  copia_obterLog_(ss).appendRow([
    copia_agora_(),
    operacao,
    id,
    "",
    antes,
    depois,
    detalhe
  ]);
}


function copia_obterOuCriarAba_(ss, nome) {
  return ss.getSheetByName(nome) || ss.insertSheet(nome);
}


function copia_validarIdsDestino_(sheet) {
  const ultima = sheet.getLastRow();
  if (ultima < 2) return;

  const ids = sheet
    .getRange(2, 1, ultima - 1, 1)
    .getDisplayValues();

  const vistos = new Set();

  ids.forEach(function (linha) {
    const id = copia_normalizarId_(linha[0]);
    if (!id) return;
    if (vistos.has(id)) {
      throw new Error(
        "PÓS-CONDIÇÃO FALHOU: ID duplicado em COPIA: " + id
      );
    }
    vistos.add(id);
  });
}


function copia_compararMatrizes_(esperado, lido, limite) {
  const divergencias = [];

  if (esperado.length !== lido.length) {
    divergencias.push({
      linha: "",
      coluna: "",
      esperado: "linhas=" + esperado.length,
      lido: "linhas=" + lido.length
    });
    return divergencias;
  }

  for (let i = 0; i < esperado.length; i++) {
    const e = esperado[i] || [];
    const l = lido[i] || [];
    const colunas = Math.max(e.length, l.length);

    for (let j = 0; j < colunas; j++) {
      if (copia_texto_(e[j]) !== copia_texto_(l[j])) {
        divergencias.push({
          linha: i + 2,
          coluna: copia_colunaLetra_(j + 1),
          esperado: copia_texto_(e[j]).slice(0, 120),
          lido: copia_texto_(l[j]).slice(0, 120)
        });

        if (divergencias.length >= limite) {
          return divergencias;
        }
      }
    }
  }

  return divergencias;
}


function copia_resolverDescricaoSincronizacao_(live, existente, fallbackD) {
  const atualD = existente
    ? copia_texto_(existente.valores[3])
    : "";

  if (!live) {
    return copia_texto_(fallbackD) || atualD;
  }

  const descricao = copia_texto_(live.descricao).trim();
  const solucao = copia_texto_(live.solucao).trim();

  // Preserva o padrão materializado da antiga CHAMADOS!W:
  // a regra geral é descrição pura. Se o registro já era explicitamente
  // composto por "Descrição - ... / Solução - ...", mantém esse formato.
  const legadoComposto =
    /^Descrição - /i.test(atualD) &&
    /\n\nSolução - /i.test(atualD);

  if (legadoComposto) {
    return copia_montarDescricaoGlpi_(descricao, solucao) || atualD;
  }

  if (descricao) return descricao;
  return copia_texto_(fallbackD) || atualD;
}


function copia_textoComparavel_(valor) {
  return copia_texto_(valor)
    .replace(/\u00a0/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}


function copia_montarDescricaoGlpi_(descricao, solucao) {
  const d = copia_texto_(descricao).trim();
  const s = copia_texto_(solucao).trim();

  if (!d && !s) return "";
  if (!s) return d;
  if (!d) return "Solução - " + s;

  return "Descrição - " + d + "\n\nSolução - " + s;
}


function copia_eErroPlanilha_(valor) {
  return /^#(REF!|N\/A|VALUE!|ERROR!|NAME\?|DIV\/0!|NUM!|NULL!)/i.test(
    String(valor || "").trim()
  );
}


function copia_normalizarId_(valor) {
  const s = String(valor == null ? "" : valor).trim();
  return s.replace(/\.0$/, "");
}


function copia_texto_(valor) {
  return String(valor == null ? "" : valor);
}


function copia_valorLiteral_(valor) {
  const s = copia_texto_(valor);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}


function copia_agora_() {
  return Utilities.formatDate(
    new Date(),
    COPIA_SYNC_CFG.timeZone,
    "yyyy-MM-dd HH:mm:ss"
  );
}


function copia_colunaLetra_(n) {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}


function copia_withLock_(fn) {
  const lock = LockService.getScriptLock();

  if (!lock.tryLock(30000)) {
    throw new Error(
      "LOCK_OCUPADO: outra sincronização está em andamento."
    );
  }

  try {
    return fn();
  } finally {
    lock.releaseLock();
  }
}
