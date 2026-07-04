"""The live seam for the Personal Store: operator statements enter as CONFIRMED, the store decays,
and the re-confirmation queue is surfaced. Phase-1 scope (preferences, projects) is enforced."""
from joni.autonomy import personal_intake
from joni.personal.store import PersonalStore, Status, Use, use_policy


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _store(tmp):
    return PersonalStore(tmp / "personal.json", tmp / "protocol.jsonl")


def test_operator_statement_enters_as_confirmed_and_usable(tmp_path):
    inbox = tmp_path / "inbox.txt"
    inbox.write_text("preferences | prefers direct honest feedback\n"
                     "projects | DESi: 4 islands confirmed\n"
                     "# a comment line is ignored\n"
                     "relationships | <a third-party note>\n",     # out of phase-1 scope -> dropped
                     encoding="utf-8")
    store = _store(tmp_path)
    res = personal_intake.interact(store, _Proto(), 1, tick=0,
                                   inbox_path=inbox, reconfirm_path=tmp_path / "rc.md")
    assert res["entered"] == 2                                    # relationships dropped
    claims = store.all()
    assert len(claims) == 2
    assert all(c.status is Status.CONFIRMED for c in claims)      # operator = trusted human
    assert all(use_policy(c) is Use.ASSERT for c in claims)       # confirmed self -> assertable
    # the drop box is reset to the template so the operator does not re-enter the same lines
    reset = inbox.read_text(encoding="utf-8")
    assert "kategorie | aussage" in reset and "prefers direct" not in reset


def test_reconfirm_sheet_is_written_each_cycle(tmp_path):
    rc = tmp_path / "rc.md"
    personal_intake.interact(_store(tmp_path), _Proto(), 1, tick=0,
                             inbox_path=tmp_path / "inbox.txt", reconfirm_path=rc)
    assert rc.exists() and "korrigieren" in rc.read_text(encoding="utf-8").lower()


def test_parse_inbox_drops_unknown_category_and_malformed_lines():
    rows = personal_intake.parse_inbox(
        "preferences | ok\n"
        "goals | out of scope\n"          # not in phase-1 CATEGORIES
        "no pipe at all\n"
        "  | empty category\n"
        "projects |    \n"                # empty statement
    )
    assert rows == [("preferences", "ok")]
