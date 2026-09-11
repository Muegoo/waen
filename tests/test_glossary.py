import json

from waen.translate.glossary import (
    DEFAULT_TEMPLATES,
    Glossary,
    translate_with_glossary,
)

TEMPLATE = "[[{i}]]"


class FakeTranslator:
    def __init__(self, rule=None):
        self.rule = rule or (lambda text: f"TH<{text}>")
        self.calls: list[list[str]] = []

    def translate_many(self, texts):
        self.calls.append(list(texts))
        return [self.rule(text) for text in texts]


def test_keep_term_is_replaced_by_a_placeholder():
    glossary = Glossary(keep=["Ryuji"], mapping={})
    protected, replacements = glossary.protect("Ryuji is late again.", TEMPLATE)
    assert protected == "[[0]] is late again."
    assert replacements == ["Ryuji"]


def test_mapped_term_carries_the_thai_replacement():
    glossary = Glossary(keep=[], mapping={"Palace": "พาเลซ"})
    protected, replacements = glossary.protect("Enter the Palace.", TEMPLATE)
    assert protected == "Enter the [[0]]."
    assert replacements == ["พาเลซ"]


def test_restore_puts_the_replacement_back():
    glossary = Glossary(keep=[], mapping={"Palace": "พาเลซ"})
    _, replacements = glossary.protect("Enter the Palace.", TEMPLATE)
    assert glossary.restore("เข้าไปใน [[0]]", replacements, TEMPLATE) == "เข้าไปใน พาเลซ"


def test_restore_tolerates_spaces_google_may_insert():
    glossary = Glossary(keep=["Ryuji"], mapping={})
    _, replacements = glossary.protect("Ryuji is here.", TEMPLATE)
    assert glossary.restore("[ [ 0 ] ] อยู่นี่", replacements, TEMPLATE) == "Ryuji อยู่นี่"


def test_longest_phrase_wins_over_its_substring():
    glossary = Glossary(keep=[], mapping={"Velvet Room": "ห้องกำมะหยี่", "Room": "ห้อง"})
    protected, replacements = glossary.protect("Back to the Velvet Room.", TEMPLATE)
    assert protected == "Back to the [[0]]."
    assert replacements == ["ห้องกำมะหยี่"]


def test_word_boundary_prevents_matching_inside_a_longer_word():
    glossary = Glossary(keep=["Ann"], mapping={})
    protected, _ = glossary.protect("Announcement from Ann.", TEMPLATE)
    assert protected == "Announcement from [[0]]."


def test_repeated_term_gets_one_placeholder_per_occurrence():
    glossary = Glossary(keep=["Joker"], mapping={})
    protected, replacements = glossary.protect("Joker, this is Joker.", TEMPLATE)
    assert protected == "[[0]], this is [[1]]."
    assert replacements == ["Joker", "Joker"]


def test_missing_reports_placeholders_the_translator_swallowed():
    glossary = Glossary(keep=["Ryuji"], mapping={})
    _, replacements = glossary.protect("Ryuji is late.", TEMPLATE)
    assert glossary.missing("มาสายแล้ว", replacements, TEMPLATE) == [0]
    assert glossary.missing("[[0]] มาสายแล้ว", replacements, TEMPLATE) == []


def test_text_without_any_glossary_term_is_left_alone():
    glossary = Glossary(keep=["Ryuji"], mapping={})
    protected, replacements = glossary.protect("Nothing special here.", TEMPLATE)
    assert protected == "Nothing special here."
    assert replacements == []


def test_from_file_reads_both_sections(tmp_path):
    path = tmp_path / "g.json"
    path.write_text(
        json.dumps({"keep": ["Ryuji"], "map": {"Palace": "พาเลซ"}}), encoding="utf-8"
    )
    glossary = Glossary.from_file(path)
    protected, replacements = glossary.protect("Ryuji went to the Palace.", TEMPLATE)
    assert protected == "[[0]] went to the [[1]]."
    assert replacements == ["Ryuji", "พาเลซ"]


def test_from_file_of_a_missing_file_is_an_empty_glossary(tmp_path):
    glossary = Glossary.from_file(tmp_path / "nope.json")
    assert glossary.protect("Ryuji", TEMPLATE) == ("Ryuji", [])


def test_from_file_of_broken_json_is_an_empty_glossary(tmp_path):
    path = tmp_path / "g.json"
    path.write_text("{ broken", encoding="utf-8")
    assert Glossary.from_file(path).protect("Ryuji", TEMPLATE) == ("Ryuji", [])


def test_pipeline_uses_the_first_template_that_survives():
    glossary = Glossary(keep=["Ryuji"], mapping={})
    translator = FakeTranslator()
    result, applied = translate_with_glossary(
        "Ryuji is late.", translator, glossary, DEFAULT_TEMPLATES
    )
    assert applied is True
    assert "Ryuji" in result
    assert len(translator.calls) == 1


def test_pipeline_falls_through_to_the_second_template():
    first, second = DEFAULT_TEMPLATES[0], DEFAULT_TEMPLATES[1]

    def rule(text: str) -> str:
        return text.replace(first.format(i=0), "") if first.format(i=0) in text else text

    glossary = Glossary(keep=["Ryuji"], mapping={})
    translator = FakeTranslator(rule)
    result, applied = translate_with_glossary(
        "Ryuji is late.", translator, glossary, [first, second]
    )
    assert applied is True
    assert "Ryuji" in result
    assert len(translator.calls) == 2


def test_pipeline_gives_up_and_translates_raw_when_every_template_fails():
    glossary = Glossary(keep=["Ryuji"], mapping={})
    translator = FakeTranslator(lambda text: "ไม่มี placeholder เหลือเลย")
    result, applied = translate_with_glossary(
        "Ryuji is late.", translator, glossary, DEFAULT_TEMPLATES
    )
    assert applied is False
    assert result == "ไม่มี placeholder เหลือเลย"


def test_pipeline_reports_failure_when_the_translator_returns_none():
    glossary = Glossary(keep=["Ryuji"], mapping={})
    translator = FakeTranslator(lambda text: None)
    result, applied = translate_with_glossary(
        "Ryuji is late.", translator, glossary, DEFAULT_TEMPLATES
    )
    assert result is None
    assert applied is False


def test_pipeline_skips_protection_entirely_when_there_is_nothing_to_protect():
    glossary = Glossary(keep=["Ryuji"], mapping={})
    translator = FakeTranslator()
    result, applied = translate_with_glossary(
        "Nothing special.", translator, glossary, DEFAULT_TEMPLATES
    )
    assert applied is True
    assert result == "TH<Nothing special.>"
    assert translator.calls == [["Nothing special."]]
