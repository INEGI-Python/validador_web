from pathlib import Path
from flask import Flask


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev-change-me",
        MAX_CONTENT_LENGTH=2 * 1024 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(app.instance_path) / "uploads"),
        RESULTS_FOLDER=str(Path(app.instance_path) / "results"),
        RULES_FILE=str(Path(app.instance_path) / "reglas.json"),
    )
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["RESULTS_FOLDER"]).mkdir(parents=True, exist_ok=True)

    from .routes.main import main_bp
    from .routes.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app
