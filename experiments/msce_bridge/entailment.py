"""Claim–Evidence-Entailment-Auditor: trägt die zitierte Evidenz den Claim?

Die Frage, die DESi für den MSCE-Fall beantworten muss, ist **nicht** „wie mehrdeutig ist dieser
Satz". Sie lautet:

    gegebene Evidenz + zulässige Prämissen  ⟹  L3-Claim?

Das ist eine Ableitungsprüfung, keine semantische Entropie. Die Ebenen sind sauber getrennt:

    SPL / Semantic Layer   →  *Was* behauptet der Satz? (Relation, Modalität, Reichweite)
    DESi (dieses Modul)    →  Folgt der normalisierte Claim aus den Belegen?
    Layer 9                →  Was darf persistent werden?

Der Semantic Layer ist Zulieferer. Seine Modellabhängigkeit (§6b/§6c des Befundberichts) ist ein
Problem der *Normalisierung* — sie macht die Governance nicht hinfällig.

**Die Bauweise ist die Lehre aus acht Fehlschlägen an einem Tag.** Jeder bisherige Versuch, ein
semantisches Urteil auf eine lexikalische Regel zu stellen, ist gescheitert (Rekurrenz,
Papertitel, Schablonen, „npm install", Negations-Asymmetrie, `must`/`do not`, die
69-Wort-Frameliste, `ess`-als-Verteilung). Deshalb hier strikt:

* **Das LLM parst** — Claim und Belege werden in eine Struktur überführt: Subjekt, Relation,
  Objekt, Modalität, Quantor, Reichweite, Bedingungen. Alles aus **geschlossenen** Vokabularen.
  Das ist Klassifikation in kleine Mengen, und genau die können LLMs (§6c: 4/4).
* **Die Regeln urteilen** — Verdikt und Verstöße entstehen aus einem *Strukturvergleich*, ohne
  Modell, ohne Stichwortliste. Ein Quantorensprung ist ein Ordnungsvergleich, kein Wortfund.

Kein Verdikt behauptet, ein Claim sei falsch. `compatible_not_entailed` heisst: *die genannten
Belege tragen ihn nicht vollständig* — eine Aussage über die Ableitung, nicht über die Welt.
"""
from __future__ import annotations

import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import spl_builder as sb  # noqa: E402

PARSER = os.getenv("ENTAIL_PARSER", "beta")     # §6c: flash war 4/4 und ist billig

# ── Geschlossene Vokabulare ──────────────────────────────────────────────────────────────────────

#: Modalitätsstärke. Ein Claim darf nie stärker behaupten als seine Evidenz hergibt.
MODALITY = ("negated", "hypothetical", "possible", "probable", "asserted")
MODAL_RANK = {m: i for i, m in enumerate(MODALITY)}

#: Quantorenreichweite. singular < existential < generic < universal.
QUANTIFIER = ("singular", "existential", "generic", "universal")
QUANT_RANK = {q: i for i, q in enumerate(QUANTIFIER)}

#: Auf welcher Ebene die Aussage über ihren Gegenstand spricht.
SCOPE = ("instance", "subclass", "class")
SCOPE_RANK = {s: i for i, s in enumerate(SCOPE)}

#: Relationsfamilien - eine kausale Behauptung braucht kausale Evidenz.
CAUSAL = frozenset({"causes", "prevents", "enables", "requires"})
ASSOCIATIVE = frozenset({"correlates_with", "supports", "has_property", "measured_as"})

VERDICTS = ("entailed", "partially_entailed", "compatible_not_entailed", "contradicted",
            "insufficient")

VIOLATIONS = ("missing_premise", "causal_upgrade", "modal_strengthening", "scope_expansion",
              "unsupported_generalization", "entity_shift", "condition_dropped")


@dataclass(frozen=True)
class Structure:
    """Die normalisierte Form einer Aussage. Vom LLM gefüllt, von den Regeln gelesen."""

    text: str
    subject: str = ""
    relation: str = ""
    object: str = ""
    modality: str = "asserted"
    quantifier: str = "singular"
    scope_level: str = "instance"
    conditions: tuple[str, ...] = field(default_factory=tuple)
    #: Spricht die Aussage über die EVIDENZLAGE statt über die Sache? "No evidence of X was found"
    #: ist eine Aussage über die Suche, nicht über X. Abwesenheit von Evidenz ist kein Beweis der
    #: Abwesenheit - ohne dieses Feld ging genau dieser Schluss als `entailed` durch (DEV-017).
    epistemic_hedge: bool = False
    source_id: str = ""
    #: Felder, bei denen die k Ziehungen keine strikte Mehrheit ergaben. Sie sind NICHT bestimmt -
    #: ein Urteil, das auf ihnen ruht, wäre geraten.
    undetermined: tuple[str, ...] = field(default_factory=tuple)
    #: Übereinstimmungsgrad je Feld (Anteil der Mehrheitsstimme), für die Sichtbarkeit.
    agreement: tuple[tuple[str, float], ...] = field(default_factory=tuple)

    def key(self) -> tuple[str, str]:
        return (self.subject.lower().strip(), self.object.lower().strip())


_PARSE_SYSTEM = """You normalise ONE statement into a fixed structure. You judge nothing.

Fill every field from the CLOSED vocabularies. Do not invent values.

  relation   : {relations}
  modality   : negated | hypothetical | possible | probable | asserted
               ("may/might/could"=possible, "likely/probably"=probable, plain claim=asserted,
                "if/suppose"=hypothetical, explicit denial=negated)
               IMPORTANT 1: negation belongs HERE, never in the relation. "X does not ship Y"
               is relation=has_property with modality=negated - NOT relation=prevents.
               IMPORTANT 2: "negated" means the statement DENIES its proposition. A statement
               that REPORTS a failure or a negative outcome is asserted, not negated:
               "A wheel failed to load" = modality=asserted (a failure did occur).
               "A wheel does not fail to load" = modality=negated.
  quantifier : singular | existential | generic | universal
               (one named case=singular, "a/some/at least one"=existential,
                "typically/in general"=generic, "all/every/always/no exceptions"=universal)
  scope_level: instance | subclass | class
               (this one thing=instance, a named subgroup=subclass, the whole kind=class)
  conditions : qualifiers the statement depends on (empty if none)
               IMPORTANT: for "X happens when/if Y", the relation describes X and Y goes
               HERE. "The build succeeds when headers are installed" is relation about the
               build succeeding, with "headers are installed" as a condition.

  epistemic_hedge : true if the statement reports the STATE OF EVIDENCE rather than asserting
               the fact itself. "No evidence of X was found", "X was not observed", "no reports
               of X" -> true (these are claims about a search, not about X). "X did not happen"
               -> false (that asserts the fact). Also true for "the log states that ...".

Return JSON exactly:
{{"subject":"...","relation":"<key>","object":"...","modality":"...","quantifier":"...",
  "scope_level":"...","conditions":["..."],"epistemic_hedge":false}}"""


_SPLIT_SYSTEM = """You split ONE statement into its atomic propositions. You judge nothing.

An atomic proposition asserts exactly ONE thing about ONE subject-object pair. A statement that
asserts several things (joined by "and", ";", ",", "but", or a relative clause that adds a second
claim) has several.

Examples:
  "Alpine containers ship musl libc, no glibc."
      -> ["Alpine containers ship musl libc.", "Alpine containers do not ship glibc."]
  "Model proposals are candidates only; they do not have decision authority."
      -> ["Model proposals are candidates only.",
          "Model proposals do not have decision authority."]
  "Alpine containers ship musl libc."
      -> ["Alpine containers ship musl libc."]

Keep each proposition a self-contained sentence: resolve pronouns, repeat the subject.
Do NOT split a single claim that merely has a qualifier or a condition.

Return JSON exactly: {"propositions": ["...", "..."]}"""


#: Ziehungen je Aussage. Ungerade, damit eine strikte Mehrheit möglich ist.
K_DRAWS = int(os.getenv("ENTAIL_K", "5"))


#: Koordinationsmarker, die auf eine zusammengesetzte Aussage hindeuten KÖNNEN.
#
# Die erste Fassung traf 9/9 auf selbst geschriebenen Kontrollfällen und liess auf ECHTER
# MSCE-Ausgabe 5 von 8 Konjunktionen durch. Übersehen war die häufigste Bauform überhaupt:
# **Komma + Partizip**, das eine zweite Proposition anhängt —
#   "…filter out all candidates, CAUSING an empty output"
#   "…fails to parse it, RESULTING IN zero generation"
#   "…has final say over claims, REJECTING proposals deemed insufficient"
# dazu disjunktive Subjektlisten mit "or". Die selbst geschriebenen Testfälle prüften nur das
# eigene Modell der Sache, nicht die Sache.
_COMPOUND_MARKERS = re.compile(
    r"(;"
    r"|\band\b|\bor\b|\bbut\b|\bwhile\b|\bwhereas\b|\bas well as\b|\bmoreover\b|\balso\b"
    r"|,\s*(no|not|nor|which|who|whose|and|but|or)\b"
    r"|,\s*\w*ing\b"                     # ", causing" / ", leading to" / ", rejecting"
    r"|\bresulting in\b|\bleading to\b|\bthereby\b"
    r"|\bthey\b|\bit\b\s+\w+s\b)", re.I)


def maybe_compound(text: str) -> bool:
    """Billige, deterministische Vorprüfung: KÖNNTE diese Aussage zusammengesetzt sein?

    Zweck ist reine Kostenersparnis (§7f/§8 des Befundberichts): die Zerlegung kostet k
    Modellaufrufe je Aussage, und die grosse Mehrheit der Aussagen ist atomar. Wer nur die
    verdächtigen in den vollen Pfad schickt, spart den Rest.

    **Diese Regel ist lexikalisch — und das ist hier ausnahmsweise vertretbar**, weil ihre
    Fehlerrichtungen asymmetrisch sind:

    * *falsch positiv* (atomare Aussage wird zur Zerlegung geschickt) kostet k Aufrufe, und der
      Splitter gibt korrekt eine Proposition zurück. Kein inhaltlicher Schaden.
    * *falsch negativ* (Konjunktion wird als atomar behandelt) bringt den gefährlichsten Fehler
      des Systems zurück: ein weggefallener Konjunkt, der als ``entailed`` durchgeht.

    Sie ist deshalb bewusst **übertriggernd** eingestellt. Das ist die Umkehrung der Lehre aus den
    neun lexikalischen Fehlschlägen dieses Projekts: dort stand eine Wortregel für ein *Urteil*,
    hier nur für eine *Kostenweiche*, deren teure Seite die sichere ist.
    """
    return bool(_COMPOUND_MARKERS.search(text or ""))


def split_propositions(text: str, *, builder: str = None, k: int = None) -> tuple[list[str], bool]:
    """Zerlege eine Aussage in atomare Propositionen. Rückgabe: (Propositionen, unbestimmt).

    Grund (§7f des Befundberichts): das ``Structure``-Schema fasst genau **eine** Proposition. Bei
    einer Konjunktion fiel der zweite Konjunkt bisher ersatzlos weg - und damit konnte ein Claim,
    der etwas ausdrücklich verneint, als ``entailed`` durchgehen. Ein falsches ``entailed`` ist das
    gefährlichste Verdikt des Systems.

    Die **Anzahl** der Propositionen wird über k Ziehungen per strikter Mehrheit bestimmt. Gibt es
    darüber keine Mehrheit, ist die Zerlegung *unbestimmt* - und dann wird nicht geraten, sondern
    abgelehnt (``insufficient``). Zerlegen wo eindeutig, ablehnen wo nicht.
    """
    builder = PARSER if builder is None else builder
    k = K_DRAWS if k is None else k

    # Kostenweiche: ohne Koordinationsmarker gar nicht erst zerlegen. Spart k Aufrufe je atomarer
    # Aussage; die Fehlerrichtung ist bewusst asymmetrisch (siehe maybe_compound).
    if not maybe_compound(text):
        return [text], False

    def _one(_i):
        try:
            raw = sb._call(sb.BUILDERS[builder], f"{_SPLIT_SYSTEM}\n\nSTATEMENT: {text}",
                           temperature=0.0)
        except Exception:  # noqa: BLE001
            return None
        props = [str(p).strip() for p in (raw.get("propositions") or []) if str(p).strip()]
        return props[:6] or None

    with ThreadPoolExecutor(max_workers=min(k, 8)) as pool:
        draws = [d for d in pool.map(_one, range(k)) if d]
    if not draws:
        return [text], False                      # Zerlegung nicht möglich -> unverändert weiter

    counts: dict[int, int] = {}
    for d in draws:
        counts[len(d)] = counts.get(len(d), 0) + 1
    top_n, votes = max(counts.items(), key=lambda kv: kv[1])
    if votes * 2 <= len(draws):                   # keine strikte Mehrheit über die ANZAHL
        return [text], True                       # unbestimmt -> Aufrufer lehnt ab
    for d in draws:                               # erste Ziehung mit der Mehrheitsanzahl
        if len(d) == top_n:
            return d, False
    return [text], True

#: Felder, auf denen ein Verdikt ruht. Ist eines davon unbestimmt, wird nicht geurteilt.
CORE_FIELDS = ("relation", "modality", "quantifier", "scope_level")


def _pick(val, allowed, default):
    v = str(val or "").strip().lower()
    return v if v in allowed else default


def _draw(text: str, builder: str) -> dict | None:
    system = _PARSE_SYSTEM.format(relations=" | ".join(sb.RELATIONS))
    try:
        raw = sb._call(sb.BUILDERS[builder], f"{system}\n\nSTATEMENT: {text}", temperature=0.0)
    except Exception:  # noqa: BLE001 - eine misslungene Ziehung ist Datum, kein Absturz
        return None
    return {
        "subject": str(raw.get("subject", ""))[:120],
        "relation": _pick(raw.get("relation"), sb.RELATIONS, ""),
        "object": str(raw.get("object", ""))[:120],
        "modality": _pick(raw.get("modality"), MODALITY, "asserted"),
        "quantifier": _pick(raw.get("quantifier"), QUANTIFIER, "singular"),
        "scope_level": _pick(raw.get("scope_level"), SCOPE, "instance"),
        "conditions": tuple(str(c)[:80] for c in (raw.get("conditions") or [])[:6]),
        "epistemic_hedge": bool(raw.get("epistemic_hedge")),
    }


def parse(text: str, *, source_id: str = "", builder: str = PARSER,
          k: int = None) -> Structure:
    """Sprache → Struktur, per **Mehrheitsentscheid über k Ziehungen**.

    Der Parser ist trotz ``temperature=0.0`` nicht deterministisch - gemessen schwankte das
    Endverdikt über fünf Läufe zwischen 6/9 und 9/9. Ein einzelner Wurf ist deshalb keine
    Normalisierung, sondern eine Stichprobe.

    Jedes Feld wird über k Ziehungen ausgezählt. Fehlt einem Feld die **strikte Mehrheit**, gilt es
    als *unbestimmt* und wandert nach ``undetermined``. Die Regeln urteilen darauf nicht mehr,
    sondern geben ``insufficient`` zurück - die Uneinigkeit wird damit vom Fehler zum Signal, genau
    wie Layer 9 es an anderer Stelle schon hält.
    """
    k = K_DRAWS if k is None else k
    with ThreadPoolExecutor(max_workers=min(k, 8)) as pool:
        draws = [d for d in pool.map(lambda _: _draw(text, builder), range(k)) if d]
    if not draws:
        return Structure(text=text, source_id=source_id, undetermined=CORE_FIELDS)

    chosen: dict = {}
    undetermined: list[str] = []
    agreement: list[tuple[str, float]] = []
    for f in ("subject", "relation", "object", "modality", "quantifier", "scope_level",
              "epistemic_hedge"):
        counts: dict = {}
        for d in draws:
            counts[d[f]] = counts.get(d[f], 0) + 1
        top, n = max(counts.items(), key=lambda kv: kv[1])
        share = n / len(draws)
        chosen[f] = top
        if f in CORE_FIELDS:
            agreement.append((f, round(share, 2)))
            if n * 2 <= len(draws):          # keine strikte Mehrheit
                undetermined.append(f)
    # Bedingungen: übernehmen, was in der Mehrheit der Ziehungen überhaupt genannt wurde
    cond_counts: dict = {}
    for d in draws:
        for c in d["conditions"]:
            cond_counts[c] = cond_counts.get(c, 0) + 1
    conditions = tuple(c for c, n in cond_counts.items() if n * 2 > len(draws))

    return Structure(text=text, source_id=source_id, conditions=conditions,
                     undetermined=tuple(undetermined), agreement=tuple(agreement),
                     epistemic_hedge=bool(chosen.get("epistemic_hedge")),
                     **{f: chosen[f] for f in
                        ("subject", "relation", "object", "modality", "quantifier",
                         "scope_level")})


# ── Der deterministische Teil: Strukturvergleich, kein Modell ────────────────────────────────────

def _overlaps(a: str, b: str) -> bool:
    """Teilen zwei Entitätsbezeichnungen ein inhaltliches Wort? Bewusst grob - Entitäts-Identität
    ist eine Normalisierungsfrage (SPL), nicht die Aufgabe des Auditors."""
    wa = {w for w in a.lower().split() if len(w) > 3}
    wb = {w for w in b.lower().split() if len(w) > 3}
    return bool(wa & wb)


def check(claim: Structure, evidence: list[Structure],
          declared_assumptions: tuple[str, ...] = ()) -> tuple[str, list[str], list[str]]:
    """Verdikt + Verstösse + Begründungen. Rein deterministisch über die Strukturen."""
    if not evidence:
        return "insufficient", ["missing_premise"], ["keine Evidenz angegeben"]

    # Unbestimmte Normalisierung ⇒ kein Urteil. Wenn die k Ziehungen sich über ein tragendes Feld
    # nicht einigen konnten, ist die Aussage nicht normalisiert - und ein Verdikt darauf wäre
    # geraten, nicht abgeleitet. Das ist der Unterschied zwischen 'wir wissen es nicht' und einem
    # Zufallsergebnis, das wie ein Urteil aussieht.
    if claim.undetermined:
        return "insufficient", [], [
            f"Claim nicht eindeutig normalisierbar - unbestimmt: {', '.join(claim.undetermined)}"]
    unstable_ev = [e for e in evidence if e.undetermined]
    if unstable_ev and len(unstable_ev) == len(evidence):
        return "insufficient", [], [
            "kein Beleg eindeutig normalisierbar - unbestimmt: "
            + ", ".join(sorted({f for e in unstable_ev for f in e.undetermined}))]
    # Belege mit unbestimmten Kernfeldern tragen nichts - sie werden ausgeschlossen, nicht geraten.
    evidence = [e for e in evidence if not e.undetermined]

    violations: list[str] = []
    notes: list[str] = []

    # Widerspruch: ein Beleg behauptet dieselbe Relation zwischen denselben Entitäten, negiert.
    # Ein Widerspruch verlangt DIESELBE Proposition, einmal behauptet und einmal geleugnet -
    # nicht bloss Relationsgleichheit plus Subjektnaehe. Ohne die Objektpruefung meldete der
    # Auditor "A binary wheel failed to load" als Widerspruch zu "Binary wheels are incompatible
    # with musl", obwohl der Beleg den Claim STUETZT. (Live an der HTTP-Schnittstelle gefunden -
    # derselbe Fehlermodus wie _polarity_clash in DESi: negative Valenz als Verneinung gelesen.)
    for e in evidence:
        # Ein gehedgter Beleg ("keine Hinweise auf X gefunden") kann nichts widerlegen - er sagt
        # nichts über X, sondern über die Suche danach.
        if e.epistemic_hedge and not claim.epistemic_hedge:
            continue
        same = (e.relation == claim.relation
                and _overlaps(e.subject, claim.subject)
                and _overlaps(e.object, claim.object))
        if same and (e.modality == "negated") != (claim.modality == "negated"):
            return "contradicted", [], [
                f"Beleg '{e.source_id or e.text[:40]}' behauptet dieselbe Relation negiert"]

    # ── Positive Stützung, nicht bloss Abwesenheit von Verstössen ───────────────────────────────
    #
    # Die frühere Logik lautete "keine Verstösse gefunden ⇒ entailed". Das ist falsch:
    # **Abwesenheit erkannter Verstösse ist nicht Anwesenheit von Stützung.** Die externe
    # Blind-Evaluation hat das an drei Fällen zugleich aufgedeckt (7/20 auf dem Dev-Satz):
    #
    #   DEV-012  "A cannot be installed" aus "A depends on B" + "C is unavailable" — die Belege
    #            müssten zu einer Kette komponieren, B und C sind aber verschieden.
    #   DEV-014  "Birne war defekt" aus "Lampe ging nicht" + "getauscht, ging wieder" — Abduktion,
    #            kein Entailment; alternative Ursachen bleiben offen.
    #   DEV-017  "Data loss did not occur" aus "no evidence of data loss was found" — Abwesenheit
    #            von Evidenz ist kein Beweis der Abwesenheit.
    #
    # Alle drei sind dieselbe Wurzel: kein Beleg BEHAUPTET die Proposition des Claims, und die
    # Regeln fanden trotzdem nichts zu beanstanden. `entailed` verlangt deshalb ab jetzt einen
    # Beleg, der den Claim tatsächlich trägt.
    def _asserts(e: Structure) -> bool:
        rel_ok = (e.relation == claim.relation
                  or (claim.relation in CAUSAL and e.relation in CAUSAL))
        return (rel_ok and _overlaps(e.subject, claim.subject)
                and _overlaps(e.object, claim.object))

    support = [e for e in evidence if _asserts(e)]

    # Ein gehedgter Beleg ("no evidence of X was found") trägt keine Aussage ÜBER X. Er kann einen
    # ungehedgten Claim nicht stützen - die dafür nötige Prämisse ("wäre X eingetreten, hätte man
    # Evidenz gefunden") ist nicht angegeben.
    hedged_only = bool(support) and all(e.epistemic_hedge for e in support) \
        and not claim.epistemic_hedge
    if hedged_only:
        violations.append("missing_premise")
        notes.append("Beleg spricht über die Evidenzlage ('keine Hinweise gefunden'), nicht über "
                     "die Sache - Abwesenheit von Evidenz ist kein Beweis der Abwesenheit")
        support = []

    if not support:
        # Berührt die Evidenz den Claim überhaupt? Wenn nicht, ist die Kette gerissen bzw. die
        # Evidenz spricht über andere Entitäten - dann wird nicht 'nicht gedeckt', sondern
        # 'nicht entscheidbar' gemeldet.
        touching = [e for e in evidence
                    if _overlaps(e.subject, claim.subject) or _overlaps(e.object, claim.object)
                    or _overlaps(e.subject, claim.object) or _overlaps(e.object, claim.subject)]
        if "missing_premise" not in violations:
            violations.append("missing_premise")
        if not touching:
            notes.append("kein Beleg berührt die Entitäten des Claims - Ableitungskette gerissen")
            return "insufficient", violations, notes
        notes.append("kein Beleg behauptet die Proposition des Claims; die Belege sind damit "
                     "vereinbar, tragen sie aber nicht (alternative Erklärungen bleiben offen)")
        return "compatible_not_entailed", violations, notes

    # Kausal-Aufwertung: kausaler Claim, aber nur assoziative Evidenz.
    if claim.relation in CAUSAL and not any(e.relation in CAUSAL for e in evidence) \
            and any(e.relation in ASSOCIATIVE for e in evidence):
        violations.append("causal_upgrade")
        notes.append(f"Claim behauptet '{claim.relation}', Evidenz nur assoziativ "
                     f"({', '.join(sorted({e.relation for e in evidence}))})")

    relevant = support   # nur tatsächlich stützende Belege dürfen decken
    ev_modal = max(MODAL_RANK.get(e.modality, 4) for e in relevant)
    if MODAL_RANK.get(claim.modality, 4) > ev_modal:
        violations.append("modal_strengthening")
        notes.append(f"Claim ist '{claim.modality}', stärkster Beleg nur "
                     f"'{MODALITY[ev_modal]}'")

    # Unbelegte Verallgemeinerung: Quantorensprung.
    ev_quant = max(QUANT_RANK.get(e.quantifier, 0) for e in relevant)
    if QUANT_RANK.get(claim.quantifier, 0) > ev_quant:
        violations.append("unsupported_generalization")
        notes.append(f"Claim quantifiziert '{claim.quantifier}', Evidenz nur "
                     f"'{QUANTIFIER[ev_quant]}'")

    # Reichweitenerweiterung: der Claim spricht über eine breitere Ebene als jeder Beleg.
    ev_scope = max(SCOPE_RANK.get(e.scope_level, 0) for e in relevant)
    if SCOPE_RANK.get(claim.scope_level, 0) > ev_scope:
        violations.append("scope_expansion")
        notes.append(f"Claim spricht auf Ebene '{claim.scope_level}', Evidenz nur "
                     f"'{SCOPE[ev_scope]}'")

    # Entitätswechsel: das Claim-Subjekt taucht in keinem Beleg auf.
    if claim.subject and not any(_overlaps(claim.subject, e.subject) or
                                 _overlaps(claim.subject, e.object) for e in evidence):
        violations.append("entity_shift")
        notes.append(f"Claim-Subjekt '{claim.subject}' kommt in keinem Beleg vor")

    # Fallengelassene Bedingung: ein Beleg gilt nur unter Vorbehalt, der Claim nennt ihn nicht.
    declared = " ".join(declared_assumptions).lower()
    for e in evidence:
        for cond in e.conditions:
            if cond.lower() not in " ".join(claim.conditions).lower() and \
                    cond.lower() not in declared:
                violations.append("condition_dropped")
                notes.append(f"Bedingung '{cond}' aus dem Beleg fehlt im Claim")
                break
        if "condition_dropped" in violations:
            break

    # Fehlende Prämisse: kein Beleg berührt die behauptete Relation.
    if claim.relation and not any(e.relation == claim.relation for e in evidence) and \
            "causal_upgrade" not in violations:
        violations.append("missing_premise")
        notes.append(f"kein Beleg behauptet die Relation '{claim.relation}'")

    violations = list(dict.fromkeys(violations))
    if not violations:
        return "entailed", [], ["Relation, Modalität, Quantor und Reichweite sind gedeckt"]
    # nur eine fallengelassene Bedingung: der Kern trägt, der Rand nicht
    if violations == ["condition_dropped"]:
        return "partially_entailed", violations, notes
    return "compatible_not_entailed", violations, notes


def combine(verdicts: list[str]) -> str:
    """Ein Claim aus mehreren Konjunkten ist nur so stark wie sein schwächster Teil.

    Deterministisch, ohne Modell. Die Reihenfolge ist die Sicherheitsreihenfolge: ein einziger
    widersprochener Konjunkt macht den ganzen Claim widersprochen, und ``entailed`` verlangt, dass
    **jeder** Teil getragen ist. So kann ein weggefallener oder ungedeckter Konjunkt nie mehr in
    ein Gütesiegel für das Ganze münden (§7f).
    """
    if not verdicts:
        return "insufficient"
    if "contradicted" in verdicts:
        return "contradicted"
    if all(v == "entailed" for v in verdicts):
        return "entailed"
    if "insufficient" in verdicts:
        return "insufficient"
    if all(v in ("entailed", "partially_entailed") for v in verdicts):
        return "partially_entailed"
    return "compatible_not_entailed"


def audit(claim: str, evidence: list[dict], *, declared_assumptions: tuple[str, ...] = (),
          context: str = "", builder: str = PARSER) -> dict:
    """Volle Prüfung. Zerlegen → parsen (LLM, parallel) → deterministisch urteilen.

    Zusammengesetzte Aussagen werden in atomare Propositionen zerlegt und **jede einzeln** geprüft;
    das Gesamturteil ist das schwächste Teilurteil (``combine``). Ist die Zerlegung selbst nicht
    eindeutig, wird abgelehnt statt geraten.
    """
    claim_props, split_undet = split_propositions(claim, builder=builder)
    if split_undet:
        return {"claim": claim, "context": context, "verdict": "insufficient", "violations": [],
                "notes": ["Zerlegung der Aussage nicht eindeutig - es wird nicht auf einem "
                          "Teilparse geurteilt"],
                "claim_structure": {}, "evidence_structures": [], "propositions": [claim]}

    # Belege ebenfalls zerlegen: jeder atomare Teil ist ein eigenständiger Beleg. Das kann nur
    # mehr Stützung sichtbar machen, nie weniger.
    ev_items: list[dict] = []
    for e in evidence:
        parts, undet = split_propositions(e["text"], builder=builder)
        if undet:
            parts = [e["text"]]
        ev_items += [{"text": p, "source_id": e.get("source_id", "")} for p in parts]

    with ThreadPoolExecutor(max_workers=8) as pool:
        c_futs = [pool.submit(parse, p, builder=builder) for p in claim_props]
        e_futs = [pool.submit(parse, e["text"], source_id=e["source_id"], builder=builder)
                  for e in ev_items]
        cs = [f.result() for f in c_futs]
        ev = [f.result() for f in e_futs]

    per_part = [check(c, ev, declared_assumptions) for c in cs]
    verdict = combine([v for v, _vi, _n in per_part])
    violations = list(dict.fromkeys(v for _vd, vi, _n in per_part for v in vi))
    notes: list[str] = []
    for i, (_vd, _vi, ns) in enumerate(per_part):
        prefix = f"[Teil {i + 1}/{len(cs)}] " if len(cs) > 1 else ""
        notes += [prefix + n for n in ns]
    c = cs[0]
    return {"claim": claim, "context": context, "verdict": verdict, "violations": violations,
            "notes": notes,
            "propositions": [c.text for c in cs],
            "per_proposition": [{"text": cs[i].text, "verdict": per_part[i][0],
                                 "violations": per_part[i][1]} for i in range(len(cs))],
            "claim_structure": {"subject": c.subject, "relation": c.relation, "object": c.object,
                                "modality": c.modality, "quantifier": c.quantifier,
                                "scope_level": c.scope_level, "conditions": list(c.conditions),
                                "undetermined": list(c.undetermined),
                                "agreement": dict(c.agreement)},
            "evidence_structures": [
                {"source_id": e.source_id, "relation": e.relation, "modality": e.modality,
                 "quantifier": e.quantifier, "scope_level": e.scope_level,
                 "conditions": list(e.conditions), "undetermined": list(e.undetermined),
                 "agreement": dict(e.agreement)} for e in ev]}


def render(res: dict) -> str:
    lines = [f"CLAIM: {res['claim']}",
             f"  ⇒ {res['verdict'].upper()}"]
    for v in res["violations"]:
        lines.append(f"     ✗ {v}")
    for n in res["notes"]:
        lines.append(f"       · {n}")
    return "\n".join(lines)


__all__ = ["Structure", "parse", "check", "audit", "render", "VERDICTS", "VIOLATIONS",
           "MODALITY", "QUANTIFIER", "SCOPE"]
