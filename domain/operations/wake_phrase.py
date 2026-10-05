"""Finding the wake phrase ("Oblivion 306") in what a speech-to-text engine heard.

A small, fast engine does not always write the phrase the same way, so the match is forgiving where speech
engines differ and strict where it matters: the *name* may be misspelled a little ("Oblivian"), and the *code*
may be said in digits or in words ("306", "three oh six", "three zero six", "three hundred and six"), but the
name must be followed right away by the code, so a sentence that merely talks about oblivion never wakes the robot.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

_TOKEN = re.compile(r"[A-Za-z]+|\d+")
_MAX_CODE_TOKENS = 8

_DIGIT_WORDS = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}
_SMALL_NUMBERS = {
    **{word: int(digit) for word, digit in _DIGIT_WORDS.items() if word not in {"oh", "o"}},
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


@dataclass(frozen=True, slots=True)
class WakePhrase:
    """The phrase to listen for: a name followed by a code (``"Oblivion 306"`` -> name ``oblivion``, code ``306``)."""

    name: str
    code: str

    @classmethod
    def parse(cls, phrase: str) -> "WakePhrase":
        words = re.findall(r"[A-Za-z]+", phrase)
        digits = "".join(re.findall(r"\d+", phrase))
        if not words:
            raise ValueError("the wake phrase needs a name made of letters, such as 'Oblivion 306'")
        return cls(name=words[0].lower(), code=digits)


@dataclass(frozen=True, slots=True)
class WakeMatch:
    """Where the phrase is in the text: ``text[start:end]``."""

    start: int
    end: int


@dataclass(frozen=True, slots=True)
class _Token:
    text: str
    start: int
    end: int


def find_wake_phrase(text: str, phrase: WakePhrase, name_similarity: float = 0.75) -> WakeMatch | None:
    """The first place the phrase is said in ``text``, or None."""
    tokens = [_Token(match.group().lower(), match.start(), match.end()) for match in _TOKEN.finditer(text)]
    for index, token in enumerate(tokens):
        if not _is_name(token.text, phrase.name, name_similarity):
            continue
        if not phrase.code:
            return WakeMatch(token.start, token.end)
        last = _code_end(tokens, index + 1, phrase.code)
        if last is not None:
            return WakeMatch(token.start, tokens[last].end)
    return None


def strip_wake_phrase(text: str, phrase: WakePhrase, name_similarity: float = 0.75) -> str:
    """``text`` without the phrase and the punctuation it leaves behind ("Hey Oblivion 306, go" -> "Hey, go")."""
    match = find_wake_phrase(text, phrase, name_similarity)
    if match is None:
        return text.strip()
    rest = f"{text[: match.start]} {text[match.end :]}"
    rest = re.sub(r"\s+([,.;:!?])", r"\1", rest)  # "Hey , go" -> "Hey, go"
    rest = re.sub(r"\s{2,}", " ", rest).strip()
    return rest.lstrip(" ,.;:!?-").strip()


# What speech engines write for background noise and silence: not something anybody said to the robot
_NOISE_PHRASES = {
    "you",
    "bye",
    "bye bye",
    "thanks",
    "thank you",
    "thank you so much",
    "thanks for watching",
    "thank you for watching",
    "thank you for watching and see you next time",
}


def is_noise_transcript(text: str) -> bool:
    """Whether ``text`` is only what an engine makes up from noise ("Thanks for watching!", "you"): nobody said it."""
    words = " ".join(match.group().lower() for match in _TOKEN.finditer(text))
    return words in _NOISE_PHRASES


def has_words(text: str) -> bool:
    """Whether there is anything to say in ``text`` besides punctuation."""
    return _TOKEN.search(text) is not None


def _is_name(word: str, name: str, similarity: float) -> bool:
    return word == name or SequenceMatcher(None, word, name).ratio() >= similarity


def _code_end(tokens: list[_Token], first: int, code: str) -> int | None:
    """The index of the last token of the code that starts at ``first``, or None when the code is not said there."""
    for last in range(first, min(len(tokens), first + _MAX_CODE_TOKENS)):
        window = [token.text for token in tokens[first : last + 1]]
        if not _could_be_number(window):
            return None
        if _digit_string(window) == code or _number(window) == int(code):
            return last
    return None


def _digit_string(words: list[str]) -> str | None:
    """"three oh six" -> "306", "3 0 6" -> "306"; None when a word is not a single digit."""
    digits = [word if word.isdigit() else _DIGIT_WORDS.get(word) for word in words]
    return None if None in digits else "".join(digits)  # type: ignore[arg-type]


def _could_be_number(words: list[str]) -> bool:
    return all(word.isdigit() or word in _DIGIT_WORDS or word in _SMALL_NUMBERS or word in {"hundred", "and"} for word in words)


def _number(words: list[str]) -> int | None:
    """The value of "three hundred and six" style words (up to 999), or None when they are not such a number."""
    value = 0
    seen = False
    for word in words:
        if word == "and":
            continue
        if word == "hundred":
            value = max(value, 1) * 100 if value < 100 else value
            seen = True
        elif word in _SMALL_NUMBERS:
            value += _SMALL_NUMBERS[word]
            seen = True
        else:
            return None
    return value if seen else None
