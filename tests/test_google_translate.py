from waen.translate.base import Translator
from waen.translate.google import GoogleTranslateBackend


class FakeBackend:
    def __init__(self, source, target, rule=None, fail_times=0, failure_budget=None):
        self.source = source
        self.target = target
        self.rule = rule or (lambda text: "\n".join(f"TH<{line}>" for line in text.split("\n")))
        self.fail_times = fail_times
        self.failure_budget = failure_budget
        self.calls: list[str] = []

    def translate(self, text: str) -> str:
        self.calls.append(text)
        if self.failure_budget is not None and self.failure_budget[0] > 0:
            self.failure_budget[0] -= 1
            raise RuntimeError("network down")
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("network down")
        return self.rule(text)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make(rule=None, fail_times=0, **kwargs):
    created: list[FakeBackend] = []
    failure_budget = [fail_times]

    def factory(source, target):
        backend = FakeBackend(source, target, rule=rule, failure_budget=failure_budget)
        created.append(backend)
        return backend

    clock = Clock()
    slept: list[float] = []

    def sleeper(seconds: float) -> None:
        slept.append(seconds)
        clock.now += seconds

    translator = GoogleTranslateBackend(
        backend_factory=factory, clock=clock, sleeper=sleeper, **kwargs
    )
    return translator, created, slept, clock


def test_satisfies_the_protocol():
    translator, _, _, _ = make()
    assert isinstance(translator, Translator)


def test_single_text_is_translated():
    translator, _, _, _ = make()
    assert translator.translate_many(["Hello"]) == ["TH<Hello>"]


def test_repeated_text_is_served_from_cache():
    translator, created, _, _ = make()
    translator.translate_many(["Hello"])
    translator.translate_many(["Hello"])
    assert created[0].calls == ["Hello"]
    assert translator.stats()["cache_hits"] == 1


def test_several_texts_go_out_as_one_joined_request():
    translator, created, _, _ = make()
    result = translator.translate_many(["one", "two", "three"])
    assert result == ["TH<one>", "TH<two>", "TH<three>"]
    assert len(created[0].calls) == 1


def test_line_count_mismatch_falls_back_to_one_request_per_text():
    def rule(text: str) -> str:
        return "collapsed" if "\n" in text else f"TH<{text}>"

    translator, created, _, _ = make(rule=rule)
    assert translator.translate_many(["one", "two"]) == ["TH<one>", "TH<two>"]
    assert len(created[0].calls) == 3


def test_empty_and_too_short_texts_return_none_without_calling_the_backend():
    translator, created, _, _ = make()
    assert translator.translate_many(["", " ", "a"]) == [None, None, None]
    assert created == []


def test_mixed_cached_and_new_texts_keep_their_order():
    translator, _, _, _ = make()
    translator.translate_many(["one"])
    assert translator.translate_many(["one", "two"]) == ["TH<one>", "TH<two>"]


def test_a_transient_failure_is_retried():
    translator, _, slept, _ = make(fail_times=1)
    assert translator.translate_many(["Hello"]) == ["TH<Hello>"]
    assert slept


def test_giving_up_returns_none_and_counts_a_failure():
    translator, _, _, _ = make(fail_times=99, max_attempts=3)
    assert translator.translate_many(["Hello"]) == [None]
    assert translator.stats()["failures"] == 1


def test_backoff_delays_increase():
    translator, _, slept, _ = make(fail_times=99, max_attempts=3)
    translator.translate_many(["Hello"])
    assert slept == sorted(slept)
    assert len(slept) >= 2


def test_rate_limit_spaces_out_consecutive_requests():
    translator, _, slept, _ = make(max_per_second=2.0)
    translator.translate_many(["one"])
    translator.translate_many(["two"])
    assert any(delay >= 0.4 for delay in slept)


def test_changing_languages_drops_the_old_backend():
    translator, created, _, _ = make()
    translator.translate_many(["Hello"])
    translator.set_languages("en", "ja")
    translator.translate_many(["Hello"])
    assert len(created) == 2
    assert created[1].target == "ja"


def test_cache_is_bounded():
    translator, _, _, _ = make(cache_size=3)
    for index in range(10):
        translator.translate_many([f"text number {index}"])
    assert translator.cache_size_now() <= 3


def test_cache_key_includes_the_language_pair():
    translator, _, _, _ = make()
    translator.translate_many(["Hello"])
    translator.set_languages("en", "ja")
    translator.translate_many(["Hello"])
    assert translator.stats()["cache_hits"] == 0
