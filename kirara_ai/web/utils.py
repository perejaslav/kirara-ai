import asyncio
import os
import tarfile
import tempfile
import time
from pathlib import Path

import aiohttp
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response

from kirara_ai.logger import get_logger
from kirara_ai.web.api.system.utils import download_file, get_latest_npm_version

logger = get_logger("WebUtils")


async def create_no_cache_response(file_path: Path, request: Request) -> Response:
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    stat = file_path.stat()
    mtime = stat.st_mtime_ns
    size = stat.st_size
    etag = f"{mtime}-{size}"

    if_none_match = request.headers.get("if-none-match")
    if if_none_match == etag:
        return Response(status_code=304)

    response = FileResponse(file_path)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "no-cache"
    return response


async def test_npm_registry_speed(registries: list[str]) -> str:
    """Проверка скорости нескольких npm-реестров, возвращает самый быстрый."""
    fastest_registry = registries[0]
    fastest_avg_time = float('inf')
    test_count = 3

    async def test_registry(registry: str) -> tuple[str, float]:
        total_time = 0
        success_count = 0

        for i in range(test_count):
            try:
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{registry}/kirara-ai-webui",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            elapsed = time.time() - start_time
                            total_time += elapsed
                            success_count += 1
            except Exception as e:
                logger.warning(f"Проверка реестра {registry}, попытка {i+1} не удалась: {e}")

        avg_time = total_time / success_count if success_count > 0 else float('inf')
        return registry, avg_time

    tasks = [test_registry(registry) for registry in registries]
    results = await asyncio.gather(*tasks)

    for registry, avg_time in results:
        if avg_time < fastest_avg_time:
            fastest_avg_time = avg_time
            fastest_registry = registry

    if fastest_avg_time != float('inf'):
        logger.info(f"Выбран самый быстрый реестр: {fastest_registry}, среднее время ответа: {fastest_avg_time:.2f} c")
    else:
        logger.warning(f"Все реестры недоступны, используется по умолчанию: {fastest_registry}")

    return fastest_registry


async def install_webui(install_path: Path) -> tuple[bool, str]:
    """
    Установка последней версии WebUI.

    Args:
        install_path: путь к каталогу установки

    Returns:
        (успех, сообщение)
    """
    try:
        # Международные реестры — приоритет; CN-зеркала удалены
        registries = [
            "https://registry.npmjs.org",
            "https://registry.yarnpkg.com",
        ]

        npm_registry = await test_npm_registry_speed(registries)

        temp_dir = tempfile.mkdtemp()
        logger.info(f"Запрос информации о последней версии WebUI из {npm_registry}")

        latest_webui_version, webui_download_url = await get_latest_npm_version("kirara-ai-webui", npm_registry)

        if not webui_download_url:
            return False, "Не удалось получить URL для скачивания WebUI"

        logger.info(f"Скачивание WebUI v{latest_webui_version}: {webui_download_url}")
        webui_file, webui_hash = await download_file(webui_download_url, temp_dir)

        if not webui_file:
            return False, "Не удалось скачать WebUI"

        os.makedirs(install_path, exist_ok=True)

        logger.info(f"Распаковка WebUI в {install_path}")
        with tarfile.open(webui_file, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.startswith("package/dist/"):
                    extracted_name = member.name[len("package/dist/"):]
                    if extracted_name:
                        member.name = extracted_name
                        tar.extract(member, path=str(install_path))

        return True, f"WebUI v{latest_webui_version} успешно установлена"
    except Exception as e:
        logger.error(f"Ошибка установки WebUI: {e}")
        return False, f"Ошибка установки WebUI: {str(e)}"
    finally:
        if 'temp_dir' in locals():
            import shutil
            shutil.rmtree(temp_dir)
