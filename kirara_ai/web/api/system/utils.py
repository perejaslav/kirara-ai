import hashlib
import os
import subprocess
import sys
from functools import lru_cache

import aiohttp
import psutil


def _get_package_version(package_name: str) -> str:
    """Попытаться получить версию установленного пакета по нескольким именам."""
    from importlib.metadata import PackageNotFoundError, version

    for name in [package_name, "kirara-ai", "kirara-ru"]:
        try:
            return version(name)
        except PackageNotFoundError:
            continue
    try:
        from pkg_resources import get_distribution  # type: ignore

        for name in [package_name, "kirara-ai", "kirara-ru"]:
            try:
                return get_distribution(name).version  # type: ignore
            except Exception:
                continue
    except Exception:
        pass
    return "0.0.0"


def get_installed_version() -> str:
    """Версия текущего установленного пакета (kirara-ru с fallback на kirara-ai)."""
    return _get_package_version("kirara-ru")


async def get_latest_pypi_version(package_name: str) -> tuple[str, str]:
    """Последняя версия пакета на PyPI и URL wheel-архива."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pypi.org/pypi/{package_name}/json") as response:
                response.raise_for_status()
                data = await response.json()
                latest_version = data["info"]["version"]
                for url_info in data["urls"]:
                    if url_info["packagetype"] == "bdist_wheel":
                        return latest_version, url_info["url"]
        return latest_version, ""
    except Exception:
        return "0.0.0", ""


async def get_latest_npm_version(package_name: str, registry: str = "https://registry.npmjs.org") -> tuple[str, str]:
    """Последняя версия npm-пакета и URL tarball."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{registry}/{package_name}") as response:
                response.raise_for_status()
                data = await response.json()
                latest_version = data["dist-tags"]["latest"]
                tarball_url = data["versions"][latest_version]["dist"]["tarball"]
        return latest_version, tarball_url
    except Exception:
        return "0.0.0", ""


async def download_file(url: str, temp_dir: str) -> tuple[str, str]:
    """Скачать файл по URL, вернуть путь и SHA256."""
    local_filename = os.path.join(temp_dir, url.split('/')[-1])
    sha256_hash = hashlib.sha256()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('Content-Length', 0))
                bytes_downloaded = 0

                with open(local_filename, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        sha256_hash.update(chunk)
                        bytes_downloaded += len(chunk)
                        if total_size > 0:
                            print(f"Скачано {bytes_downloaded / total_size:.2%}", end='\r')
                print()
        return local_filename, sha256_hash.hexdigest()
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        return "", ""


@lru_cache(maxsize=1)
def get_cpu_info() -> str:
    """Информация о CPU (кэшируется)."""
    try:
        if sys.platform == 'win32':
            result = subprocess.run(['wmic', 'cpu', 'get', 'name'], capture_output=True, text=True)
            if result.returncode == 0:
                cpu_info = result.stdout.strip().removeprefix('Name').strip()
            else:
                cpu_info = ""
        else:
            cpu_info = ""
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        cpu_info = line.split(':')[1].strip()
                        break

        return cpu_info if cpu_info else "Unknown"
    except Exception:
        return "Unknown"


def get_memory_usage() -> dict:
    """Использование памяти (системная и процесс)."""
    process = psutil.Process()
    system_memory = psutil.virtual_memory()
    process_mem = process.memory_full_info().uss
    percent = system_memory.used / system_memory.total
    return {
        "percent": percent,
        "total": system_memory.total / 1024 / 1024,  # MB
        "free": system_memory.available / 1024 / 1024,  # MB
        "used": process_mem / 1024 / 1024,  # MB
    }


def get_cpu_usage() -> float:
    """Загрузка CPU, %."""
    try:
        return psutil.cpu_percent()
    except Exception:
        return 0.0
