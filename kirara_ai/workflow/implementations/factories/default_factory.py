
from kirara_ai.workflow.core.workflow.builder import WorkflowBuilder
from kirara_ai.workflow.implementations.blocks.im.messages import GetIMMessage, SendIMMessage
from kirara_ai.workflow.implementations.blocks.im.states import ToggleEditState
from kirara_ai.workflow.implementations.blocks.llm.chat import (ChatCompletion, ChatMessageConstructor,
                                                                ChatResponseConverter)
from kirara_ai.workflow.implementations.blocks.memory.chat_memory import ChatMemoryQuery, ChatMemoryStore
from kirara_ai.workflow.implementations.blocks.system.basic import TextBlock


class DefaultWorkflowFactory:
    """
    Фабрика воркфлоу по умолчанию — универсальный ассистент.
    """

    @staticmethod
    def create_default_workflow() -> WorkflowBuilder:
        """Базовый чат-воркфлоу: универсальный ассистент на русском."""
        system_prompt = """Ты — Kirara RU, дружелюбный и полезный AI-ассистент.

Отвечай на русском языке, будь точным и кратким, но достаточно подробным.
Если пользователь пишет на другом языке — отвечай на его языке.
Используй `<break>` для разделения длинных ответов на несколько сообщений в мессенджере.

# Системная информация

Текущая дата и время: {{current_date_time}}

# Память беседы

-- начало истории --
{{memory_content}}
-- конец истории --

Примечания:
- `<break>` — маркер разделения ответа на несколько сообщений.
- Отвечай по делу и дружелюбно.
""".strip()

        user_prompt = """{user_name}: {user_msg}"""

        builder = (
            WorkflowBuilder("Чат — универсальный ассистент")
            .use(GetIMMessage, name="get_message")
            .parallel(
                [
                    (ToggleEditState, {"is_editing": True}),
                    (ChatMemoryQuery, "query_memory", {"scope_type": "group"}),
                ]
            )
            .chain(TextBlock, name="system_prompt", text=system_prompt)
            .chain(TextBlock, name="user_prompt", text=user_prompt)
            .chain(
                ChatMessageConstructor,
                wire_from=[
                    "get_message",
                    "user_prompt",
                    "query_memory",
                    "get_message",
                    "system_prompt",
                ],
            )
            .chain(ChatCompletion, name="llm_chat")
            .chain(ChatResponseConverter)
            .parallel(
                [
                    SendIMMessage,
                    (
                        ChatMemoryStore,
                        {"scope_type": "group"},
                        ["get_message", "llm_chat"],
                    ),
                ]
            )
        )
        builder.description = "Универсальный ассистент — отвечает на любые вопросы, помнит контекст беседы."
        return builder
