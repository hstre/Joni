# DESi ↔ MSCE — Prototyp einer Read-only-Validierungsschicht

**Status: Experiment. Nicht Teil von Jonis autonomer Schleife. Kein Ergebnis, das man
veröffentlichen sollte — eine Vorprüfung, bevor irgendjemand irgendetwas zusagt.**

Das MSCE-Team (Yang Zhang u. a., arXiv 2607.16621, Code in `MemTensor/MemOS` unter
`apps/memos-local-plugin`) hat angeboten, DESi als epistemische Validierungsschicht an der
L2→L3-Konsolidierungsgrenze zu prototypisieren. Vor einer Zusage war eine Frage zu klären:

> **Produziert DESi auf einem echten MSCE-L3-Kandidaten überhaupt ein differenziertes Urteil —
> oder nur `insufficient-semantic-evidence`?**

Antwort: **ja, differenziert.** Wie belastbar das ist, steht unter „Was das *nicht* zeigt".

## Die Architektur, in einem Satz

MSCE konsolidiert `L1-Traces → L2-Policies f²=(φ,π,κ,ℬ,{f¹}) → L3-Weltmodell f³=(ℰ,ℐ,𝒞,{f²})`.
Der L3-Schritt nimmt eine Kohorte von L2-Policies über **Embedding-Zentroid-Ähnlichkeit
(θ_sim = 0.62)** auf, übergibt sie einem LLM-Prompt und speichert das Ergebnis.

Die Nachprüfung in `core/memory/l3/abstract.ts` verifiziert: `title` ist ein nicht-leerer String,
und `environment` / `inference` / `constraints` sind Arrays. **Das ist alles.** Nicht geprüft wird,
ob ein Eintrag durch die zitierten Belege gedeckt ist, ob er überhaupt welche zitiert, oder ob er
Gespeichertem widerspricht.

## Warum Layer 9 dafür schon Vokabular hat

Layer 9 kennt eine Stufe für „billige Rekurrenz hat die Mitglieder gefunden":
`LEXICAL_CANDIDATE`. Ihre Regel lautet, dass so ein Cluster **keine Synthese speisen darf**, bis er
semantisch gemessen wurde (`SEMANTIC_MEASURED`).

Eine θ_sim-Kohorte *ist* genau ein lexikalisch/embedding-basierter Kandidat. MSCE geht in einem
Schritt Kohorte → LLM → gespeichertes L3. Die beiden Architekturen sind sich also über **genau eine
Sache** uneinig, und für diese Sache existiert in Layer 9 bereits ein Zustand.

Deshalb erfindet der Prototyp kein neues Urteilsvokabular, sondern gibt `SemanticState` zurück:

| Layer 9 | Bedeutung für MSCE |
|---|---|
| `synthesis-eligible` | zulässig — belegt, richtig typisiert, deklarativ |
| `lexical-candidate` | als **Hypothese** halten, nicht konsolidieren |
| `human-review-required` | Typisierung prüfen (als Tatsache abgelegt, als Schluss formuliert) |
| `synthesis-rejected` | Schichtfehler oder Widerspruch |
| `insufficient-semantic-evidence` | nicht entscheidbar |

## Die fünf Prüfungen

Alle deterministisch, **kein Modellaufruf**.

| | Prüfung | Grundlage |
|---|---|---|
| C1 | **Verankerung** — löst jedes `evidenceIds` in die `policyIds`/`sourceEpisodeIds` der Zeile auf? | ein nicht auflösbares Zitat ist keine Provenienz |
| C2 | **Facetten-Typisierung** — ℰ = Existenz-Tatsachen, ℐ = Ursache→Wirkung, 𝒞 = die Umwelt-Tatsache, die etwas unsicher macht | MSCEs *eigener* Prompt-Vertrag |
| C3 | **Prozedurale Drift** — Handlungsanweisungen gehören nach L2 | derselbe Prompt verbietet sie ausdrücklich |
| C4 | **Annahme** — unbeschränkte Verallgemeinerung ohne Beleg | Annahme als Beobachtung ausgegeben |
| C5 | **Konfidenz-Provenienz** — gemeldet, nie verwendet | MSCEs `confidence` = LLM-Selbsteinschätzung × Embedding-Kohäsion; keines der Maße ist Evidenz über die Welt |

## Ergebnis auf dem Korpus

`python experiments/msce_bridge/adjudicate.py`

**Echte Fixture-Zeilen (11 Einträge aus ihren Tests):**

| Urteil | Anteil |
|---|---|
| `lexical-candidate` | 7 (64 %) |
| `synthesis-rejected` | 3 (27 %) |
| `synthesis-eligible` | 1 (9 %) |

**Verankert: 1 von 11.** Die drei Ablehnungen sind Schichtfehler, die MSCEs eigener Vertrag
verbietet und ihr Struktur-Validator durchlässt:

- `inference: "binary wheels fail" / "must compile from source"` — „must" ist Anweisung, nicht Ursache→Wirkung
- `constraints: "no --prebuilt" / "avoid binary wheels"` — die Form, die ihr Prompt wörtlich als **BAD** führt
- `constraints: "No pre-built wheels" / "avoid binary on alpine"` — dieselbe Form

## Der Gold-Standard — und ein Fehler, den er gefangen hat

MSCEs Prompt führt eigene **GOOD**-Beispiele. Ein Prüfer, der die ablehnt, ist falsch. Sie liegen
deshalb als fünfte Zeile im Korpus und sind durch einen Test verankert.

Der erste Entwurf ist daran durchgefallen. Er triggerte auf das bloße Verb „install" und verwarf

> „node_modules/ is rewritten by **npm install**; manual edits are lost on the next sync"

— eines ihrer GOOD-Beispiele. „npm install" benennt dort ein Kommando und schreibt nichts vor.
Das Muster prüft jetzt **Modal- und Vermeidungsverben, die sich an einen Leser richten**, nicht
jedes Verb, das eine Handlung bezeichnet. Nach der Korrektur: **0 von 7** GOOD-Beispielen
fälschlich abgelehnt oder fehltypisiert.

Das ist derselbe Fehlermodus wie an drei anderen Stellen dieses Projekts: ein lexikalischer Test
übertriggert, und nur echte Daten zeigen es.

## Was das *nicht* zeigt

Wichtiger als das Ergebnis:

1. **Der Korpus sind Test-Fixtures und Prompt-Beispiele, keine Produktions-LLM-Ausgabe.**
   Fixtures sind von Hand geschrieben, um die Pipeline zu treiben. Das Ergebnis zeigt, dass **das
   Tor durchlässig ist** — nicht, wie oft die Realität dagegen drückt. Die Quote „27 % Schichtfehler"
   ist **keine** Aussage über MSCEs echte Ausgabe.
2. **Die 0/7-Verankerung bei den GOOD-Beispielen ist ein Artefakt meines Korpus**, nicht ein Befund:
   ich habe diese Zeile aus dem Prompt-Text gebaut, sie hat konstruktionsbedingt keine `policyIds`.
3. **Widerspruchserkennung ist nicht implementiert.** Layer 9s `CONTRADICTORY` bräuchte den
   DESi Semantic Layer (FrameDetector, LogicalAuditor) laufend auf *ihrer* Domäne. Ob der auf
   Agenten-Interaktions-Traces sinnvolle Frames produziert, ist die eigentliche offene Frage — und
   sie ist empirisch, nicht durch Nachdenken zu beantworten.
4. **Es wurde kein Modell befragt.** Nur deterministische Prüfungen.

## Was als Nächstes zu messen wäre

Nicht Benchmarks. Zuerst: einen Satz **echter** L3-Zeilen aus einem MSCE-Lauf durch C1–C4 schicken
und die eine Frage beantworten, auf die es ankommt — **von den Einträgen, die DESi als unbelegt
markiert: wie viele waren tatsächlich falsch?** Das Ergebnis ist in beide Richtungen brauchbar.

Danach erst: Semantic Layer auf ihre Domäne, Widerspruchserkennung, Gate, Benchmarks.
