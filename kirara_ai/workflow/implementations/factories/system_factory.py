from kirara_ai.workflow.core.workflow.builder import WorkflowBuilder
from kirara_ai.workflow.implementations.blocks.im.messages import GetIMMessage, SendIMMessage
from kirara_ai.workflow.implementations.blocks.memory.clear_memory import ClearMemory
from kirara_ai.workflow.implementations.blocks.system.help import GenerateHelp


class SystemWorkflowFactory:
    """Фабрика системных воркфлоу."""

    @staticmethod
    def create_help_workflow() -> WorkflowBuilder:
        """Воркфлоу справки."""
        return WorkflowBuilder("Справка").use(GenerateHelp).chain(SendIMMessage)

    @staticmethod
    def create_clear_memory_workflow() -> WorkflowBuilder:
        """Воркфлоу очистки памяти."""
        return (
            WorkflowBuilder("Очистка памяти")
            .use(GetIMMessage)
            .parallel(
                [
                    (ClearMemory, {"scope_type": "group"}),
                    (ClearMemory, {"scope_type": "member"}),
                ]
            )
            .chain(SendIMMessage)
        )
