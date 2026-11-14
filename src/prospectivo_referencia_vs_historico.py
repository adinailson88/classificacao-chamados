import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "src")
import trilha_b as tb
import corte_b as cb

snap = sys.argv[1]
manifesto = json.loads(tb.MANIFESTO_B.read_text(encoding="utf-8"))
linhas = tb.ler_snapshot_json(snap)
tb.verificar_snapshot(linhas, manifesto)
registros = tb.registros_do_snapshot(linhas)
corpus = tb.preparar_corpus(registros, tb.carregar_particoes_b())
por_digest = {tb._digest(r["id"]): r for r in registros}
n = len(corpus["textos"])
hist = [i for i in range(n) if corpus["periodos"][i] == cb.PERIODO_HISTORICO]
prosp = [i for i in range(n) if corpus["periodos"][i] == cb.PERIODO_PROSPECTIVO]
print("treino", len(hist), "teste", len(prosp))
modelo = tb.rmc.zoo.criar_modelo("linear_svc")
modelo.fit([corpus["textos"][i] for i in hist], [corpus["rotulos"][i] for i in hist])
prev, _ = modelo.predict_score([corpus["textos"][i] for i in prosp])
prev = [str(p) for p in prev]
ref = [corpus["rotulos"][i] for i in prosp]
histo = [por_digest[corpus["chaves"][i]]["categoria_historica"] for i in prosp]
acc = lambda a, b: round(sum(x == y for x, y in zip(a, b)) / len(a), 4)
print("acuracia contra a referencia:", acc(prev, ref))
print("acuracia contra o historico:", acc(prev, histo))
print("historico != referencia no teste:", sum(a != b for a, b in zip(histo, ref)), "de", len(prosp))
# separacao: chamados em que historico = referencia
iguais = [j for j in range(len(prosp)) if histo[j] == ref[j]]
dif = [j for j in range(len(prosp)) if histo[j] != ref[j]]
print("onde historico = referencia: n", len(iguais), "acc", acc([prev[j] for j in iguais], [ref[j] for j in iguais]))
print("onde historico != referencia: n", len(dif), "acc vs ref", acc([prev[j] for j in dif], [ref[j] for j in dif]),
      "| acc vs historico", acc([prev[j] for j in dif], [histo[j] for j in dif]))
