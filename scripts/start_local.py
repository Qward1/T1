"""
Запуск локальной среды: backend (FastAPI) + frontend (Vite).

Использование:
    py -3 scripts/start_local.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.Popen[str]:
    """Подготовить запуск процесса с наследованием stdout/stderr."""
    return subprocess.Popen(cmd, cwd=cwd, stdout=sys.stdout, stderr=sys.stderr)


def _npm_command() -> str:
    """Найти исполняемый файл npm (npm.cmd на Windows)."""
    npm_path = shutil.which("npm")
    if npm_path:
        return npm_path
    # Попробуем npm.cmd напрямую
    npm_cmd = shutil.which("npm.cmd")
    if npm_cmd:
        return npm_cmd
    raise RuntimeError(
        "Команда 'npm' не найдена. Убедитесь, что Node.js и npm установлены и добавлены в PATH."
    )


def _npm_args(*args: str) -> list[str]:
    """Подготовить команду запуска npm с учётом платформы."""
    npm = _npm_command()
    if sys.platform.startswith("win"):
        return ["cmd", "/c", npm, *args]
    return [npm, *args]


def ensure_frontend_dependencies() -> None:
    """Проверить, что у фронтенда установлены зависимости."""
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        return
    print(">>> Устанавливаем зависимости фронтенда (npm install)")
    subprocess.check_call(_npm_args("install"), cwd=FRONTEND_DIR)


def build_index() -> None:
    """Запустить пересборку FAQ-индекса перед стартом."""
    print(">>> Обновляем индекс FAQ (python -m backend.app.build_index)")
    subprocess.check_call([sys.executable, "-m", "backend.app.build_index"], cwd=ROOT)


def start_backend() -> subprocess.Popen[str]:
    """Стартовать FastAPI backend."""
    print(">>> Запускаем backend на http://localhost:8000")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.api:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    proc = _run(cmd, cwd=ROOT)
    time.sleep(1.5)
    if proc.poll() is not None:
        raise RuntimeError(
            "Не удалось запустить backend. Проверьте, не занят ли порт 8000 и нет ли ошибок в логах."
        )
    return proc


def start_frontend() -> subprocess.Popen[str]:
    """Стартовать Vite frontend."""
    print(">>> Запускаем frontend (Vite) на http://localhost:5173")
    env = os.environ.copy()
    env.setdefault("VITE_API_BASE_URL", "http://localhost:8000")
    cmd = _npm_args("run", "dev")
    return subprocess.Popen(cmd, cwd=FRONTEND_DIR, env=env)


def main() -> None:
    ensure_frontend_dependencies()
    build_index()

    backend_proc: subprocess.Popen[str] | None = None
    frontend_proc: subprocess.Popen[str] | None = None
    try:
        backend_proc = start_backend()
        # Даём бэкенду инициализироваться, чтобы фронтенд сразу увидел API.
        time.sleep(2)
        frontend_proc = start_frontend()

        print(">>> Оба сервиса запущены. Нажмите Ctrl+C для остановки.")
        # Ожидаем завершение любого из процессов.
        while True:
            backend_code = backend_proc.poll() if backend_proc else None
            frontend_code = frontend_proc.poll() if frontend_proc else None
            if backend_code is not None:
                print(f"Backend завершился с кодом {backend_code}. Останавливаем фронтенд.")
                break
            if frontend_code is not None:
                print(f"Frontend завершился с кодом {frontend_code}. Останавливаем backend.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n>>> Получен сигнал остановки. Завершаем процессы...")
    except RuntimeError as exc:
        print(f">>> Ошибка запуска: {exc}")
    finally:
        for proc in (frontend_proc, backend_proc):
            if proc and proc.poll() is None:
                proc.terminate()
        for proc in (frontend_proc, backend_proc):
            if proc:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    main()
