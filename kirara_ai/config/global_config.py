from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kirara_ai.llm.model_types import LLMAbility, ModelType


class IMConfig(BaseModel):
    """Конфигурация мессенджера"""

    name: str = Field(default="", description="Имя экземпляра мессенджера")
    enable: bool = Field(default=True, description="Включён ли мессенджер")
    adapter: str = Field(default="dummy", description="Тип адаптера мессенджера")
    config: Dict[str, Any] = Field(default={}, description="Конфигурация мессенджера")


class ModelConfig(BaseModel):
    """Конфигурация модели"""

    id: str = Field(description="Идентификатор модели")
    type: str = Field(default=ModelType.LLM.value, description="Тип модели: llm / embedding / image_generation и т.д.")
    ability: int = Field(description="Возможности модели — значение из перечисления Ability соответствующего типа")

    model_config = ConfigDict(extra="allow")


class LLMBackendConfig(BaseModel):
    """Конфигурация бэкенда LLM"""

    name: str = Field(description="Имя бэкенда")
    adapter: str = Field(description="Тип адаптера LLM")
    config: Dict[str, Any] = Field(default={}, description="Конфигурация бэкенда")
    enable: bool = Field(default=True, description="Включён ли бэкенд")
    models: List[ModelConfig] = Field(
        default=[], description="Список поддерживаемых моделей"
    )

    @model_validator(mode='before')
    @classmethod
    def migrate_models_format(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Автоматическая миграция формата конфигурации моделей.
        Преобразует список строковых ID старого формата в объекты ModelConfig.
        """
        if "models" in data and isinstance(data["models"], list):
            new_models = []

            for model in data["models"]:
                if isinstance(model, str):
                    new_models.append(ModelConfig(id=model, type=ModelType.LLM.value, ability=LLMAbility.TextChat.value))
                else:
                    new_models.append(model)

            data["models"] = new_models

        return data


class LLMConfig(BaseModel):
    """Конфигурация LLM"""

    api_backends: List[LLMBackendConfig] = Field(
        default=[], description="Список бэкендов LLM API"
    )


class MCPServerConfig(BaseModel):
    """Конфигурация MCP-сервера"""

    id: str = Field(description="Идентификатор сервера")
    description: str = Field(default="", description="Описание сервера")
    url: Optional[str] = Field(default="", description="URL сервера")
    headers: Dict[str, str] = Field(default_factory=dict, description="Заголовки запроса")
    command: Optional[str] = Field(default="", description="Команда запуска сервера")
    args: List[str] = Field(default_factory=list, description="Аргументы запуска")
    env: Dict[str, str] = Field(default_factory=dict, description="Переменные окружения")
    connection_type: str = Field(default="stdio", description="Тип подключения: stdio / sse")
    enable: bool = Field(default=True, description="Включён ли сервер")


class MCPConfig(BaseModel):
    """Конфигурация MCP"""

    servers: List[MCPServerConfig] = Field(default=[], description="Список MCP-серверов")


class DefaultConfig(BaseModel):
    """Конфигурация по умолчанию"""

    llm_model: str = Field(
        default="gpt-4o-mini", description="Имя модели LLM по умолчанию"
    )


class MemoryPersistenceConfig(BaseModel):
    """Конфигурация хранения памяти"""

    type: str = Field(default="file", description="Тип хранения: file / redis")
    file: Dict[str, Any] = Field(
        default={"storage_dir": "./data/memory"}, description="Конфигурация файлового хранения"
    )
    redis: Dict[str, Any] = Field(
        default={"host": "localhost", "port": 6379, "db": 0},
        description="Конфигурация Redis",
    )


class MemoryConfig(BaseModel):
    """Конфигурация памяти"""

    persistence: MemoryPersistenceConfig = MemoryPersistenceConfig()
    max_entries: int = Field(default=100, description="Максимум записей памяти на область")
    default_scope: str = Field(default="member", description="Тип области по умолчанию")


class WebConfig(BaseModel):
    """Конфигурация веб-сервера"""

    host: str = Field(default="127.0.0.1", description="IP-адрес веб-сервера")
    port: int = Field(default=8080, description="Порт веб-сервера")
    secret_key: str = Field(default="", description="Секретный ключ веб-сервера (JWT и т.д.)")
    password_file: str = Field(
        default="./data/web/password.hash", description="Путь к файлу хеша пароля"
    )


class PluginConfig(BaseModel):
    """Конфигурация плагинов"""

    enable: List[str] = Field(default=[], description="Список включённых внешних плагинов")
    market_base_url: str = Field(
        default="https://kirara-plugin.app.lss233.com/api/v1",
        description="Базовый URL маркета плагинов",
    )


class UpdateConfig(BaseModel):
    """Конфигурация источников обновлений"""

    pypi_registry: str = Field(default="https://pypi.org/simple", description="URL сервера PyPI")
    npm_registry: str = Field(default="https://registry.npmjs.org", description="URL сервера npm")


class FrpcConfig(BaseModel):
    """Конфигурация FRPC (проброс портов)"""

    enable: bool = Field(default=False, description="Включён ли FRPC")
    server_addr: str = Field(default="", description="Адрес сервера FRPC")
    server_port: int = Field(default=7000, description="Порт сервера FRPC")
    token: str = Field(default="", description="Токен подключения FRPC")
    remote_port: int = Field(default=0, description="Удалённый порт, 0 — случайный")


class SystemConfig(BaseModel):
    """Системная конфигурация"""

    timezone: str = Field(default="Europe/Moscow", description="Часовой пояс")


class TracingConfig(BaseModel):
    """Конфигурация трассировки"""

    llm_tracing_content: bool = Field(default=False, description="Записывать ли содержимое запросов к LLM")


class MediaConfig(BaseModel):
    """Конфигурация медиа"""

    cleanup_duration: int = Field(default=30, description="Интервал очистки медиафайлов, дней")
    auto_remove_unreferenced: bool = Field(default=True, description="Удалять ли неиспользуемые медиафайлы автоматически")
    last_cleanup_time: int = Field(default=0, description="Время последней очистки (timestamp)")


class GlobalConfig(BaseModel):
    """Глобальная конфигурация Kirara RU"""

    ims: List[IMConfig] = Field(default=[], description="Список мессенджеров")
    llms: LLMConfig = LLMConfig()
    mcp: MCPConfig = MCPConfig()
    defaults: DefaultConfig = DefaultConfig()
    memory: MemoryConfig = MemoryConfig()
    web: WebConfig = WebConfig()
    plugins: PluginConfig = PluginConfig()
    update: UpdateConfig = UpdateConfig()
    frpc: FrpcConfig = FrpcConfig()
    system: SystemConfig = SystemConfig()
    tracing: TracingConfig = TracingConfig()
    media: MediaConfig = MediaConfig()

    model_config = ConfigDict(extra="allow")
