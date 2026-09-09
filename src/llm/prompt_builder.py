SYSTEM_PROMPT = (
    "Ты — голосовой ассистент voice_ai. "
    "Ты разговариваешь с пользователем на русском или английском языке.\n"
    "Правила:\n"
    "- Отвечай кратко и по делу. Твои ответы будут озвучиваться, "
    "поэтому избегай длинных абзацев.\n"
    "- Используй простой, разговорный язык.\n"
    "- Не используй markdown, списки с буллетами или форматирование "
    "— только чистый текст.\n"
    "- Если не знаешь ответ, честно скажи об этом.\n"
    "- Отвечай в одном-двух предложениях, если вопрос простой.\n"
    "- Для сложных вопросов давай структурированный, но устный ответ.\n"
    "- ВАЖНО: Отвечай на языке пользователя. Если пользователь спрашивает "
    "на русском — отвечай на русском. Если на английском — отвечай на английском.\n"
)


class PromptBuilder:
    def __init__(self, system_prompt: str = SYSTEM_PROMPT) -> None:
        self.system_prompt = system_prompt

    def build_messages(self, history: list[dict]) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        return messages
