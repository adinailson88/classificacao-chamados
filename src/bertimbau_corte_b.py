#!/usr/bin/env python3
"""BERTimbau ajustado (fine-tuning) no corte B, sob as mesmas partições (Trilha B).

Baseline moderno para a comparacao principal: o BERTimbau base e ajustado a cada
dobra de treino (cinco dobras, StratifiedGroupKFold ja congelado) e prediz a dobra
de teste, de modo que a acuracia fora de dobra e comparavel a dos demais modelos.
A perda usa pesos de classe balanceados (como os demais modelos), o comprimento
maximo e 128 tokens, o lote e agrupado por comprimento para reduzir preenchimento e
nao ha busca de hiperparametros. Cada dobra concluida e gravada em disco, e a
execucao retoma do ponto em que parou. Roda em CPU; o tempo de cada dobra e
registrado. Saem so identificadores com hash, categorias e metricas agregadas.

Uso: python src/bertimbau_corte_b.py --snapshot-json snapshot.json --trabalho pasta_local
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = "neuralmind/bert-base-portuguese-cased"
RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "dados" / "trilha_b"


def lotes_por_comprimento(comprimentos: list[int], tamanho: int, rng: random.Random) -> list[list[int]]:
    """Agrupa indices de comprimento parecido em lotes e embaralha a ordem dos lotes."""
    ordem = sorted(range(len(comprimentos)), key=lambda i: (comprimentos[i], rng.random()))
    lotes = [ordem[i:i + tamanho] for i in range(0, len(ordem), tamanho)]
    rng.shuffle(lotes)
    return lotes


def pesos_balanceados(rotulos: list[int], n_classes: int) -> list[float]:
    cont = [0] * n_classes
    for r in rotulos:
        cont[r] += 1
    n = len(rotulos)
    return [n / (n_classes * c) if c else 0.0 for c in cont]


def metricas(verdade: list[str], previsto: list[str]) -> dict[str, float]:
    classes = sorted(set(verdade))
    acc = sum(v == p for v, p in zip(verdade, previsto)) / len(verdade)
    f1s = []
    for c in classes:
        tp = sum(v == c and p == c for v, p in zip(verdade, previsto))
        fp = sum(v != c and p == c for v, p in zip(verdade, previsto))
        fn = sum(v == c and p != c for v, p in zip(verdade, previsto))
        f1s.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return {"acuracia": round(acc, 4), "macro_f1": round(sum(f1s) / len(f1s), 4)}


def ajustar_e_prever(tok, textos_tr, y_tr, textos_te, n_classes, epocas, lote, lr, semente, log):
    import torch
    from transformers import AutoModelForSequenceClassification, get_linear_schedule_with_warmup

    torch.manual_seed(semente)
    rng = random.Random(semente)
    modelo = AutoModelForSequenceClassification.from_pretrained(BASE, num_labels=n_classes)
    enc_tr = tok(textos_tr, truncation=True, max_length=128)["input_ids"]
    comp = [len(x) for x in enc_tr]
    pesos = torch.tensor(pesos_balanceados(y_tr, n_classes), dtype=torch.float)
    perda = torch.nn.CrossEntropyLoss(weight=pesos)
    opt = torch.optim.AdamW(modelo.parameters(), lr=lr, weight_decay=0.01)
    passos = epocas * ((len(textos_tr) + lote - 1) // lote)
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * passos), passos)
    modelo.train()
    feito = 0
    for ep in range(epocas):
        for ix in lotes_por_comprimento(comp, lote, rng):
            b = tok.pad({"input_ids": [enc_tr[i] for i in ix]}, return_tensors="pt")
            saida = modelo(input_ids=b["input_ids"], attention_mask=b["attention_mask"]).logits
            p = perda(saida, torch.tensor([y_tr[i] for i in ix]))
            p.backward()
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            feito += 1
            if feito % 50 == 0:
                log(f"  passo {feito}/{passos} perda {p.item():.3f}")
    modelo.eval()
    enc_te = tok(textos_te, truncation=True, max_length=128)["input_ids"]
    ordem = sorted(range(len(textos_te)), key=lambda i: len(enc_te[i]))
    previsto = [0] * len(textos_te)
    with torch.no_grad():
        for i in range(0, len(ordem), 64):
            ix = ordem[i:i + 64]
            b = tok.pad({"input_ids": [enc_te[j] for j in ix]}, return_tensors="pt")
            lg = modelo(input_ids=b["input_ids"], attention_mask=b["attention_mask"]).logits
            sm = torch.softmax(lg, dim=1)
            for j, k in zip(ix, sm.argmax(dim=1).tolist()):
                previsto[j] = (k, float(sm[ix.index(j), k]))
    return previsto


def main() -> int:
    from transformers import AutoTokenizer

    import trilha_b as tb

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot-json", type=Path, required=True)
    p.add_argument("--trabalho", type=Path, required=True, help="pasta local para resultados parciais")
    p.add_argument("--epocas", type=int, default=2)
    p.add_argument("--lote", type=int, default=16)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--dobras", default="1,2,3,4,5")
    args = p.parse_args()
    args.trabalho.mkdir(parents=True, exist_ok=True)

    manifesto = json.loads(tb.MANIFESTO_B.read_text(encoding="utf-8"))
    linhas = tb.ler_snapshot_json(args.snapshot_json)
    tb.verificar_snapshot(linhas, manifesto)
    corpus = tb.preparar_corpus(tb.registros_do_snapshot(linhas), tb.carregar_particoes_b())
    textos, rotulos, dobras, chaves = corpus["textos"], corpus["rotulos"], corpus["dobras"], corpus["chaves"]
    classes = sorted(set(rotulos))
    idx = {c: i for i, c in enumerate(classes)}
    tok = AutoTokenizer.from_pretrained(BASE)
    log = lambda s: print(s, flush=True)  # noqa: E731

    for dobra in [int(x) for x in args.dobras.split(",")]:
        arq = args.trabalho / f"dobra_{dobra}.csv"
        if arq.exists():
            log(f"dobra {dobra} ja concluida")
            continue
        tr = [i for i, d in enumerate(dobras) if d != dobra]
        te = [i for i, d in enumerate(dobras) if d == dobra]
        log(f"dobra {dobra}: treino {len(tr)} teste {len(te)}")
        t0 = time.time()
        prev = ajustar_e_prever(tok, [textos[i] for i in tr], [idx[rotulos[i]] for i in tr],
                                [textos[i] for i in te], len(classes), args.epocas, args.lote,
                                args.lr, args.semente, log)
        seg = time.time() - t0
        with open(arq, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id_sha256", "dobra", "referencia_humana", "modelo", "previsto", "confianca", "segundos_dobra"])
            for i, (k, conf) in zip(te, prev):
                w.writerow([chaves[i], dobra, rotulos[i], "bertimbau_ft", classes[k], f"{conf:.6f}", round(seg, 1)])
        log(f"dobra {dobra} concluida em {seg / 60:.1f} min")

    todas = []
    for dobra in range(1, 6):
        arq = args.trabalho / f"dobra_{dobra}.csv"
        if arq.exists():
            todas += list(csv.DictReader(open(arq, encoding="utf-8")))
    if len({r["dobra"] for r in todas}) == 5:
        verdade = [r["referencia_humana"] for r in todas]
        previsto = [r["previsto"] for r in todas]
        seg = sum({r["dobra"]: float(r["segundos_dobra"]) for r in todas}.values())
        saida = {"modelo": "bertimbau_ft", "base": BASE, "epocas": args.epocas, "lote": args.lote,
                 "lr": args.lr, "semente": args.semente, "n": len(todas), **metricas(verdade, previsto),
                 "segundos_total_5_dobras": round(seg, 1),
                 "hash_corte": manifesto.get("impressoes_digitais", {}).get("hash_corte")}
        (SAIDA / "bertimbau_corte_b.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(SAIDA / "bertimbau_corte_b_predicoes.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id_sha256", "dobra", "referencia_humana", "modelo", "previsto", "confianca"])
            w.writeheader()
            for r in todas:
                w.writerow({k: r[k] for k in w.fieldnames})
        log(json.dumps(saida, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
