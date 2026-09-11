from scripts.placeholder_probe import score_template
from waen.translate.glossary import Glossary


class KeepsPlaceholders:
    def translate_many(self, texts):
        return [f"TH {text}" for text in texts]


class EatsPlaceholders:
    def translate_many(self, texts):
        return ["nothing remains" for _ in texts]


class Flaky:
    """Preserves only the first tested sentence."""

    def __init__(self):
        self.count = 0

    def translate_many(self, texts):
        self.count += 1
        return [f"TH {texts[0]}" if self.count == 1 else "nothing remains"]


GLOSSARY = Glossary(keep=["Ryuji"], mapping={"Palace": "พาเลซ"})
SENTENCES = ("Ryuji is here.", "Enter the Palace.")


def test_a_surviving_template_scores_full_marks():
    assert score_template("[[{i}]]", GLOSSARY, KeepsPlaceholders(), SENTENCES) == (2, 2)


def test_a_swallowed_template_scores_zero():
    assert score_template("[[{i}]]", GLOSSARY, EatsPlaceholders(), SENTENCES) == (0, 2)


def test_partial_survival_is_reported_honestly():
    assert score_template("[[{i}]]", GLOSSARY, Flaky(), SENTENCES) == (1, 2)


def test_sentences_without_glossary_terms_are_not_counted():
    assert score_template("[[{i}]]", GLOSSARY, KeepsPlaceholders(), ("Nothing here.",)) == (0, 0)
