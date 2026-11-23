from flask import Blueprint, render_template
main_bp = Blueprint("main", __name__)

@main_bp.get("/")
def index():
    return render_template("index.html",small1="Seleccione la ubicacion de su archivo",listaCapas="Seleccione una o varias capas para convertir")
