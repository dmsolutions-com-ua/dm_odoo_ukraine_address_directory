"""Ukrainian -> Latin transliteration, official rules.

Source: Resolution of the Cabinet of Ministers of Ukraine No. 55 of 2010-01-27
"On the streamlining of the transliteration of the Ukrainian alphabet in Latin
script" (https://zakon.rada.gov.ua/laws/show/55-2010-%D0%BF).

Pure Python, no ORM and no HTTP: transliteration is a deterministic per-letter
function, so it is computed locally instead of being requested from the API.
Follows the `res_country_state_sync` precedent - a plain helper module that is
deliberately NOT registered in `models/__init__.py`.
"""

import logging

_logger = logging.getLogger(__name__)

# Однозначні відповідники (позиція в слові не впливає).
_SIMPLE = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "ж": "zh", "з": "z", "и": "y", "і": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    # Поза українським алфавітом, але трапляється у сирих даних. Мапимо, щоб у
    # латинський рядок ніколи не просочилася кирилиця.
    "ё": "e", "ъ": "", "ы": "y", "э": "e",
}

# Позиційні: (на початку слова, в інших позиціях).
_POSITIONAL = {
    "є": ("ye", "ie"),
    "ї": ("yi", "i"),
    "й": ("y", "i"),
    "ю": ("yu", "iu"),
    "я": ("ya", "ia"),
}

# Не відтворюються латиницею (примітка 2 постанови): м'який знак і апостроф.
# Апостроф при цьому НЕ розриває слово: Знам'янка -> Znamianka.
_APOSTROPHES = "'’ʼˈ`´"
_DROPPED = "ь" + _APOSTROPHES

# Усі кириличні символи, які модуль вважає «літерою» для визначення межі слова.
_LETTERS = set(_SIMPLE) | set(_POSITIONAL) | {"ь"}


def _is_letter(char):
    """True for a Ukrainian letter (either case) - used for word boundaries."""
    return char.lower() in _LETTERS


def _apply_case(latin, upper_source, next_char):
    """Case a Latin replacement after an uppercase Ukrainian letter.

    "Житомир" -> "Zhytomyr" (only the first char kept uppercase), but
    "ЖИТОМИР" -> "ZHYTOMYR" (the whole replacement uppercased).
    """
    if not upper_source or not latin:
        return latin
    # Наступна МАЛА українська літера означає звичайне слово з великої -> лише
    # перший символ великий. Інакше (кінець слова, верхній регістр) — усе велике.
    if next_char and _is_letter(next_char) and next_char.islower():
        return latin[0].upper() + latin[1:]
    return latin.upper()


def transliterate(text):
    """Transliterate Ukrainian text to Latin script per CMU Resolution No. 55.

    Characters outside the Ukrainian alphabet (Latin letters, digits, spaces,
    punctuation) pass through unchanged, so abbreviations keep their shape:
    "вул." -> "vul.", "обл." -> "obl.", "р-н" -> "r-n", "смт" -> "smt".

    Returns "" for empty/false input; the function is idempotent on text that is
    already Latin.
    """
    if not text:
        return ""
    text = str(text)
    out = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        lower = char.lower()
        upper_source = char != lower
        prev = text[index - 1] if index else ""
        # Початок слова: немає попереднього символу або він не літера. Апостроф
        # межею НЕ вважається (примітка 2), тож "Знам'янка" -> "Znamianka".
        at_word_start = not prev or not (_is_letter(prev) or prev in _APOSTROPHES)
        nxt = text[index + 1] if index + 1 < length else ""

        # Примітка 1: буквосполучення "зг" -> "zgh" (на відміну від "ж" -> "zh").
        # Перевіряється ДО одиночного "з".
        if lower == "з" and nxt.lower() == "г":
            out.append(_apply_case(
                "zgh", upper_source, text[index + 2] if index + 2 < length else ""))
            index += 2
            continue

        if lower in _DROPPED:
            index += 1
            continue

        if lower in _POSITIONAL:
            start, other = _POSITIONAL[lower]
            out.append(_apply_case(start if at_word_start else other,
                                   upper_source, nxt))
            index += 1
            continue

        if lower in _SIMPLE:
            out.append(_apply_case(_SIMPLE[lower], upper_source, nxt))
            index += 1
            continue

        # Не кирилиця — залишаємо як є (цифри, латиниця, розділові знаки).
        out.append(char)
        index += 1
    return "".join(out)
