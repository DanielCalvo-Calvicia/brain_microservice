import pytest

from domain.operations.wake_phrase import WakePhrase, find_wake_phrase, has_words, strip_wake_phrase

PHRASE = WakePhrase.parse("Oblivion 306")


def test_the_phrase_is_a_name_and_a_code() -> None:
    assert PHRASE == WakePhrase(name="oblivion", code="306")
    assert WakePhrase.parse("Robot") == WakePhrase(name="robot", code="")


def test_a_phrase_without_a_name_is_refused() -> None:
    with pytest.raises(ValueError):
        WakePhrase.parse("306")


@pytest.mark.parametrize(
    "heard",
    [
        "Oblivion 306",
        "oblivion, 306.",
        "Oblivion three oh six",
        "Oblivion three zero six",
        "Oblivion three-o-six",
        "Oblivion 3 0 6",
        "Oblivion three hundred six",
        "Oblivion three hundred and six",
        "OBLIVION THREE HUNDRED AND SIX!",
        "Oblivian 306",  # a small misspelling of the name
    ],
)
def test_every_way_of_saying_the_phrase_is_found(heard: str) -> None:
    assert find_wake_phrase(heard, PHRASE) is not None


@pytest.mark.parametrize(
    "heard",
    [
        "",
        "hello there",
        "Oblivion",  # the name alone is not the phrase
        "I fear oblivion",
        "Oblivion 305",
        "Oblivion three oh five",
        "Oblivion three hundred seven",
        "306 oblivion",  # the code comes after the name
        "Oblivion hello 306",  # and right after it
        "Oblivion 3060",
    ],
)
def test_anything_else_is_not_the_phrase(heard: str) -> None:
    assert find_wake_phrase(heard, PHRASE) is None


def test_the_phrase_may_be_anywhere_in_the_sentence() -> None:
    assert find_wake_phrase("Oblivion 306 move your left arm", PHRASE) is not None
    assert find_wake_phrase("move your left arm Oblivion 306", PHRASE) is not None
    assert find_wake_phrase("hey, Oblivion 306, move your left arm", PHRASE) is not None


def test_a_phrase_that_is_only_a_name_matches_the_name() -> None:
    assert find_wake_phrase("hey robot, wave", WakePhrase.parse("Robot")) is not None


def test_the_match_covers_exactly_the_phrase() -> None:
    text = "hey Oblivion three oh six, wave"
    match = find_wake_phrase(text, PHRASE)

    assert match is not None
    assert text[match.start : match.end] == "Oblivion three oh six"


@pytest.mark.parametrize(
    ("heard", "expected"),
    [
        ("Oblivion 306 move your left arm", "move your left arm"),
        ("Oblivion, 306. Move your left arm.", "Move your left arm."),
        ("Move your left arm, Oblivion 306", "Move your left arm,"),
        ("Hey Oblivion 306, move your left arm", "Hey, move your left arm"),
        ("Oblivion three hundred and six", ""),
        ("Oblivion 306!", ""),
        ("no phrase here", "no phrase here"),
    ],
)
def test_stripping_the_phrase_leaves_the_rest_of_the_sentence(heard: str, expected: str) -> None:
    assert strip_wake_phrase(heard, PHRASE) == expected


def test_has_words_ignores_punctuation() -> None:
    assert has_words("wave") is True
    assert has_words("  ...,  ") is False
    assert has_words("") is False
