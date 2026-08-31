import asyncio
import mimetypes
import os
import socket
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, g, jsonify

from kirara_ai.config.global_config import GlobalConfig
from kirara_ai.ioc.container import DependencyContainer
from kirara_ai.logger import HypercornLoggerWrapper, get_logger
from kirara_ai.web.auth.services import AuthService, FileBasedAuthService
from kirara_ai.web.utils import create_no_cache_response, install_webui

from .api.block import block_bp
from .api.dispatch import dispatch_bp
from .api.im import im_bp
from .api.llm import llm_bp
from .api.mcp import mcp_bp
from .api.media import media_bp
from .api.plugin import plugin_bp
from .api.system import system_bp
from .api.tracing import tracing_bp
from .api.workflow import workflow_bp
from .auth.routes import auth_bp

ERROR_MESSAGE = """
<h1>WebUI launch failed!</h1>
<p lang="en">Web UI not found. Please download from <a href='https://github.com/perejaslav/kirara-webui/releases' target='_blank'>here</a> and extract to the <span>TARGET_DIR</span> folder, make sure the <span>TARGET_DIR/index.html</span> file exists.</p>
<h1>Запуск WebUI не удался!</h1>
<p lang="ru">Веб-интерфейс не найден. Скачайте его <a href='https://github.com/perejaslav/kirara-webui/releases' target='_blank'>отсюда</a> и распакуйте в папку <span>TARGET_DIR</span> — должен появиться файл <span>TARGET_DIR/index.html</span>.</p>

<style>
    body {
        font-family: Arial, sans-serif;
        background-color: #f0f0f0;
        color: #333;
        padding: 20px;
    }
    h1 {
        color: #333;
        font-size: 24px;
        margin-bottom: 10px;
    }
    p {
        font-size: 16px;
        margin-bottom: 10px;
    }
    a {
        color: #007bff;
        text-decoration: none;
    }
</style>
"""

cwd = os.getcwd()
STATIC_FOLDER = f"{cwd}/web"

logger = get_logger("WebServer")

custom_static_assets: dict[str, str] = {}


def create_web_api_app(container: DependencyContainer) -> Quart:
    """Создать Quart-приложение для /backend-api."""
    app = Quart(__name__, static_folder=STATIC_FOLDER)
    app.json.sort_keys = False  # type: ignore

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(im_bp, url_prefix="/api/im")
    app.register_blueprint(llm_bp, url_prefix="/api/llm")
    app.register_blueprint(dispatch_bp, url_prefix="/api/dispatch")
    app.register_blueprint(block_bp, url_prefix="/api/block")
    app.register_blueprint(workflow_bp, url_prefix="/api/workflow")
    app.register_blueprint(plugin_bp, url_prefix="/api/plugin")
    app.register_blueprint(system_bp, url_prefix="/api/system")
    app.register_blueprint(media_bp, url_prefix="/api/media")
    app.register_blueprint(tracing_bp, url_prefix="/api/tracing")
    app.register_blueprint(mcp_bp, url_prefix="/api/mcp")

    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.opt(exception=error).error("Ошибка при обработке запроса")
        response = jsonify({"error": str(error)})
        response.status_code = 500
        return response

    @app.before_request
    async def inject_container():  # type: ignore
        g.container = container

    @app.before_websocket
    async def inject_container_ws():  # type: ignore
        g.container = container

    app.container = container  # type: ignore

    return app


def create_app(container: DependencyContainer) -> FastAPI:
    """Создать основное FastAPI-приложение (SPA + статика)."""
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    mimetypes.add_type("text/html", ".html")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("image/svg+xml", ".svg")
    mimetypes.add_type("image/png", ".png")
    mimetypes.add_type("image/jpeg", ".jpg")
    mimetypes.add_type("image/gif", ".gif")
    mimetypes.add_type("image/webp", ".webp")

    async def serve_custom_static(path: str, request: Request):
        if path not in custom_static_assets:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = Path(custom_static_assets[path])
        try:
            return await create_no_cache_response(file_path, request)
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка при отдаче кастомного статического файла: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/")
    async def index(request: Request):
        try:
            index_path = Path(STATIC_FOLDER) / "index.html"
            if not index_path.exists():
                return HTMLResponse(content=ERROR_MESSAGE.replace("TARGET_DIR", STATIC_FOLDER))

            return await create_no_cache_response(index_path, request)
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка при отдаче index: {e}")
            return HTMLResponse(content=ERROR_MESSAGE.replace("TARGET_DIR", STATIC_FOLDER))

    @app.middleware("http")
    async def spa_middleware(request: Request, call_next):
        path = request.url.path
        if path in custom_static_assets:
            return await serve_custom_static(path, request)

        skip_paths = [route.path for route in app.routes]  # type: ignore

        if any(path == skip_path for skip_path in skip_paths):
            return await call_next(request)

        skip_paths.remove("/")

        if any(path.startswith(skip_path) for skip_path in skip_paths):
            return await call_next(request)

        file_path = Path(STATIC_FOLDER) / path.lstrip('/')
        if not file_path.resolve().is_relative_to(Path(STATIC_FOLDER).resolve()):
            raise HTTPException(status_code=404, detail="Access denied")

        if file_path.is_file():
            try:
                return await create_no_cache_response(file_path, request)
            except HTTPException as e:
                raise e
            except Exception as e:
                logger.error(f"Ошибка при отдаче статического файла: {e}")
                return FileResponse(file_path)

        fallback_path = Path(STATIC_FOLDER) / "index.html"
        if fallback_path.is_file():
            try:
                return await create_no_cache_response(fallback_path, request)
            except HTTPException as e:
                raise e
            except Exception as e:
                logger.error(f"Ошибка при отдаче index.html: {e}")
                return FileResponse(fallback_path)
        else:
            return PlainTextResponse(status_code=404, content="route not found")

    return app


class WebServer:
    app: FastAPI
    web_api_app: Quart
    listen_host: str
    listen_port: int
    container: DependencyContainer

    def __init__(self, container: DependencyContainer):
        self.app = create_app(container)
        self.web_api_app = create_web_api_app(container)
        self.server_task = None
        self.shutdown_event = asyncio.Event()
        self.container = container
        container.register(
            AuthService,
            FileBasedAuthService(
                password_file=Path(container.resolve(GlobalConfig).web.password_file),
                secret_key=container.resolve(GlobalConfig).web.secret_key,
            ),
        )
        self.config = container.resolve(GlobalConfig)

        from hypercorn.logging import Logger

        self.hypercorn_config = Config()
        self.hypercorn_config._log = Logger(self.hypercorn_config)

        class FilteredLoggerWrapper(HypercornLoggerWrapper):
            def info(self, message, *args, **kwargs):
                ignored_paths = [
                    '/backend-api/api/system/status',
                    '/favicon.ico',
                ]
                for path in ignored_paths:
                    if path in str(args):
                        return
                super().info(message, *args, **kwargs)

        self.hypercorn_config._log.access_logger = FilteredLoggerWrapper(logger)  # type: ignore
        self.hypercorn_config._log.error_logger = HypercornLoggerWrapper(logger)  # type: ignore

        self.mount_app("/backend-api", self.web_api_app)

    def mount_app(self, prefix: str, app):
        """Примонтировать подприложение по префиксу."""
        self.app.mount(prefix, app)

    def _check_port_available(self, host: str, port: int) -> bool:
        """Проверить, свободен ли порт."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return True
            except socket.error:
                return False

    async def start(self):
        """Запустить веб-сервер."""
        if self.container.has("cli_args"):
            cli_args = self.container.resolve("cli_args")
            self.listen_host = cli_args.host or self.config.web.host
            self.listen_port = cli_args.port or self.config.web.port
        else:
            self.listen_host = self.config.web.host
            self.listen_port = self.config.web.port

        self.hypercorn_config.bind = [f"{self.listen_host}:{self.listen_port}"]

        if not self._check_port_available(self.listen_host, self.listen_port):
            error_msg = f"Порт {self.listen_port} занят — смените порт или завершите процесс, который его использует."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.server_task = asyncio.create_task(serve(self.app, self.hypercorn_config, shutdown_trigger=self.shutdown_event.wait))  # type: ignore
        logger.info(f"Веб-сервер слушает: http://{self.listen_host}:{self.listen_port}/")

        self._check_and_install_webui()

    async def stop(self):
        """Остановить веб-сервер."""
        self.shutdown_event.set()

        if self.server_task:
            try:
                await asyncio.wait_for(self.server_task, timeout=3.0)
            except asyncio.TimeoutError:
                logger.warning("Остановка сервера превысила таймаут 3 c.")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Ошибка при остановке сервера: {e}")

    def add_static_assets(self, url_path: str, local_path: str):
        """Добавить кастомный статический ресурс."""
        if not os.path.exists(local_path):
            logger.warning(f"Путь к статическому ресурсу не существует: {local_path}")
            return

        custom_static_assets[url_path] = local_path

    def _check_and_install_webui(self):
        """Проверить наличие WebUI и при необходимости запустить установку."""
        index_path = Path(STATIC_FOLDER) / "index.html"
        if not index_path.exists():
            logger.info("WebUI не найден — будет запущена автоматическая установка после старта сервера...")
            self._webui_install_task = asyncio.create_task(self._install_webui())

    async def _install_webui(self):
        """Фоновая установка WebUI."""
        try:
            logger.info("Установка WebUI...")
            success, message = await install_webui(Path(STATIC_FOLDER))

            if success:
                logger.info(message)
                logger.info(f"WebUI установлена в {STATIC_FOLDER} — обновите страницу браузера")
            else:
                logger.error(message)
                logger.error("Автоматическая установка WebUI не удалась — скачайте вручную")
        except Exception as e:
            logger.error(f"Ошибка при установке WebUI: {e}")
