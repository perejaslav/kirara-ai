<p align="center">
  <h1 align="center">Kirara RU</h1>
  <p align="center">
    Русскоязычный форк <a href="https://github.com/lss233/kirara-ai">Kirara AI</a> — фреймворк для AI-агентов с поддержкой Telegram, OpenAI-совместимых API и WebUI
    <br/>
    <em>Модифицированный форк оригинального проекта <a href="https://github.com/lss233/kirara-ai">lss233/kirara-ai</a> (AGPL-3.0)</em>
  </p>
</p>

<p align="center">
  <a href="https://github.com/perejaslav/kirara-ai"><img src="https://img.shields.io/github/stars/perejaslav/kirara-ai?color=F8B195&logo=github&style=for-the-badge" alt="Звёзды"></a>
  <a href="https://github.com/perejaslav/kirara-ai/blob/ru-main/LICENSE"><img src="https://img.shields.io/github/license/perejaslav/kirara-ai?&color=C06C84&style=for-the-badge" alt="Лицензия AGPL-3.0"></a>
  <a href="https://github.com/perejaslav/kirara-webui"><img src="https://img.shields.io/badge/WebUI-perejaslav%2Fkirara--webui-007AFF?style=for-the-badge&logo=vue.js" alt="WebUI"></a>
</p>

---

## Что это

**Kirara RU** — самостоятельный русскоязычный форк [Kirara AI](https://github.com/lss233/kirara-ai) для пользователей России и СНГ. Сохранены архитектура (LLM, IM, plugins, workflow, MCP) и возможность получать обновления из `lss233/kirara-ai` (upstream).

Отличия от оригинала:
- Полностью русский интерфейс, документация и настройки по умолчанию
- Telegram — основной рекомендуемый мессенджер
- Любые OpenAI-совместимые API из коробки (LM Studio, Ollama, llama.cpp, vLLM)
- Зависимости — GitHub / PyPI / npmjs (без обязательных CN-зеркал)
- 5 готовых пресетов на русском

> **Upstream:** `lss233/kirara-ai` подключён как `upstream` — обновления подтягиваются через `git fetch upstream && git merge upstream/master` в ветку `ru-main` (ежемесячно). Лицензия AGPL-3.0 и исходные copyright — сохранены.

---

## Быстрый старт

### Установка → Запуск → WebUI → Telegram → Модель → Первый диалог

#### 1. Установка

**Windows 11 / Linux / WSL (Ubuntu):**

```bash
git clone https://github.com/perejaslav/kirara-ai.git
cd kirara-ai
git checkout ru-main
pip install -e .
```

Требования: Python 3.10+, pip.

**Docker:**

```bash
docker build -t kirara-ru .
docker run -p 8080:8080 -v ./data:/app/data kirara-ru
# или
docker compose up -d
```

#### 2. Запуск

```bash
kirara_ai
# или
python -m kirara_ai
```

Откройте веб-панель: **http://127.0.0.1:8080** — при первом запуске задайте пароль.

#### 3. Подключение Telegram (рекомендуется)

1. Создайте бота у [@BotFather](https://t.me/BotFather) → `/newbot` → скопируйте токен.
2. В WebUI: **Мессенджеры → Добавить → Telegram** → вставьте токен → Сохранить и запустить.
3. Или вручную в `data/config.yaml`:

```yaml
ims:
  - name: "telegram-основной"
    enable: true
    adapter: "telegram"
    config:
      token: "123456:ABC..."
```

#### 4. Подключение модели

В WebUI: **Модели → Добавить бэкенд**.

| Провайдер | Adapter | Base URL | Примечание |
|-----------|---------|----------|------------|
| OpenAI | `openai` | `https://api.openai.com/v1` | нужен API-ключ |
| DeepSeek | `deepseek` | `https://api.deepseek.com/v1` | — |
| LM Studio | `openai` | `http://localhost:1234/v1` | локально, ключ любой |
| Ollama | `ollama` | `http://localhost:11434` | или `http://localhost:11434/v1` |
| llama.cpp | `openai` | `http://localhost:8080/v1` | — |
| vLLM | `openai` | `http://localhost:8000/v1` | — |

Для локальных моделей ключ может быть любым (например, `lm-studio`).

Пример `data/config.yaml`:

```yaml
llms:
  api_backends:
    - name: "локальная-модель"
      adapter: "openai"
      enable: true
      config:
        api_key: "lm-studio"
        api_base: "http://localhost:1234/v1"
      models:
        - "local-model"

defaults:
  llm_model: local-model
```

#### 5. Первый диалог

Напишите боту в Telegram любое сообщение — он ответит через настроенный воркфлоу. В WebUI можно проверить логи в **Консоль** и трассировку в **Журнал**.

---

## Подробные инструкции

### Windows

См. раздел «Установка» выше. Если используется WSL (Ubuntu), следуйте инструкции для Linux.

### Linux / WSL (Ubuntu)

```bash
sudo apt update && sudo apt install python3.10 python3-pip git -y
git clone https://github.com/perejaslav/kirara-ai.git
cd kirara-ai && git checkout ru-main
pip install -e .
kirara_ai
```

### Docker

```bash
docker build -t kirara-ru .
docker run -d --name kirara-ru -p 8080:8080 -v ./data:/app/data kirara-ru
# логи
docker logs -f kirara-ru
```

### Обновление

**Из исходников:**

```bash
cd kirara-ai
git fetch upstream
git merge upstream/master  # или git pull --rebase upstream master
pip install -e . --upgrade
```

**Через WebUI:** Система → Обновление → Проверить.

### Подключение OpenAI-совместимых API

В WebUI (**Модели → Добавить бэкенд**): укажите `Base URL`, `API Key` и `Model ID`. Кнопка «Проверить подключение» — опционально.

Примеры:

- **LM Studio:** запустите Local Server → скопируйте Base URL (`http://localhost:1234/v1`) → добавьте в Kirara RU.
- **Ollama:** `ollama serve` → `ollama pull llama3` → Base URL `http://localhost:11434/v1`.
- **llama.cpp:** `./llama-server -m model.gguf --port 8080` → Base URL `http://localhost:8080/v1`.

---

## Пресеты

В комплекте 5 пресетов (воркфлоу) на русском:

| Пресет | Описание |
|--------|----------|
| Универсальный ассистент | Дружелюбный помощник на любые темы |
| Помощник компании | Корпоративный стиль, от имени компании |
| Техническая поддержка | Помогает решать техпроблемы пошагово |
| Консультант | Сравнивает варианты, даёт рекомендации |
| Персонаж | Ролевой персонаж с характером |

Также сохранены: мультимодальный чат, глубокое размышление, запись памяти, разделение сообщений.

Пресеты лежат в `data/workflows/chat/*.yaml` — можно редактировать в WebUI (Воркфлоу).

---

## Возможности

- Отправка изображений, голосовые ответы (Azure / VITS)
- Ключевые слова, условия, команды администратора
- Плагины и MCP-серверы
- Пользовательские воркфлоу и правила вызова
- Web-панель управления
- Поддержка Telegram, QQ, WeCom, Discord (в доработке), OneBot (плагин), HTTP API

### Чат-платформы

| Платформа | Группа | Личка | Правила | Админ-команды |
|-----------|--------|-------|---------|---------------|
| Telegram | ✓ | ✓ | ✓ | ✓ |
| QQ Bot | ✓ | ✓ | ✓ | ✓ |
| OneBot | плагин | плагин | плагин | плагин |
| WeCom | ✓ | ✓ | ✓ | — |
| Discord | в доработке | — | — | — |

---

## Разработка

```bash
git clone https://github.com/perejaslav/kirara-ai.git
cd kirara-ai && git checkout ru-main
pip install -e ".[dev]"  # если есть extras
pre-commit install
```

Ветки: `ru-main` — русская локализация, `master` — синхронизация с upstream.

---

## Связанные проекты

- [Kirara RU WebUI](https://github.com/perejaslav/kirara-webui) — форк WebUI (Vue + Naive UI)
- [Upstream: lss233/kirara-ai](https://github.com/lss233/kirara-ai) — оригинальный проект
- [Kirara Registry](https://github.com/DarkSkyTeam/kirara-registry) — маркет плагинов

---

## Лицензия

AGPL-3.0 — см. [LICENSE](./LICENSE). Исходные copyright сохранены. Проект является модифицированным форком Kirara AI.
