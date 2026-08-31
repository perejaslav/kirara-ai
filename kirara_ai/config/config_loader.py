import os
import shutil
from functools import wraps
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from ruamel.yaml import YAML

from ..logger import get_logger
from . import DATA_PATH

CONFIG_FILE = os.path.join(DATA_PATH, "config.yaml")

T = TypeVar("T", bound=BaseModel)


class ConfigLoader:
    """
    Загрузчик конфигурации: чтение/запись YAML с сохранением комментариев.
    """

    yaml = YAML()

    @staticmethod
    def load_config(config_path: str, config_class: Type[T]) -> T:
        """
        Загрузить YAML-конфигурацию и валидировать её.

        :param config_path: путь к файлу конфигурации
        :param config_class: класс конфигурации (наследник BaseModel)
        :return: экземпляр конфигурации
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = ConfigLoader.yaml.load(f)
            return config_class(**config_data)
        except ValidationError as e:
            raise ValueError(f"Ошибка валидации конфигурации: {e}")
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить конфигурацию: {e}")

    @staticmethod
    def save_config(config_path: str, config_object: BaseModel):
        """
        Сохранить конфигурацию в YAML.

        :param config_path: путь к файлу
        :param config_object: объект конфигурации
        """
        with open(config_path, "w", encoding="utf-8") as f:
            ConfigLoader.yaml.dump(config_object.model_dump(), f)

    @staticmethod
    def save_config_with_backup(config_path: str, config_object: BaseModel):
        """
        Сохранить конфигурацию, предварительно создав .bak-копию.

        :param config_path: путь к файлу
        :param config_object: объект конфигурации
        """
        if os.path.exists(config_path):
            backup_path = f"{config_path}.bak"
            shutil.copy2(config_path, backup_path)
        ConfigLoader.save_config(config_path, config_object)


def pydantic_validation_wrapper(func):
    """Декоратор: логирует ошибки валидации Pydantic."""
    logger = get_logger("ConfigLoader")

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.error(f"Ошибка валидации Pydantic: '{e.title}':")
            for error in e.errors():
                logger.error(
                    f"Поле: {error['loc'][0]}, тип ошибки: {error['type']}, сообщение: {error['msg']}"
                )
            logger.opt(exception=True).error("Трассировка:")
            raise

    return wrapper


class ConfigJsonSchema(GenerateJsonSchema):
    def sort(
        self, value: JsonSchemaValue, parent_key: Optional[str] = None
    ) -> JsonSchemaValue:
        """Без сортировки — сохраняем исходный порядок ключей."""
        return value
