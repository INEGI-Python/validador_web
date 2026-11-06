import shutil

from flask import Blueprint, jsonify, request
from app.services.validation_service import prepare_and_validate

api_bp = Blueprint("api", __name__)

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


@api_bp.get("/download/<job_id>")
def download(job_id):
    from flask import send_from_directory, current_app
    import os

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    job_folder = os.path.join(upload_folder, job_id)
    if not os.path.exists(job_folder):
        return jsonify(ok=False, message="Trabajo no encontrado."), 404

    # Crear un archivo comprimido con todos los resultados de errores
    job_folder = os.path.join(upload_folder, job_id)
    if not os.path.exists(job_folder):
        return jsonify(ok=False, message="Trabajo no encontrado."), 404 
    
    zip_filename = f"errores_{job_id}.gpkg"
    zip_path = os.path.join(job_folder, zip_filename)
    #shutil.make_archive(zip_path.replace('.gpkg', ''), 'zip', job_folder)

    return send_from_directory(job_folder, zip_path, as_attachment=True)   