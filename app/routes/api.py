import mimetypes
import tempfile
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.utils import secure_filename
from app.services.geospatial import (
    SHAPEFILE_COMPONENTS,
    convert_to_geoparquet,
    reproject_layer,
)
from app.services.validation_service import prepare_and_validate

api_bp = Blueprint("api", __name__)


def _save_source_files(uploads, directory, allowed_formats):
    saved = []
    seen_names = set()
    for upload in uploads:
        filename = secure_filename(upload.filename or "")
        if not filename:
            continue

        suffix = Path(filename).suffix.lower()
        is_shapefile_component = (
            ".shp" in allowed_formats and suffix in SHAPEFILE_COMPONENTS
        )
        if suffix not in allowed_formats and not is_shapefile_component:
            formats = ", ".join(sorted(allowed_formats))
            raise ValueError(f"Formato no admitido: {filename}. Formatos permitidos: {formats}.")
        if filename.casefold() in seen_names:
            raise ValueError(f"Se recibió más de un archivo llamado {filename}.")
        seen_names.add(filename.casefold())

        target = directory / filename
        upload.save(target)
        saved.append(target)

    if not saved:
        raise ValueError("Selecciona una capa para continuar.")

    sources = [path for path in saved if path.suffix.lower() in allowed_formats]
    if len(sources) != 1:
        raise ValueError("Selecciona exactamente una capa de origen.")

    source = sources[0]
    if source.suffix.lower() == ".shp":
        matching_files = [
            path for path in saved if path.stem.casefold() == source.stem.casefold()
        ]
        if len(matching_files) != len(saved):
            raise ValueError("Los componentes del Shapefile deben compartir el mismo nombre.")
        components = {path.suffix.lower() for path in matching_files}
        missing = {".shx", ".dbf"} - components
        if missing:
            raise ValueError(
                "Para cargar un Shapefile selecciona también sus archivos .shx y .dbf."
            )
    elif len(saved) != 1:
        raise ValueError("Selecciona un solo archivo para este formato.")

    return source


def _tool_download(operation, allowed_formats):
    temporary = tempfile.TemporaryDirectory(
        prefix="capa-", dir=current_app.config["RESULTS_FOLDER"]
    )
    directory = Path(temporary.name)
    try:
        source = _save_source_files(
            request.files.getlist("files"), directory, allowed_formats
        )
        output = operation(source, directory)
        mimetype = mimetypes.guess_type(output.name)[0] or "application/octet-stream"

        def stream_output():
            try:
                with output.open("rb") as stream:
                    while chunk := stream.read(64 * 1024):
                        yield chunk
            finally:
                temporary.cleanup()

        response = Response(
            stream_output(),
            mimetype=mimetype,
            headers={
                "Content-Disposition": f'attachment; filename="{output.name}"',
                "Content-Length": str(output.stat().st_size),
                "X-Content-Type-Options": "nosniff",
            },
        )
        response.call_on_close(temporary.cleanup)
        return response
    except ValueError as exc:
        temporary.cleanup()
        return jsonify(ok=False, message=str(exc)), 400
    except Exception:
        current_app.logger.exception("Error al procesar una capa geoespacial.")
        temporary.cleanup()
        return jsonify(ok=False, message="Ocurrió un error al procesar la capa."), 500


@api_bp.post("/validate")
def validate():
    files = request.files.getlist("layers")
    if not files:
        return jsonify(ok=False, message="No se recibieron archivos."), 400
    try:
        result = prepare_and_validate(files)
        return jsonify(ok=True, **result)
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except Exception as exc:
        return jsonify(ok=False, message=f"Error durante la validación: {exc}"), 500


@api_bp.post("/convert")
def convert():
    formats = {".geojson", ".json", ".gpkg", ".shp"}
    return _tool_download(
        lambda source, directory: convert_to_geoparquet(
            source, directory / f"{source.stem}.parquet"
        ),
        formats,
    )


@api_bp.post("/reproject")
def reproject():
    target_crs = request.form.get("targetCrs", "")
    return _tool_download(
        lambda source, directory: reproject_layer(source, target_crs, directory),
        {".geojson", ".json", ".gpkg", ".parquet", ".shp"},
    )


@api_bp.get("/download/<job_id>/<filename>")
def download(job_id, filename):
    from flask import send_from_directory, current_app
    import os
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    job_folder = os.path.join(upload_folder, job_id)
    if not os.path.exists(job_folder):
        return jsonify(ok=False, message="Trabajo no encontrado."), 404
    return send_from_directory(job_folder, f"errores_{filename}.gpkg", as_attachment=True )