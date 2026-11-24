import shutil
import uuid
from pathlib import Path
from flask import current_app
from werkzeug.utils import secure_filename

from engine.adapter import discover_parquet_layers, validate_layer

ALLOWED = {".parquet"}


def prepare_and_validate(files):
    job_id = uuid.uuid4().hex

    workdir = Path(Path(files[0]).as_posix().replace(Path(files[0]).name,""))
    results = []
    for file in files:
        nom = Path(file).name
        nom_rule = Path(file).stem
        results.append(validate_layer(workdir,nom,nom_rule))
    return {"job_id": job_id, "layers": files, "results": results}
