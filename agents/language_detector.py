UKRAINIAN_CODEPOINTS = {
    0x0404,  # Ye
    0x0406,  # I
    0x0407,  # Yi
    0x0490,  # Ghe with upturn
    0x0454,  # ye
    0x0456,  # i
    0x0457,  # yi
    0x0491,  # ghe with upturn
}


def _has_cyrillic(text: str) -> bool:
    return any(0x0400 <= ord(char) <= 0x04FF for char in text)


def detect_language(user_query: str, llm_language: str | None = None) -> str:
    if any(ord(char) in UKRAINIAN_CODEPOINTS for char in user_query):
        return "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430"

    if _has_cyrillic(user_query):
        return "\u0420\u0443\u0441\u0441\u043a\u0438\u0439"

    return (llm_language or "English").strip() or "English"
