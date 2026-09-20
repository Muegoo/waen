import pytest

from waen.metrics import character_error_rate, levenshtein, normalize, word_accuracy


def test_normalize_collapses_whitespace_and_case():
    assert normalize("  Hello   WORLD \n") == "hello world"


def test_normalize_keeps_punctuation():
    # เครื่องหมายวรรคตอนมีความหมายกับการแปล จึงห้ามตัดทิ้งตอนวัด
    assert normalize("Wait, what?!") == "wait, what?!"


def test_levenshtein_on_strings():
    assert levenshtein("kitten", "sitting") == 3


def test_levenshtein_of_identical_is_zero():
    assert levenshtein("same", "same") == 0


def test_levenshtein_with_empty_input_is_length_of_the_other():
    assert levenshtein("", "abcd") == 4
    assert levenshtein("abcd", "") == 4


def test_levenshtein_works_on_word_lists():
    assert levenshtein(["a", "b", "c"], ["a", "x", "c"]) == 1


def test_word_accuracy_perfect_match_is_one():
    assert word_accuracy("Welcome to this village", "Welcome to this village") == 1.0


def test_word_accuracy_is_case_insensitive():
    assert word_accuracy("Welcome Home", "welcome home") == 1.0


def test_word_accuracy_one_wrong_word_in_four():
    assert word_accuracy("a b c d", "a b x d") == pytest.approx(0.75)


def test_word_accuracy_missing_word():
    assert word_accuracy("a b c d", "a b d") == pytest.approx(0.75)


def test_word_accuracy_never_goes_below_zero():
    assert word_accuracy("a b", "x y z q r s t u") == 0.0


def test_word_accuracy_of_empty_truth_and_empty_hypothesis_is_one():
    assert word_accuracy("", "") == 1.0


def test_word_accuracy_of_empty_truth_with_output_is_zero():
    assert word_accuracy("", "spurious text") == 0.0


def test_character_error_rate_perfect_is_zero():
    assert character_error_rate("hello", "hello") == 0.0


def test_character_error_rate_one_of_five():
    assert character_error_rate("hello", "hallo") == pytest.approx(0.2)


def test_character_error_rate_can_exceed_one_when_ocr_hallucinates():
    assert character_error_rate("hi", "hi there my friend") > 1.0


def test_normalize_unifies_typographic_quotes_and_dashes():
    assert normalize("couldn’t — “ok”…") == normalize("couldn't - \"ok\"...")


def test_word_accuracy_ignores_typographic_differences():
    assert word_accuracy("It’s me—the king.", "It's me-the king.") == 1.0
