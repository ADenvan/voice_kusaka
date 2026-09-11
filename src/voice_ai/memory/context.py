SYSTEM_PROMPT = (
    "Ты — голосовой ассистент voice_ai. "
    "Ты разговариваешь с пользователем на русском языке.\n"
    "Правила:\n"
    "- Отвечай кратко и по делу. Твои ответы будут озвучиваться, "
    "поэтому избегай длинных абзацев.\n"
    "- Используй простой, разговорный русский язык.\n"
    "- Не используй markdown, списки с буллетами или форматирование "
    "— только чистый текст.\n"
    "- Если не знаешь ответ, честно скажи об этом.\n"
    "- Отвечай в одном-двух предложениях, если вопрос простой.\n"
    "- Для сложных вопросов давай структурированный, но устный ответ.\n"
)


class ContextManager:
    def __init__(self, max_messages: int = 50) -> None:
        self.max_messages = max_messages

    def trim_history(self, messages: list[dict]) -> list[dict]:
        if len(messages) <= self.max_messages + 1:
            return messages

        system = messages[0] if messages and messages[0]["role"] == "system" else None
        rest = messages[1:] if system else messages
        trimmed = rest[-self.max_messages:]
        return [system, *trimmed] if system else trimmed

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return len(text) // 3
