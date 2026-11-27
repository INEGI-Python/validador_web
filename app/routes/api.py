import tempfile
from pathlib import Path
import json 
from flask import send_from_directory,Blueprint, Response, current_app, jsonify, request
import os
from tkinter import Tk, filedialog
from  concurrent.futures import ThreadPoolExecutor
from threading import Lock
import uuid

from app.services.geospatial import (
    SHAPEFILE_COMPONENTS,
    convert_geopackage_layers,
    convert_to_geoparquet,
    list_geopackage_layers,
    reproject_geopackage_layers,
    reproject_layer,
)
from app.services.validation_service import prepare_and_validate
from app.services.rules_service import (
    RULE_METHODS,
    add_layer_rules,
    load_rules,
    set_layer_enabled,
    set_rule_enabled,
)

api_bp = Blueprint("api", __name__)

def _get_environ_names():
    environ_names = ("USERNAME", "USER")
    for name in environ_names:
        value = os.environ.get(name)
        if value:
            return value
    return request.environ.get("REMOTE_USER")


@api_bp.get("/client-user")
def client_user():
    username = _get_environ_names()
    if not username:
        return jsonify(ok=False, message="No se pudo determinar el usuario de Windows del cliente."), 404
    return jsonify(ok=True, username=username)

@api_bp.post("/validate")
def validate():
    data = json.loads(request.get_data())
    print(data)
    layers = data.get("layers",[])
    if not layers:
        return jsonify(ok=False, message="No se recibieron archivos."), 400
    try:
        result = prepare_and_validate(layers)
        return jsonify(ok=True, **result)
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except Exception as exc:
        return jsonify(ok=False, message=f"Error durante la validación: {exc}"), 500


@api_bp.get("/rules")
def get_rules():
    try:
        return jsonify(
            ok=True,
            layers=load_rules(),
            methods=[
                {"method": method, "name": name}
                for method, name in RULE_METHODS.items()
            ],
        )
    except RuntimeError as exc:
        current_app.logger.exception("No se pudo cargar la configuración de reglas.")
        return jsonify(ok=False, message=str(exc)), 500


@api_bp.post("/rules")
def create_layer_rules():
    try:
        layer_name, rules = add_layer_rules(request.get_json(silent=True))
        return jsonify(ok=True, layer=layer_name, rules=rules), 201
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except RuntimeError as exc:
        current_app.logger.exception("No se pudo guardar la configuración de reglas.")
        return jsonify(ok=False, message=str(exc)), 500


@api_bp.patch("/rules/<layer_name>")
def update_layer_enabled(layer_name):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(ok=False, message="Se requiere indicar el estado de la capa."), 400
    try:
        enabled = payload.get("enabled")
        rules = set_layer_enabled(layer_name, enabled)
        return jsonify(ok=True, layers=rules)
    except KeyError as exc:
        return jsonify(ok=False, message=exc.args[0]), 404
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except RuntimeError as exc:
        current_app.logger.exception("No se pudo actualizar el estado de la capa.")
        return jsonify(ok=False, message=str(exc)), 500


@api_bp.patch("/rules/<layer_name>/<rule_name>")
def update_rule_enabled(layer_name, rule_name):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(ok=False, message="Se requiere indicar el estado de la regla."), 400
    try:
        enabled = payload.get("enabled")
        rules = set_rule_enabled(layer_name, rule_name, enabled)
        return jsonify(ok=True, layers=rules)
    except KeyError as exc:
        return jsonify(ok=False, message=exc.args[0]), 404
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except RuntimeError as exc:
        current_app.logger.exception("No se pudo actualizar el estado de la regla.")
        return jsonify(ok=False, message=str(exc)), 500



@api_bp.post("/gpkg_layers")
def gpkg_layers():
    try:
        filepath = json.loads(request.get_data()).get("filepath", "")
        print(filepath)
        layers = list_geopackage_layers(Path(filepath))
        return jsonify(ok=True, layers=layers)
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except Exception:
        current_app.logger.exception("No se pudieron consultar las capas del GeoPackage.")
        return jsonify(ok=False, message="Ocurrió un error al consultar el GeoPackage."), 500


@api_bp.post("/reproject")
def reproject():
    data = json.loads(request.get_data())
    gpkg = Path(data.get("gpkg",""))
    selected_layers=data.get("layers", [])
    epsg = data.get("epsg","")
    def operation(source, directory, selected_layers):
        if source.suffix.lower() == ".gpkg":
            return reproject_geopackage_layers(Path(source), epsg, selected_layers, Path(directory))
        return reproject_layer(Path(source), epsg, Path(directory))

    return jsonify(ok=True, result=operation(gpkg, tempfile.mkdtemp(prefix="capa-reproyectada-", dir=current_app.config["RESULTS_FOLDER"]),selected_layers))


@api_bp.get("/download/<job_id>/<filename>")
def download(job_id, filename):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    job_folder = os.path.join(upload_folder, job_id)
    if not os.path.exists(job_folder):
        return jsonify(ok=False, message="Trabajo no encontrado."), 404
    return send_from_directory(job_folder, f"errores_{filename}.gpkg", as_attachment=True )

@api_bp.get("/descargar/<folder>/<file>")
def descargar(folder,file):
    print(folder,file)
    tmp = current_app.config["RESULTS_FOLDER"]
    result_folder = os.path.join(tmp,folder)
    if not os.path.exists(result_folder):
        return jsonify(ok=False, message="No se encontro la carpeta de trabajo"),404
    return send_from_directory(result_folder,file,as_attachment=True)


@api_bp.get("/seleccionar_archivo/<multi>")
def seleccionar_archivo(multi):
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    ruta = filedialog.askopenfilenames(
        title="Seleccione archivo .parquet",
        filetypes=[("GeoParquet","*.parquet")]
    ) if multi=="1" else filedialog.askopenfilename(
        title="Seleccione archivo geográfico",
        filetypes=[("GeoPackage","*.gpkg"),("Shapefile","*.shp"),("GeoJSON","*.geojson")]
    )
    root.destroy()
    if not ruta:
        return jsonify({"ok":False,"message":"No se pudo seleccionar el archivo"})
    return jsonify({"ok":True,"ruta":ruta})


ejecutor = ThreadPoolExecutor(max_workers=4)
tareas = {}
tareas_bloqueada = Lock() 

#@api_bp.post("/convert")
def convert(tarea_id:str,datos):
    def operation(source, directory, selected_layers):
        if source.suffix.lower() == ".gpkg":
            return convert_geopackage_layers(source, selected_layers, directory)
        return convert_to_geoparquet(Path(source), f"{directory}/{source.stem}.parquet")
    
    try:
        source= Path(datos.get("gpkg", ""))
        selected_layers=datos.get("layers", [])
        result = operation(source, tempfile.mkdtemp(prefix="capa-", dir=current_app.config["RESULTS_FOLDER"]), selected_layers)
        with tareas_bloqueada:
            tareas[tarea_id]["estado"] ="Completado"
            tareas[tarea_id]["progreso"] = 100
            tareas[tarea_id]["message"] = "Proceso Terminado con éxito"
            tareas[tarea_id]["resultado"] = result
    except Exception as exc:
        with tareas_bloqueada:
            tareas[tarea_id]["estado"]= "Fallido"
            tareas[tarea_id]["mensaje"]="Ocurrio un error durante el proceso"
            tareas[tarea_id]["error"] = str(exc)
 
@api_bp.post("/comenzar_tarea")
def comenzar_tarea():
    data=request.get_json(silent=True) or {}
    total_pasos = int(data.get("total_pasos",4))
    total_pasos = max(1,min(total_pasos,20))
    tarea_id = str(uuid.uuid4())

    with tareas_bloqueada:
        tareas[tarea_id]={
            "id":tarea_id,
            "estado":"corriendo",
            "progreso":0,
            "message":"Tarea iniciada....",
            "result":None,
            "error":None
        }

    ejecutor.submit(convert,tarea_id,data)
    return jsonify({"id_tarea":tarea_id,"estado":"corriendo"}),202

@api_bp.get("/estado_trabajos/<tarea_id>")
def estado_trabajos(tarea_id:str):
    with tareas_bloqueada:
        tarea=tareas.get(tarea_id)
        if not tarea:
            return jsonify({"error":"Tarea no encontrada"}),404
        snapshot = dict(tarea)
    return jsonify(snapshot),200



#  supervisor_cs@lvvdigital.com
# 163663