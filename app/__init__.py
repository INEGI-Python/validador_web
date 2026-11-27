import shutil
import sys
from pathlib import Path

from flask import Flask


def create_app():
    if getattr(sys, "frozen", False):
        runtime_root = Path(sys.executable).resolve().parent
        bundled_root = Path(sys._MEIPASS)
    else:
        runtime_root = Path(__file__).resolve().parent.parent
        bundled_root = runtime_root

    runtime_instance = runtime_root / "instance"
    bundled_instance = bundled_root / "instance"
    runtime_instance.mkdir(parents=True, exist_ok=True)

    filename = "reglasTopologicas.json"
    target = runtime_instance / filename
    source = bundled_instance / filename
    if not target.exists() and source.exists():
        shutil.copy2(source, target)

    app = Flask(
        __name__,
        instance_path=str(runtime_instance),
        instance_relative_config=True,
    )
    app.config.from_mapping(
        SECRET_KEY="dev-change-me",
        MAX_CONTENT_LENGTH=14 * 1024 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(app.instance_path) / "uploads"),
        RESULTS_FOLDER=str(Path(app.instance_path) / "results"),
        RULES_FILE=str(Path(app.instance_path) / "reglasTopologicas.json"),
    )
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["RESULTS_FOLDER"]).mkdir(parents=True, exist_ok=True)

    from .routes.main import main_bp
    from .routes.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app
