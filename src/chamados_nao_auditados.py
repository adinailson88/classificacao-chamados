"""Lista de chamados ainda nao auditados, ordenada pela divergencia do modelo.

Treina o LinearSVC com todos os chamados do corte (rotulo = referencia revisada) e prediz os chamados
do export do GLPI que nao constam do corte. Os que o modelo manda para outra categoria que nao a
registrada formam a fila de conferencia. Entradas com texto de chamados: nada daqui deve ser versionado.

Uso:
    python src/chamados_nao_auditados.py --snapshot snapshot_B.json --glpi dados/glpi_chamados.csv --saida lista.csv
"""
import argparse
import csv
import json
import sys

sys.path.insert(0, "src")
import retreinar_modelos_canonicos as rmc  # noqa: E402

csv.field_size_limit(10 ** 9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--glpi", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()

    valores = json.load(open(a.snapshot, encoding="utf-8"))["values"]
    cab = valores[0]
    ix = {c: i for i, c in enumerate(cab)}
    treino = [dict(zip(cab, lin + [""] * (len(cab) - len(lin)))) for lin in valores[1:] if lin and lin[0]]
    no_corte = {str(r["id_chamado"]) for r in treino}
    treino = [r for r in treino if r["referencia_humana"]]
    taxonomia = {r["categoria_historica"] for r in treino} | {r["referencia_humana"] for r in treino}

    novos = []
    fora_taxonomia = 0
    with open(a.glpi, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["id"] in no_corte or not r["categoria"]:
                continue
            if r["categoria"] not in taxonomia:  # projetos, memoriais e orcamentos ficam fora da taxonomia de manutencao
                fora_taxonomia += 1
                continue
            desc = "Descrição - " + (r["descricao"] or "").strip()
            if (r.get("solucao") or "").strip():
                desc += "\n\nHistórico / solução - " + r["solucao"].strip()
            novos.append({"id": r["id"], "titulo": r["titulo"], "descricao_glpi": desc, "titulo_osm": "", "descricao_osm": "",
                          "categoria": r["categoria"], "abertura": r["data_abertura"][:10], "status": r["status"]})

    modelo = rmc.zoo.criar_modelo("linear_svc")
    modelo.fit([rmc.montar_texto(r) for r in treino], [r["referencia_humana"] for r in treino])
    prev, score = modelo.predict_score([rmc.montar_texto(r) for r in novos])
    for r, p, s in zip(novos, prev, score):
        r["sugerida"], r["confianca"] = str(p), float(s)
        r["diverge"] = r["sugerida"] != r["categoria"]
    novos.sort(key=lambda r: (not r["diverge"], -r["confianca"]))

    with open(a.saida, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Posição", "ID Chamado", "Abertura", "Status", "Título", "Categoria registrada", "Categoria sugerida pelo modelo", "Confiança", "Conferir?"])
        for i, r in enumerate(novos, 1):
            w.writerow([i, r["id"], r["abertura"], r["status"], " ".join(r["titulo"].split())[:80], r["categoria"], r["sugerida"],
                        f"{r['confianca']:.2f}".replace(".", ","), "SIM" if r["diverge"] else "não"])
    print(len(treino), "no treino;", len(novos), "chamados sem auditoria;", sum(r["diverge"] for r in novos), "divergem;", fora_taxonomia, "fora da taxonomia")


if __name__ == "__main__":
    main()
