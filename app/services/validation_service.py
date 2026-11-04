import shutil
import uuid
from pathlib import Path
from flask import current_app
from werkzeug.utils import secure_filename

from engine.adapter import discover_parquet_layers, validate_layer

ALLOWED = {".parquet"}


def prepare_and_validate(files):
    job_id = uuid.uuid4().hex
    workdir = Path(current_app.config["UPLOAD_FOLDER"]) / job_id
    workdir.mkdir(parents=True, exist_ok=False)

    saved = []
    for upload in files:
        filename = secure_filename(upload.filename or "")
        if not filename:
            continue
        suffix = Path(filename).suffix.lower()
        # GeoParquet may arrive as a directory in local workflows, but browsers upload files.
        # This first web version therefore accepts .parquet files directly.
        if suffix not in ALLOWED:
            raise ValueError(f"Formato no admitido: {filename}. Por ahora carga archivos .parquet.")
        target = workdir / filename
        upload.save(target)
        saved.append(target)

    if not saved:
        raise ValueError("No se guardó ninguna capa válida.")

    available = discover_parquet_layers(workdir)
    results = []
    for layer_name in available:
        results.append(validate_layer(workdir, layer_name))

    return {"job_id": job_id, "layers": available, "results": results}
