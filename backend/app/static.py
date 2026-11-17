from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_static(app: FastAPI, directory: str) -> bool:
    if not directory or not (Path(directory) / "index.html").is_file():
        return False
    app.mount("/", StaticFiles(directory=directory, html=True), name="web")
    return True
