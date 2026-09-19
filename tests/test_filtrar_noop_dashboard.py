#!/usr/bin/env python3
"""Testes dos lotes A3-2 e A3-2R: `src/filtrar_noop_dashboard.py` restaura
para HEAD os JSONs de docs/dados cuja unica mudanca seja um campo volatil de
timestamp -- `gerado_em` no nivel superior (regra geral) ou, exclusivamente
em docs/dados/multimodelo_metricas.json, `atualizado_em` por item da lista
(excecao especifica, A3-2R) -- sem `git checkout`/`restore`/`reset`, e sem
tocar em nenhum outro tipo de divergencia. Cobre a logica pura (sem Git), o
uso de HEAD via `git ls-tree`/`git show` em um repositorio local temporario
(inclusive fail-closed de falha real do Git), o CLI, as regressoes
historicas dos commits reais "dados do dashboard [skip ci]" e um teste
estatico de que a integracao em dashboard.yml preserva triggers/allowlist e
chama o helper antes do `git add`.

Nenhum teste acessa rede, planilha real ou GitHub Actions.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import filtrar_noop_dashboard as fnd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
WORKFLOWS = RAIZ / ".github" / "workflows"


def _git(args, cwd):
    resultado = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"git {args} falhou: {resultado.stderr}")
    return resultado.stdout


# --------------------------------------------------------------------------
# Grupo 1: logica semantica pura -- sem Git.
# --------------------------------------------------------------------------

class TestValidarPath(unittest.TestCase):
    def test_path_valido_aceito(self):
        p = fnd.validar_path("docs/dados/calibracao.json")
        self.assertEqual(p.as_posix(), "docs/dados/calibracao.json")

    def test_path_absoluto_rejeitado(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.validar_path("/etc/passwd")

    def test_path_absoluto_windows_rejeitado(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.validar_path("C:/Windows/system.json")

    def test_travessia_diretorio_rejeitada(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.validar_path("docs/dados/../../etc/passwd.json")

    def test_fora_de_docs_dados_rejeitado(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.validar_path("src/filtrar_noop_dashboard.py")

    def test_extensao_diferente_de_json_rejeitada(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.validar_path("docs/dados/mapa.csv")

    def test_diretorio_nao_aceito(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.validar_path("docs/dados/")


class TestEhApenasGeradoEmDiferente(unittest.TestCase):
    def test_somente_gerado_em_muda(self):
        baseline = {"gerado_em": "19/08/2026 19:59", "total": 100, "taxa": 0.91}
        novo = {"gerado_em": "19/08/2026 20:29", "total": 100, "taxa": 0.91}
        self.assertTrue(fnd.eh_apenas_gerado_em_diferente(baseline, novo))

    def test_gerado_em_e_valor_substantivo_mudam(self):
        baseline = {"gerado_em": "19/08/2026 19:59", "total": 100}
        novo = {"gerado_em": "19/08/2026 20:29", "total": 101}
        self.assertFalse(fnd.eh_apenas_gerado_em_diferente(baseline, novo))

    def test_gerado_em_aninhado_muda_nao_aplica_excecao(self):
        baseline = {"gerado_em": "19/08/2026 19:59", "objeto": {"gerado_em": "a"}}
        novo = {"gerado_em": "19/08/2026 20:29", "objeto": {"gerado_em": "b"}}
        self.assertFalse(fnd.eh_apenas_gerado_em_diferente(baseline, novo))

    def test_gerado_em_so_no_novo(self):
        baseline = {"total": 100}
        novo = {"gerado_em": "19/08/2026 20:29", "total": 100}
        self.assertFalse(fnd.eh_apenas_gerado_em_diferente(baseline, novo))

    def test_gerado_em_so_no_baseline(self):
        baseline = {"gerado_em": "19/08/2026 19:59", "total": 100}
        novo = {"total": 100}
        self.assertFalse(fnd.eh_apenas_gerado_em_diferente(baseline, novo))

    def test_lista_no_topo_nao_aplica_excecao(self):
        baseline = [{"modelo": "a", "gerado_em": "x"}]
        novo = [{"modelo": "a", "gerado_em": "y"}]
        self.assertFalse(fnd.eh_apenas_gerado_em_diferente(baseline, novo))

    def test_escalar_no_topo_nao_aplica_excecao(self):
        self.assertFalse(fnd.eh_apenas_gerado_em_diferente(42, 42))


# --------------------------------------------------------------------------
# Grupo 2: processar_path sobre um repositorio Git local temporario.
# --------------------------------------------------------------------------

class BaseRepoTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fnd-repo-")
        self.repo = Path(self._tmp.name)
        _git(["init", "-b", "main", str(self.repo)], cwd=self.repo.parent)
        _git(["config", "user.name", "teste"], cwd=self.repo)
        _git(["config", "user.email", "teste@example.com"], cwd=self.repo)
        (self.repo / "docs" / "dados").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _commitar(self, rel_path: str, conteudo: str, mensagem="seed"):
        alvo = self.repo / rel_path
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")
        _git(["add", "--", rel_path], cwd=self.repo)
        _git(["commit", "-m", mensagem], cwd=self.repo)

    def _escrever_sem_commit(self, rel_path: str, conteudo: str):
        alvo = self.repo / rel_path
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")

    def _ler(self, rel_path: str) -> str:
        return (self.repo / rel_path).read_text(encoding="utf-8")


class TestProcessarPathCasos(BaseRepoTestCase):
    def test_caso_a_restaura_baseline_quando_so_gerado_em_muda(self):
        rel = "docs/dados/calibracao.json"
        self._commitar(rel, json.dumps({"gerado_em": "19/08/2026 19:59", "total": 100}))
        self._escrever_sem_commit(rel, json.dumps({"gerado_em": "19/08/2026 20:29", "total": 100}))

        path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_VOLATIL_RESTAURADO)
        self.assertEqual(path_norm, rel)
        self.assertEqual(json.loads(self._ler(rel)), {"gerado_em": "19/08/2026 19:59", "total": 100})

    def test_caso_b_mantem_quando_ha_mudanca_substantiva(self):
        rel = "docs/dados/calibracao.json"
        self._commitar(rel, json.dumps({"gerado_em": "19/08/2026 19:59", "total": 100}))
        novo_conteudo = json.dumps({"gerado_em": "19/08/2026 20:29", "total": 101})
        self._escrever_sem_commit(rel, novo_conteudo)

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_SUBSTANTIVO)
        self.assertEqual(self._ler(rel), novo_conteudo)

    def test_caso_c_arquivo_novo_sem_baseline_permanece(self):
        # HEAD precisa existir (repo com pelo menos um commit) para exercitar
        # de fato "path ausente em HEAD", e nao um HEAD inexistente (unborn).
        self._commitar("docs/dados/outro.json", json.dumps({"gerado_em": "t0", "x": 1}))
        rel = "docs/dados/novo_arquivo.json"
        conteudo = json.dumps({"gerado_em": "19/08/2026 20:29", "total": 1})
        self._escrever_sem_commit(rel, conteudo)

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_NOVO)
        self.assertEqual(self._ler(rel), conteudo)

    def test_caso_d_arquivo_removido_nao_e_restaurado(self):
        rel = "docs/dados/resumo.json"
        self._commitar(rel, json.dumps({"gerado_em": "19/08/2026 19:59", "total": 100}))
        (self.repo / rel).unlink()

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_SUBSTANTIVO)
        self.assertFalse((self.repo / rel).exists())

    def test_caso_e_json_invalido_no_novo_falha_fechado_e_preserva(self):
        rel = "docs/dados/calibracao.json"
        self._commitar(rel, json.dumps({"gerado_em": "19/08/2026 19:59", "total": 100}))
        conteudo_quebrado = "{isto nao e json valido"
        self._escrever_sem_commit(rel, conteudo_quebrado)

        with self.assertRaises(fnd.JsonInvalidoError):
            fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(self._ler(rel), conteudo_quebrado)

    def test_caso_e_json_invalido_no_baseline_falha_fechado_e_preserva_novo(self):
        rel = "docs/dados/calibracao.json"
        self._commitar(rel, "{isto no head nao e json valido")
        conteudo_novo = json.dumps({"gerado_em": "19/08/2026 20:29", "total": 1})
        self._escrever_sem_commit(rel, conteudo_novo)

        with self.assertRaises(fnd.JsonInvalidoError):
            fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(self._ler(rel), conteudo_novo)

    def test_caso_f_lista_modificada_nao_aplica_excecao(self):
        # Path generico (nao multimodelo_metricas.json): lista no topo nunca
        # recebe a excecao de gerado_em, mesmo com valor real mudando.
        rel = "docs/dados/comparacao_previsoes.json"
        self._commitar(rel, json.dumps([{"modelo": "a", "valor": 1}]))
        novo_conteudo = json.dumps([{"modelo": "a", "valor": 2}])
        self._escrever_sem_commit(rel, novo_conteudo)

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_SUBSTANTIVO)
        self.assertEqual(self._ler(rel), novo_conteudo)

    def test_caso_g_gerado_em_so_no_novo_nao_restaura(self):
        rel = "docs/dados/resumo.json"
        self._commitar(rel, json.dumps({"total": 100}))
        novo_conteudo = json.dumps({"gerado_em": "19/08/2026 20:29", "total": 100})
        self._escrever_sem_commit(rel, novo_conteudo)

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_SUBSTANTIVO)
        self.assertEqual(self._ler(rel), novo_conteudo)

    def test_caso_g_gerado_em_so_no_baseline_nao_restaura(self):
        rel = "docs/dados/resumo.json"
        self._commitar(rel, json.dumps({"gerado_em": "19/08/2026 19:59", "total": 100}))
        novo_conteudo = json.dumps({"total": 100})
        self._escrever_sem_commit(rel, novo_conteudo)

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_SUBSTANTIVO)
        self.assertEqual(self._ler(rel), novo_conteudo)

    def test_caso_h_gerado_em_aninhado_muda_nao_restaura(self):
        rel = "docs/dados/comparacao_categoria.json"
        self._commitar(rel, json.dumps({"gerado_em": "19/08/2026 19:59", "obj": {"gerado_em": "a"}}))
        novo_conteudo = json.dumps({"gerado_em": "19/08/2026 20:29", "obj": {"gerado_em": "b"}})
        self._escrever_sem_commit(rel, novo_conteudo)

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_SUBSTANTIVO)
        self.assertEqual(self._ler(rel), novo_conteudo)

    def test_path_fora_de_docs_dados_rejeitado_em_processar_path(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.processar_path("outra_pasta/arquivo.json", cwd=self.repo)

    def test_path_com_travessia_rejeitado_em_processar_path(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.processar_path("docs/dados/../../fora.json", cwd=self.repo)

    def test_path_nao_json_rejeitado_em_processar_path(self):
        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.processar_path("docs/dados/mapa.csv", cwd=self.repo)

    def test_idempotencia_segunda_execucao_nao_muda_nada(self):
        rel = "docs/dados/calibracao.json"
        self._commitar(rel, json.dumps({"gerado_em": "19/08/2026 19:59", "total": 100}))
        self._escrever_sem_commit(rel, json.dumps({"gerado_em": "19/08/2026 20:29", "total": 100}))

        fnd.processar_path(rel, cwd=self.repo)
        conteudo_apos_primeira = self._ler(rel)
        _path_norm, status_segunda = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status_segunda, fnd.STATUS_VOLATIL_RESTAURADO)
        self.assertEqual(self._ler(rel), conteudo_apos_primeira)

    def test_bytes_restaurados_sao_exatamente_os_bytes_do_head(self):
        rel = "docs/dados/calibracao.json"
        conteudo_head = '{"gerado_em": "19/08/2026 19:59", "total": 100}'
        self._commitar(rel, conteudo_head)
        self._escrever_sem_commit(rel, '{"gerado_em": "19/08/2026 20:29", "total": 100}')

        fnd.processar_path(rel, cwd=self.repo)

        bytes_head = subprocess.run(
            ["git", "show", f"HEAD:{rel}"], cwd=self.repo, capture_output=True, check=True
        ).stdout
        self.assertEqual((self.repo / rel).read_bytes(), bytes_head)

    def test_multiplos_paths_mistos_restaura_apenas_os_noop(self):
        rel_a = "docs/dados/calibracao.json"
        rel_b = "docs/dados/resumo.json"
        rel_c = "docs/dados/shannon_resumo.json"
        self._commitar(rel_a, json.dumps({"gerado_em": "t1", "total": 100}), mensagem="seed a")
        self._commitar(rel_b, json.dumps({"gerado_em": "t1", "total": 1}), mensagem="seed b")
        self._commitar(rel_c, json.dumps({"gerado_em": "t1", "total": 9}), mensagem="seed c")

        self._escrever_sem_commit(rel_a, json.dumps({"gerado_em": "t2", "total": 100}))  # noop
        novo_b = json.dumps({"gerado_em": "t2", "total": 2})  # substantivo
        self._escrever_sem_commit(rel_b, novo_b)
        self._escrever_sem_commit(rel_c, json.dumps({"gerado_em": "t2", "total": 9}))  # noop

        resultados = {}
        for rel in (rel_a, rel_b, rel_c):
            _p, status = fnd.processar_path(rel, cwd=self.repo)
            resultados[rel] = status

        self.assertEqual(resultados[rel_a], fnd.STATUS_VOLATIL_RESTAURADO)
        self.assertEqual(resultados[rel_b], fnd.STATUS_SUBSTANTIVO)
        self.assertEqual(resultados[rel_c], fnd.STATUS_VOLATIL_RESTAURADO)

        self.assertEqual(json.loads(self._ler(rel_a)), {"gerado_em": "t1", "total": 100})
        self.assertEqual(self._ler(rel_b), novo_b)
        self.assertEqual(json.loads(self._ler(rel_c)), {"gerado_em": "t1", "total": 9})

        status_git = _git(["status", "--porcelain", "--", "docs/dados"], cwd=self.repo)
        alterados = [l[3:] for l in status_git.splitlines() if l.strip()]
        self.assertEqual(alterados, [rel_b])


# --------------------------------------------------------------------------
# Grupo 3: regressao historica -- reproduz semanticamente o padrao observado
# no commit 525edb3466481850155bd80381ad61ad01ea5cd6 ("dados do dashboard
# [skip ci]"), onde calibracao.json mudou so em "gerado_em".
# --------------------------------------------------------------------------

class TestRegressaoHistoricaGeradoEmOnly(BaseRepoTestCase):
    def test_padrao_commit_525edb34_fica_sem_diff(self):
        rel = "docs/dados/calibracao.json"
        antes = {
            "gerado_em": "19/08/2026 19:59",
            "run_id": "EXP_CLASSIFICACAO_CHAMADOS_2026_06_001",
            "total": 14160,
            "validados": 14057,
            "acerto_ia_validado": 0.9198,
        }
        depois = dict(antes, **{"gerado_em": "19/08/2026 20:01"})
        self._commitar(rel, json.dumps(antes))
        self._escrever_sem_commit(rel, json.dumps(depois))

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_VOLATIL_RESTAURADO)
        status_git = _git(["status", "--porcelain", "--", rel], cwd=self.repo)
        self.assertEqual(status_git.strip(), "", "arquivo deveria estar sem diff apos a restauracao")


# --------------------------------------------------------------------------
# Grupo 3b: excecao exclusiva de docs/dados/multimodelo_metricas.json
# (atualizado_em por item), microcorrecao A3-2R.
# --------------------------------------------------------------------------

class TestEhApenasAtualizadoEmPorItemDiferentePuro(unittest.TestCase):
    def _item(self, modelo, atualizado_em, **extra):
        base = {
            "modelo": modelo,
            "feitos_total": 14166,
            "pendentes_restantes": 0,
            "concordancia_acumulada": 0.8,
            "concordancia_ultimo_lote": "",
            "metodo_ultimo": "",
            "processados_ultimo": 0,
            "atualizado_em": atualizado_em,
        }
        base.update(extra)
        return base

    def test_todos_os_itens_mudam_so_atualizado_em(self):
        baseline = [self._item("a", "t1"), self._item("b", "t1")]
        novo = [self._item("a", "t2"), self._item("b", "t2")]
        self.assertTrue(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_so_alguns_itens_mudam_atualizado_em(self):
        baseline = [self._item("a", "t1"), self._item("b", "t1")]
        novo = [self._item("a", "t2"), self._item("b", "t1")]
        self.assertTrue(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_feitos_total_muda_em_um_item(self):
        baseline = [self._item("a", "t1"), self._item("b", "t1")]
        novo = [self._item("a", "t2", feitos_total=99), self._item("b", "t2")]
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_concordancia_acumulada_muda(self):
        baseline = [self._item("a", "t1")]
        novo = [self._item("a", "t2", concordancia_acumulada=0.99)]
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_ordem_dos_elementos_muda(self):
        baseline = [self._item("a", "t1"), self._item("b", "t1")]
        novo = [self._item("b", "t2"), self._item("a", "t2")]
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_elemento_novo(self):
        baseline = [self._item("a", "t1")]
        novo = [self._item("a", "t2"), self._item("b", "t2")]
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_elemento_removido(self):
        baseline = [self._item("a", "t1"), self._item("b", "t1")]
        novo = [self._item("a", "t2")]
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_atualizado_em_so_de_um_lado(self):
        item_sem_campo = self._item("a", "t1")
        del item_sem_campo["atualizado_em"]
        baseline = [item_sem_campo]
        novo = [self._item("a", "t2")]
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_elemento_deixa_de_ser_dict(self):
        baseline = [self._item("a", "t1")]
        novo = ["nao e mais um dict"]
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_atualizado_em_aninhado_nao_conta(self):
        baseline = [self._item("a", "t1", obj={"atualizado_em": "x"})]
        novo = [self._item("a", "t1", obj={"atualizado_em": "y"})]
        # atualizado_em top-level do item nao mudou; o aninhado nao e tocado
        # pela excecao, entao o item difere e a excecao nao se aplica.
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente(baseline, novo))

    def test_topo_nao_e_lista(self):
        self.assertFalse(fnd.eh_apenas_atualizado_em_por_item_diferente({"a": 1}, {"a": 1}))


class TestExcecaoRestritaAoPathExato(BaseRepoTestCase):
    """Item 10 da microcorrecao: mesma estrutura em outro filename nao deve
    ignorar atualizado_em -- a excecao e exclusiva de
    docs/dados/multimodelo_metricas.json."""

    def _lista(self, atualizado_em):
        return json.dumps([{
            "modelo": "extra_trees", "feitos_total": 14166, "pendentes_restantes": 0,
            "concordancia_acumulada": 0.7872, "concordancia_ultimo_lote": "",
            "metodo_ultimo": "", "processados_ultimo": 0, "atualizado_em": atualizado_em,
        }])

    def test_arquivo_com_mesma_estrutura_mas_outro_nome_nao_e_isento(self):
        rel = "docs/dados/multimodelo_reclass_turnos.json"
        self._commitar(rel, self._lista("t1"))
        novo_conteudo = self._lista("t2")
        self._escrever_sem_commit(rel, novo_conteudo)

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_SUBSTANTIVO)
        self.assertEqual(self._ler(rel), novo_conteudo)

    def test_multimodelo_metricas_no_path_exato_e_isento(self):
        rel = "docs/dados/multimodelo_metricas.json"
        self._commitar(rel, self._lista("t1"))
        self._escrever_sem_commit(rel, self._lista("t2"))

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_VOLATIL_RESTAURADO)


class TestMultimodeloMetricasIntegracao(BaseRepoTestCase):
    """Testes fim a fim (com Git real) para docs/dados/multimodelo_metricas.json."""

    REL = "docs/dados/multimodelo_metricas.json"

    def _item(self, modelo, atualizado_em, feitos_total=14166, concordancia_acumulada=0.8):
        return {
            "modelo": modelo, "feitos_total": feitos_total, "pendentes_restantes": 0,
            "concordancia_acumulada": concordancia_acumulada, "concordancia_ultimo_lote": "",
            "metodo_ultimo": "", "processados_ultimo": 0, "atualizado_em": atualizado_em,
        }

    def test_restauracao_e_byte_a_byte_igual_ao_head(self):
        baseline = [self._item("extra_trees", "t1"), self._item("linear_svc", "t1")]
        self._commitar(self.REL, json.dumps(baseline))
        self._escrever_sem_commit(
            self.REL,
            json.dumps([self._item("extra_trees", "t2"), self._item("linear_svc", "t2")]),
        )

        fnd.processar_path(self.REL, cwd=self.repo)

        bytes_head = subprocess.run(
            ["git", "show", f"HEAD:{self.REL}"], cwd=self.repo, capture_output=True, check=True
        ).stdout
        self.assertEqual((self.repo / self.REL).read_bytes(), bytes_head)


# --------------------------------------------------------------------------
# Grupo 3c: fail-closed do baseline Git (git ls-tree / git show), item 7 da
# microcorrecao.
# --------------------------------------------------------------------------

class TestBaselineGitFailClosed(BaseRepoTestCase):
    def test_arquivo_realmente_inexistente_em_head_e_novo(self):
        self._commitar("docs/dados/outro.json", json.dumps({"gerado_em": "t0"}))
        rel = "docs/dados/nao_existe_em_head.json"
        self._escrever_sem_commit(rel, json.dumps({"gerado_em": "t1"}))

        _path_norm, status = fnd.processar_path(rel, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_NOVO)

    def test_falha_real_do_git_nunca_vira_novo(self):
        # cwd fora de qualquer repositorio Git: git ls-tree falha de verdade
        # (nao "path ausente em HEAD"), e isso deve ser ERRO, nunca NOVO.
        tmp = tempfile.TemporaryDirectory(prefix="fnd-nao-git-")
        try:
            nao_repo = Path(tmp.name)
            alvo = nao_repo / "docs" / "dados" / "arquivo.json"
            alvo.parent.mkdir(parents=True)
            alvo.write_text(json.dumps({"gerado_em": "t1"}), encoding="utf-8")

            with self.assertRaises(fnd.GitBaselineError):
                fnd.processar_path("docs/dados/arquivo.json", cwd=nao_repo)
        finally:
            tmp.cleanup()

    def test_falha_em_git_show_de_path_que_existe_e_erro(self):
        rel = "docs/dados/calibracao.json"
        self._commitar(rel, json.dumps({"gerado_em": "t1", "total": 1}))
        self._escrever_sem_commit(rel, json.dumps({"gerado_em": "t2", "total": 1}))

        # Corrompe o objeto do blob referenciado pela arvore de HEAD: o path
        # continua listado por `git ls-tree` (a entrada da arvore nao muda),
        # mas `git show HEAD:<path>` falha ao tentar ler o conteudo do blob.
        blob_sha = _git(["rev-parse", f"HEAD:{rel}"], cwd=self.repo).strip()
        objeto = self.repo / ".git" / "objects" / blob_sha[:2] / blob_sha[2:]
        self.assertTrue(objeto.exists(), "pre-condicao: objeto do blob deveria existir")
        # objetos do Git sao gravados somente-leitura; ajusta o modo antes de
        # corromper o conteudo (git-for-windows nega unlink direto).
        os.chmod(objeto, 0o600)
        objeto.write_bytes(b"conteudo corrompido, nao e um objeto git valido")

        with self.assertRaises(fnd.GitBaselineError):
            fnd.processar_path(rel, cwd=self.repo)

        # Fail closed: o arquivo no working tree nao foi tocado.
        self.assertEqual(
            json.loads(self._ler(rel)), {"gerado_em": "t2", "total": 1}
        )

    def test_diretorio_chamado_algo_json_e_rejeitado(self):
        (self.repo / "docs" / "dados" / "pasta.json").mkdir(parents=True)

        with self.assertRaises(fnd.PathRejeitadoError):
            fnd.processar_path("docs/dados/pasta.json", cwd=self.repo)


# --------------------------------------------------------------------------
# Grupo 3d: regressao com os dois commits reais observados pelo ChatGPT
# (1f237f8e -> a3f1a731), item 10 da microcorrecao.
# --------------------------------------------------------------------------

class TestRegressaoDoisCommitsReais(BaseRepoTestCase):
    REL = "docs/dados/multimodelo_metricas.json"

    MODELOS = [
        ("extra_trees", 14166, 0, 0.7872),
        ("linear_svc", 14166, 0, 0.8035),
        ("lstm", 14166, 0, 0.6885),
        ("naive_bayes", 14166, 0, 0.6973),
        ("random_forest", 14166, 0, 0.7769),
        ("regressao_logistica", 14166, 0, 0.7697),
        ("sgd", 14166, 0, 0.7762),
        ("transformer_ft", "", 14166, ""),
    ]

    def _lista(self, atualizado_em):
        return json.dumps([
            {
                "modelo": modelo, "feitos_total": feitos_total,
                "pendentes_restantes": pendentes, "concordancia_acumulada": concordancia,
                "concordancia_ultimo_lote": "", "metodo_ultimo": "", "processados_ultimo": 0,
                "atualizado_em": atualizado_em,
            }
            for modelo, feitos_total, pendentes, concordancia in self.MODELOS
        ])

    def _rodar_ciclo(self, antes, depois):
        self._commitar(self.REL, self._lista(antes))
        self._escrever_sem_commit(self.REL, self._lista(depois))

        _path_norm, status = fnd.processar_path(self.REL, cwd=self.repo)

        self.assertEqual(status, fnd.STATUS_VOLATIL_RESTAURADO)
        status_git = _git(["status", "--porcelain", "--", self.REL], cwd=self.repo)
        self.assertEqual(status_git.strip(), "")

    def test_regressao_1934_para_1955(self):
        self._rodar_ciclo("19/08/2026 19:34", "19/08/2026 19:55")

    def test_regressao_1955_para_2030(self):
        self._rodar_ciclo("19/08/2026 19:55", "19/08/2026 20:30")


# --------------------------------------------------------------------------
# Grupo 3e: cenario misto (secao 11 da microcorrecao) -- calibracao.json e
# multimodelo_metricas.json restaurados, resumo.json com mudanca real
# permanece, staging final contem so ele.
# --------------------------------------------------------------------------

class TestCenarioMisto(BaseRepoTestCase):
    def test_staging_final_contem_so_o_arquivo_com_mudanca_real(self):
        rel_calib = "docs/dados/calibracao.json"
        rel_multi = "docs/dados/multimodelo_metricas.json"
        rel_resumo = "docs/dados/resumo.json"

        self._commitar(rel_calib, json.dumps({"gerado_em": "t1", "total": 100}), mensagem="seed calib")
        self._commitar(
            rel_multi,
            json.dumps([{"modelo": "a", "feitos_total": 1, "atualizado_em": "t1"}]),
            mensagem="seed multi",
        )
        self._commitar(rel_resumo, json.dumps({"gerado_em": "t1", "total": 1}), mensagem="seed resumo")

        self._escrever_sem_commit(rel_calib, json.dumps({"gerado_em": "t2", "total": 100}))
        self._escrever_sem_commit(
            rel_multi, json.dumps([{"modelo": "a", "feitos_total": 1, "atualizado_em": "t2"}])
        )
        novo_resumo = json.dumps({"gerado_em": "t2", "total": 2})
        self._escrever_sem_commit(rel_resumo, novo_resumo)

        resultados = {}
        for rel in (rel_calib, rel_multi, rel_resumo):
            _p, status = fnd.processar_path(rel, cwd=self.repo)
            resultados[rel] = status

        self.assertEqual(resultados[rel_calib], fnd.STATUS_VOLATIL_RESTAURADO)
        self.assertEqual(resultados[rel_multi], fnd.STATUS_VOLATIL_RESTAURADO)
        self.assertEqual(resultados[rel_resumo], fnd.STATUS_SUBSTANTIVO)

        status_git = _git(["status", "--porcelain", "--", "docs/dados"], cwd=self.repo)
        alterados = [l[3:] for l in status_git.splitlines() if l.strip()]
        self.assertEqual(alterados, [rel_resumo])
        self.assertEqual(self._ler(rel_resumo), novo_resumo)


# --------------------------------------------------------------------------
# Grupo 4: CLI (main).
# --------------------------------------------------------------------------

class TestCli(BaseRepoTestCase):
    def _rodar_no_repo(self, argv):
        cwd_antigo = Path.cwd()
        try:
            os.chdir(self.repo)
            return fnd.main(argv)
        finally:
            os.chdir(cwd_antigo)

    def test_cli_sem_argumentos_retorna_erro(self):
        self.assertEqual(fnd.main([]), 2)

    def test_cli_restaura_e_retorna_zero(self):
        rel = "docs/dados/calibracao.json"
        self._commitar(rel, json.dumps({"gerado_em": "t1", "total": 100}))
        self._escrever_sem_commit(rel, json.dumps({"gerado_em": "t2", "total": 100}))

        codigo = self._rodar_no_repo(["--", rel])

        self.assertEqual(codigo, 0)
        self.assertEqual(json.loads(self._ler(rel)), {"gerado_em": "t1", "total": 100})

    def test_cli_json_invalido_retorna_nao_zero(self):
        rel = "docs/dados/calibracao.json"
        self._commitar(rel, json.dumps({"gerado_em": "t1", "total": 100}))
        self._escrever_sem_commit(rel, "{quebrado")

        codigo = self._rodar_no_repo(["--", rel])

        self.assertNotEqual(codigo, 0)
        self.assertEqual(self._ler(rel), "{quebrado")

    def test_cli_path_rejeitado_retorna_nao_zero(self):
        codigo = self._rodar_no_repo(["--", "fora/de/docs_dados.json"])
        self.assertNotEqual(codigo, 0)


# --------------------------------------------------------------------------
# Grupo 5: teste estatico de dashboard.yml (so leitura, sem executar nada).
# --------------------------------------------------------------------------

class TestIntegracaoDashboardYml(unittest.TestCase):
    def setUp(self):
        self.texto = (WORKFLOWS / "dashboard.yml").read_text(encoding="utf-8")
        import yaml
        with (WORKFLOWS / "dashboard.yml").open(encoding="utf-8") as f:
            self.doc = yaml.safe_load(f)
        self.on = self.doc["on"] if "on" in self.doc else self.doc[True]

    def test_schedule_30min_inalterado(self):
        self.assertEqual(self.on["schedule"][0]["cron"], "*/30 * * * *")

    def test_workflow_run_upstreams_inalterados(self):
        self.assertEqual(
            self.on["workflow_run"]["workflows"],
            [
                "Comparar modelos (lote)",
                "Multimodelo - reclassificacao",
                "Transformer fine-tuning (BERTimbau)",
            ],
        )

    def test_workflow_dispatch_presente(self):
        self.assertIn("workflow_dispatch", self.on)

    def test_concurrency_inalterada(self):
        self.assertEqual(self.doc["concurrency"]["group"], "escrita-planilha")
        self.assertEqual(self.doc["concurrency"]["cancel-in-progress"], False)

    def test_permissions_inalteradas(self):
        self.assertEqual(self.doc["permissions"]["contents"], "write")

    def test_chama_o_helper(self):
        self.assertIn("python src/filtrar_noop_dashboard.py -- ", self.texto)

    def test_helper_chamado_antes_do_git_add(self):
        idx_helper = self.texto.index("filtrar_noop_dashboard.py")
        idx_git_add = self.texto.index('git add -- "${STAGE_LIST[@]}"')
        self.assertLess(idx_helper, idx_git_add)

    def test_releitura_do_git_status_apos_o_helper(self):
        idx_helper = self.texto.index("filtrar_noop_dashboard.py")
        trecho_apos = self.texto[idx_helper:]
        self.assertIn("git status --porcelain -- docs/dados", trecho_apos)

    def test_staging_continua_por_allowlist_explicita(self):
        self.assertIn("validar_e_montar_stage", self.texto)
        self.assertIn("BLOQUEADO: arquivo(s) inesperado(s) alterado(s) em docs/dados", self.texto)

    def test_allowlist_fixas_inalterada(self):
        esperado = [
            "log_turnos_classificacao.json",
            "metricas_por_categoria.json",
            "log_turnos_reclassificacao.json",
            "metricas_experimento.json",
            "comparacao_modelos.json",
            "comparacao_categoria.json",
            "multimodelo_turnos.json",
            "multimodelo_metricas.json",
            "multimodelo_reclass_turnos.json",
            "comparacao_previsoes.json",
            "reclass_resumo.json",
            "calibracao.json",
            "registros.json",
            "calibracao_modelos.json",
            "calibracao_ajustada_modelos.json",
            "resumo.json",
            "shannon_resumo.json",
            "shannon_modelos.json",
            "jensen_shannon_modelos.json",
            "shannon_categorias.json",
            "shannon_votos.json",
        ]
        for nome in esperado:
            self.assertIn(nome, self.texto)

    def test_produtores_de_dados_inalterados(self):
        self.assertIn('python src/exportar_dashboard.py --fonte-modelos "$FONTE"', self.texto)
        self.assertIn("run: python src/analise_shannon.py", self.texto)

    def test_sem_git_add_dot_ou_dash_a(self):
        self.assertNotIn("git add .", self.texto)
        self.assertNotIn("git add -A", self.texto)

    def test_sem_theirs_ours_ou_force_em_codigo_executavel(self):
        # Linhas de comentario (que so explicam a ausencia desses padroes) sao
        # ignoradas; o que importa e nao haver uso executavel real.
        linhas_codigo = "\n".join(
            l for l in self.texto.splitlines() if not l.strip().startswith("#")
        )
        for proibido in ("-X theirs", "-X ours", "push --force", "reset --hard"):
            self.assertNotIn(proibido, linhas_codigo)


if __name__ == "__main__":
    unittest.main()
