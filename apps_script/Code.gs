const API_TOKEN = 'TROQUE_PELO_TOKEN_DO_SECRET';

function doGet(e) {
  const auth = validarToken_(e);
  if (!auth.ok) return jsonResponse_(auth);

  const action = e.parameter.action || 'validar';

  if (action === 'listar_abas') return listarAbas_();
  if (action === 'validar') return validarAba_(e);
  if (action === 'ler') return lerAba_(e);

  return jsonResponse_({
    ok: false,
    erro: 'acao_get_desconhecida',
    action
  });
}

function doPost(e) {
  const body = parseJsonBody_(e);
  const auth = validarTokenBody_(body);
  if (!auth.ok) return jsonResponse_(auth);

  const action = body.action || '';

  if (action === 'preparar_abas_experimento') {
    return prepararAbasExperimento_(body);
  }

  if (action === 'registrar_config_experimento') {
    return registrarConfigExperimento_(body);
  }

  if (action === 'registrar_snapshot_inicial') {
    return registrarSnapshotInicial_(body);
  }

  return jsonResponse_({
    ok: false,
    erro: 'acao_post_desconhecida',
    action
  });
}

function listarAbas_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets().map(sheet => ({
    name: sheet.getName(),
    lastRow: sheet.getLastRow(),
    lastColumn: sheet.getLastColumn()
  }));

  return jsonResponse_({
    ok: true,
    action: 'listar_abas',
    sheets
  });
}

function validarAba_(e) {
  const sheetName = e.parameter.sheet || '';
  const rangeA1 = e.parameter.range || 'A:M';

  const sheet = getSheetOrError_(sheetName);
  if (sheet.erro) return jsonResponse_(sheet);

  const values = getValuesDynamic_(sheet, rangeA1);
  const header = values.length ? values[0] : [];
  const dataRows = values.slice(1);
  const nonEmptyRows = dataRows.filter(row =>
    row.some(cell => String(cell || '').trim() !== '')
  );

  return jsonResponse_({
    ok: true,
    action: 'validar',
    sheet: sheetName,
    range: rangeA1,
    lastRow: sheet.getLastRow(),
    lastColumn: sheet.getLastColumn(),
    totalRowsRead: values.length,
    totalDataRows: dataRows.length,
    totalNonEmptyRows: nonEmptyRows.length,
    header
  });
}

function lerAba_(e) {
  const sheetName = e.parameter.sheet || '';
  const rangeA1 = e.parameter.range || 'A:M';

  const sheet = getSheetOrError_(sheetName);
  if (sheet.erro) return jsonResponse_(sheet);

  return jsonResponse_({
    ok: true,
    action: 'ler',
    sheet: sheetName,
    range: rangeA1,
    values: getValuesDynamic_(sheet, rangeA1)
  });
}

function prepararAbasExperimento_(body) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const abas = body.abas || [];
  const resultado = [];

  abas.forEach(item => {
    const nome = item.nome || '';
    const cabecalho = item.cabecalho || [];

    if (!nome) {
      resultado.push({ nome, ok: false, erro: 'nome_vazio' });
      return;
    }

    let sheet = ss.getSheetByName(nome);
    let criada = false;

    if (!sheet) {
      sheet = ss.insertSheet(nome);
      criada = true;
    }

    if (cabecalho.length > 0) {
      sheet.getRange(1, 1, 1, cabecalho.length).setValues([cabecalho]);
      sheet.setFrozenRows(1);
    }

    resultado.push({
      nome,
      ok: true,
      criada,
      lastRow: sheet.getLastRow(),
      lastColumn: sheet.getLastColumn()
    });
  });

  return jsonResponse_({
    ok: true,
    action: 'preparar_abas_experimento',
    resultado
  });
}

function registrarConfigExperimento_(body) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetName = body.sheet || 'EXPERIMENTO_CONFIG';
  const linhas = body.linhas || [];

  if (!Array.isArray(linhas) || linhas.length === 0) {
    return jsonResponse_({
      ok: false,
      erro: 'linhas_invalidas'
    });
  }

  let sheet = ss.getSheetByName(sheetName);
  let criada = false;

  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    criada = true;
  }

  sheet.clearContents();
  sheet.getRange(1, 1, linhas.length, 3).setValues(linhas);
  sheet.setFrozenRows(1);

  return jsonResponse_({
    ok: true,
    action: 'registrar_config_experimento',
    sheet: sheetName,
    criada,
    linhas_gravadas: linhas.length,
    lastRow: sheet.getLastRow(),
    lastColumn: sheet.getLastColumn()
  });
}

function registrarSnapshotInicial_(body) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const origemNome = body.origem || 'CHAMADOS_ESQUELETO_REDUZIDO';
  const destinoNome = body.destino || 'SNAPSHOT_ETAPA_1';
  const runId = body.run_id || '';
  const dataSnapshot = formatarDataBahia_(new Date());

  const origem = ss.getSheetByName(origemNome);
  if (!origem) {
    return jsonResponse_({
      ok: false,
      erro: 'aba_origem_nao_encontrada',
      origem: origemNome
    });
  }

  let destino = ss.getSheetByName(destinoNome);
  let criada = false;
  if (!destino) {
    destino = ss.insertSheet(destinoNome);
    criada = true;
  }

  const lastRow = origem.getLastRow();
  const values = lastRow > 0 ? origem.getRange(1, 1, lastRow, 13).getValues() : [];
  const cabecalho = [
    'run_id',
    'linha_planilha',
    'id_chamado',
    'categoria_original',
    'categoria_ia_etapa_1',
    'confianca_etapa_1',
    'executor_etapa_1',
    'criticidade_etapa_1',
    'conferencia_etapa_1',
    'data_snapshot'
  ];

  const linhas = [cabecalho];
  const dados = values.slice(1);

  dados.forEach((row, idx) => {
    const vazia = row.every(cell => String(cell || '').trim() === '');
    if (vazia) return;

    linhas.push([
      runId,
      idx + 2,
      row[0] || '',
      row[2] || '',
      row[6] || '',
      row[7] || '',
      row[8] || '',
      row[9] || '',
      row[12] || '',
      dataSnapshot
    ]);
  });

  destino.clearContents();
  gravarEmBlocos_(destino, linhas, 10, 1000);
  destino.setFrozenRows(1);

  return jsonResponse_({
    ok: true,
    action: 'registrar_snapshot_inicial',
    origem: origemNome,
    destino: destinoNome,
    criada,
    linhas_origem_lidas: values.length,
    linhas_snapshot: linhas.length - 1,
    lastRow: destino.getLastRow(),
    lastColumn: destino.getLastColumn()
  });
}

function gravarEmBlocos_(sheet, linhas, colunas, tamanhoBloco) {
  for (let inicio = 0; inicio < linhas.length; inicio += tamanhoBloco) {
    const bloco = linhas.slice(inicio, inicio + tamanhoBloco);
    sheet.getRange(inicio + 1, 1, bloco.length, colunas).setValues(bloco);
  }
}

function formatarDataBahia_(data) {
  return Utilities.formatDate(data, 'America/Bahia', "yyyy-MM-dd'T'HH:mm:ss") + '-03:00';
}

function getSheetOrError_(sheetName) {
  if (!sheetName) {
    return { ok: false, erro: 'sheet_nao_informada' };
  }

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    return {
      ok: false,
      erro: 'aba_nao_encontrada',
      sheet: sheetName
    };
  }

  return sheet;
}

function getValuesDynamic_(sheet, rangeA1) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 1) return [];

  if (rangeA1 === 'A:M') {
    return sheet.getRange(1, 1, lastRow, 13).getValues();
  }

  return sheet.getRange(rangeA1).getValues();
}

function validarToken_(e) {
  const token = e.parameter.token || '';
  if (token !== API_TOKEN) {
    return { ok: false, erro: 'token_invalido' };
  }
  return { ok: true };
}

function validarTokenBody_(body) {
  const token = body.token || '';
  if (token !== API_TOKEN) {
    return { ok: false, erro: 'token_invalido' };
  }
  return { ok: true };
}

function parseJsonBody_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return {};
  }

  try {
    return JSON.parse(e.postData.contents);
  } catch (err) {
    return {};
  }
}

function jsonResponse_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
