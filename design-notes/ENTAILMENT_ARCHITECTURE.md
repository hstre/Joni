# Entailment-Architektur v2 — Modell urteilt, Regeln vetoen

**Festgezurrt 2026-07-29 · abgeleitet aus Messungen, nicht aus Entwurf**

---

## Warum v1 verworfen wurde

v1 liess **Regeln über normalisierten Strukturen urteilen**. Auf einer extern konstruierten
Blind-Evaluation:

| Verfahren | Verdikte | Falschdurchlässe | Läufe |
|---|---|---|---|
| v1: Regeln urteilen | **7/20** | **3** | 1 |
| v1 nach Verschärfung | 5/20 | 1 | 1 |
| **Modell urteilt direkt** | **18, 17, 17 /20** | **0, 0, 0** | 3 |

Das Modell trifft **genau die Fälle**, die für Regeln architektonisch unerreichbar sind:
Weltwissen (39,1 °C ist Fieber), mehrstufige Ketten, Abduktion, epistemische Operatoren.

Der Grundsatz „LLM für Sprache, Regeln für Logik" bleibt richtig — **für Governance**. Für die
Ableitungsprüfung selbst war er falsch: sie braucht Weltwissen und Komposition, und Regeln über
einer dünnen Struktur haben dafür nicht die Auflösung.

---

## Die vier Schichten

```
1  MODELL          schlägt Verdikt + Begründung vor
                   ↓
2  KONTROLLEN      deterministisch, prüfen bekannte Gefahrenmuster
                   ↓  (dürfen NUR herabstufen)
3  DESi            akzeptiert · stuft herab · verlangt Prüfung
                   ↓
4  LAYER 9         persistiert ausschliesslich das Gegovernte
```

### 1 — Modell

Urteilt über die Ableitung. Bekommt Claim, Evidenz, deklarierte Annahmen. Liefert ein Verdikt aus
geschlossenem Vokabular plus Begründung. **k Ziehungen, Mehrheitsentscheid** — ohne Mehrheit gilt
das Ergebnis als unbestimmt.

Gemessen: `deepseek-v4-flash` erreicht 17–18/20 bei null Falschdurchlässen und ist damit besser als
`deepseek-v4-pro` (15/20, ein Falschdurchlass). Das kleine Modell ist hier auch das richtige.

### 2 — Kontrollen

Deterministisch, ohne Modell, über den normalisierten Strukturen. Sie prüfen **ausschliesslich die
gemessenen Gefahrenmuster** — jedes stammt aus einem realen Fehlschlag, nicht aus Vermutung.

### 3 — DESi

Wendet die Kontrollen auf das Modellurteil an und entscheidet: annehmen, herabstufen, oder zur
Prüfung geben. **Die Herabstufung ist die einzige Richtung.**

### 4 — Layer 9

Unverändert. Persistiert nur, was Schicht 3 freigibt.

---

## Die tragende Invariante

> **Kontrollen dürfen ein Verdikt nur auf der Durchlass-Leiter nach unten bewegen.
> Sie können niemals ein Urteil erzeugen, verschärfen zu `contradicted`, oder eines heraufstufen.**

Die Leiter:

```
entailed  >  partially_entailed  >  compatible_not_entailed  >  insufficient
```

`contradicted` liegt **ausserhalb** der Leiter. Eine Kontrolle darf es nie setzen — einen
Widerspruch zu *behaupten* ist eine positive Aussage, und genau daran sind Regeln nachweislich
gescheitert (die Negations-Heuristik in `_polarity_clash`: 43 % Falschmeldungen). `contradicted`
kann nur vom Modell kommen.

### Warum das die Fehlerrichtung umkehrt

In v1 konnten Parserfehler **Falschdurchlässe** erzeugen — ein verschluckter Konjunkt wurde zu
`entailed`. In v2 speist der Parser nur noch die Kontrollen. Ein Parserfehler kann deshalb:

* eine Kontrolle **verfehlen** → das Modellurteil bleibt stehen (kein neuer Schaden), oder
* eine Kontrolle **fälschlich auslösen** → Herabstufung → eine Falschsperre.

**Beides ist die sichere Seite.** Die Instabilität der Normalisierung, die v1 gefährlich machte,
kann in v2 nur noch zu Überstrenge führen.

---

## Der Kontrollkatalog

Jede Kontrolle nennt den gemessenen Fall, der sie nötig gemacht hat.

| Kontrolle | Prüft | Herkunft |
|---|---|---|
| `evidence_padding` | Trägt die Evidenz den Claim über **Entitätsbezug**, nicht nur über Relationsgleichheit? | §7g: zwei unverwandte Belege mit universellem Quantor kippten ein Urteil auf `entailed`; ausnutzbar, weil ein Generator seine Zitate selbst wählt |
| `conjunction_coverage` | Ist **jede** Proposition einer zusammengesetzten Aussage abgedeckt? | §7f: „ships musl, **no glibc**" wurde auf den ersten Konjunkt reduziert → falsches `entailed` |
| `epistemic_hedge` | Stützt sich ein ungehedgter Claim auf Belege, die nur die **Evidenzlage** beschreiben? | DEV-017: „no evidence of data loss was found" ⟹ „data loss did not occur" |
| `quantifier_escalation` | Quantifiziert der Claim weiter als jeder stützende Beleg? | Standardfall unbelegter Verallgemeinerung |
| `modality_escalation` | Behauptet der Claim sicherer als der stärkste stützende Beleg? | Standardfall Modalitätsverstärkung |
| `scope_escalation` | Spricht der Claim auf breiterer Ebene als die Evidenz? | Standardfall Reichweitenerweiterung |

**Alle sechs stufen um genau eine Stufe herab**, ausser `conjunction_coverage` bei einem
widersprochenen Konjunkt — dort greift die Konjunktionsregel aus v1 (das Ganze ist so stark wie
sein schwächster Teil), aber auch die nur nach unten.

---

## Kostenregel

Kontrollen laufen **nur auf durchlassenden Verdikten** (`entailed`, `partially_entailed`).

Das ist keine Sparmassnahme, sondern folgt aus der Invariante: Wer nur herabstufen darf, hat bei
einem bereits niedrigen Verdikt nichts zu tun. Praktisch spart es den gesamten Parser-Aufwand für
die Mehrheit der Fälle — im Dev-Satz sind das rund zwei Drittel.

---

## Was NICHT Teil des Urteils ist

* **Weltwissens-Adapter** (Wikidata + PubMed) — liefert *Zitate für Lücken*, nie Wahrheitsurteile.
  „Kein Treffer" ist niemals eine Widerlegung.
* **Commonsense-Regelbestand** — benennt *Annahmen* mit Regel-ID und Anwendungsgrenze. Eine
  defeasible Regel deckelt ein Verdikt auf `partially_entailed` und kann es nie heben.

Beide reichern die **Begründung** an, nicht das Verdikt.

---

## Invarianten, die getestet sein müssen

1. Keine Kontrolle hebt ein Verdikt.
2. Keine Kontrolle setzt `contradicted`.
3. Ohne ausgelöste Kontrolle ist das Ergebnis **identisch** mit dem Modellurteil.
4. Kontrollen laufen nicht auf nicht-durchlassenden Verdikten.
5. Die Antwort weist jeden Teil seiner Herkunft zu (Modell vs. Regel).
6. Ein unbestimmtes Modellurteil (keine Mehrheit) ergibt `insufficient`, nie ein geratenes.

---

## Messregel für v2

Die Nachfolgearchitektur muss auf dem Dev-Satz **mindestens die Baseline erreichen** (17–18/20).
Liegt sie darunter, schaden die Kontrollen mehr als sie nützen — dann sind sie zu scharf, nicht
das Modell zu schwach.

**Der Blind-Satz bleibt versiegelt**, bis v2 steht: einmal laufen, Vorhersagen einfrieren, dann
erst den Schlüssel öffnen — und danach nicht mehr nachjustieren. Der Dev-Satz ist als
Messinstrument verbraucht, weil an ihm diagnostiziert wurde.
