"""Start disposable API/proxy processes, run HTTP checks, then remove test data."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil
import subprocess
import sys
from smoke_http import main as smoke


def main():
    root = Path(__file__).resolve().parents[1]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    with TemporaryDirectory(prefix="srs-http-") as directory:
        env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(Path(directory) / "test.db"),
            "UPLOAD_DIR": str(Path(directory) / "uploads"), "MAIL_SINK_DIR": str(Path(directory) / "mail"),
            "APP_ENV": "development", "COOKIE_SECURE": "false", "SMTP_HOST": "", "LLM_PROVIDER": "mock",
            "PUBLIC_URL": "http://127.0.0.1:15173", "CORS_ORIGINS": "http://127.0.0.1:15173",
            "API_PROXY_TARGET": "http://127.0.0.1:18003"}
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root / "backend", env=env, check=True, creationflags=flags)
        with (Path(directory) / "services.log").open("w+") as log:
            processes = []
            try:
                processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18003"], cwd=root / "backend", env=env, stdout=log, stderr=log, creationflags=flags))
                processes.append(subprocess.Popen([shutil.which("node"), str(root / "frontend/node_modules/vite/bin/vite.js"), "--host", "127.0.0.1", "--port", "15173", "--strictPort"], cwd=root / "frontend", env=env, stdout=log, stderr=log, creationflags=flags))
                os.environ["SMOKE_API_URL"] = "http://127.0.0.1:15173/api"
                smoke()
            except Exception:
                log.flush(); log.seek(0); print(log.read())
                raise
            finally:
                for process in reversed(processes):
                    if sys.platform == "win32" and process.poll() is None:
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, creationflags=flags)
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait()


if __name__ == "__main__":
    main()
