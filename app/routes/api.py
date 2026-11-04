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
