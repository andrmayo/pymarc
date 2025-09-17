import html
from typing import Optional
from unicodedata import normalize


def decompose_diacritics_html(char) -> Optional[str]:
    """Function for detecting if a unicode char has or is a diacritic,
    and returning decomposed html representation.
    This should work for standard unicode Latin, Greek, and Cyrillic diacritics."""
    unicode_val = ord(char)
    if not (
        (unicode_val >= 7936 and unicode_val <= 8190)  # covers most greek compositions
        or (
            unicode_val >= 256 and unicode_val <= 382
        )  # covers diacritics in Latin Extended-A
        or (unicode_val >= 461 and unicode_val <= 496)
        or (unicode_val >= 500 and unicode_val <= 501)
        or (unicode_val >= 504 and unicode_val <= 539)
        or (unicode_val >= 542 and unicode_val <= 543)
        or (unicode_val >= 550 and unicode_val <= 563)
        or (
            unicode_val >= 768 and unicode_val <= 901
        )  # covers combining diacritical marks
        or (unicode_val >= 938 and unicode_val <= 944)
        or (unicode_val >= 970 and unicode_val <= 974)
        or (unicode_val >= 979 and unicode_val <= 980)
        or (unicode_val >= 1024 and unicode_val <= 1025)  # covers cyrillic compositions
        or (
            unicode_val == 1027
            or unicode_val == 1031
            or unicode_val == 1081
            or unicode_val == 1107
            or unicode_val == 1111
        )
        or (unicode_val >= 1036 and unicode_val <= 1038)
        or (unicode_val >= 1104 and unicode_val <= 1105)
        or (unicode_val >= 1116 and unicode_val <= 1118)
        or (unicode_val >= 1142 and unicode_val <= 1143)
        or (unicode_val >= 1148 and unicode_val <= 1151)
        or (unicode_val >= 1154 and unicode_val <= 1161)  # cyrillic combining marks
        or (unicode_val >= 1217 and unicode_val <= 1218)
        or (unicode_val >= 1232 and unicode_val <= 1235)
        or (unicode_val >= 1238 and unicode_val <= 1239)
        or (unicode_val >= 1242 and unicode_val <= 1247)
        or (unicode_val >= 1250 and unicode_val <= 1255)
        or (unicode_val >= 1258 and unicode_val <= 1273)
    ):
        return
    # decompose character + diacritic
    norm = normalize("NFD", char)
    decomp_buffer = []
    for decomp_char in norm:
        decomp_val = ord(decomp_char)
        decomp_html = html.entities.codepoint2name.get(decomp_val)  # type: ignore
        if decomp_html:
            decomp_buffer.append("&" + decomp_html + ";")
            continue
        decomp_buffer.append("&#" + str(decomp_val) + ";")
    return "".join(decomp_buffer)


def html_escape_unicode(text) -> str:
    """Function to replace non-ASCII characters with their html representations.
    Entity names are preferred to codepoints. This handles Greek diacritics specially."""
    if not isinstance(text, str):
        return text
    buffer = []
    for char in text:
        if char.isascii():
            buffer.append(char)
            continue
        diacr = decompose_diacritics_html(char)
        if diacr:
            buffer.append(diacr)
            continue
        char_val = ord(char)
        new_char = html.entities.codepoint2name.get(char_val)  # type: ignore
        if not new_char:
            new_char = "#" + str(char_val)
            print(f"Representing char {char} with codepoint: {'&' + new_char + ';'}")
        buffer.append("&" + new_char + ";")
    return "".join(buffer)
