"""Puente entre Flask y el motor topológico existente.

Coloca tus archivos reglas.py y topologias.py en este directorio (engine/) o ajusta
los imports. El adaptador evita que la capa web conozca detalles de GeoPandas/Dask.
"""
from pathlib import Path

try:
    from .reglas import topologicas
    from .topologias import Topo
except ImportError as exc:
    topologicas = None
    Topo = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def discover_parquet_layers(folder: Path):
    return sorted(p.stem for p in folder.glob("*.parquet"))


def validate_layer(folder: Path, layer_name: str):
    if IMPORT_ERROR:
        raise RuntimeError(
            "Falta integrar engine/reglas.py y engine/topologias.py. "
            f"Detalle: {IMPORT_ERROR}"
        )
    rules = topologicas.get(layer_name)
    if not rules:
        return {
            "layer": layer_name,
            "status": "sin_reglas",
            "rule_count": 0,
            "error_count": 0,
            "rules": []
        }

    # Tu motor concatena ruta + capa + '.parquet', por eso conservamos '/' final.
    route = str(folder.resolve()) + "/"
    topo = Topo(route, layer_name, rules)

    execution_errors = []
    for rule_name, rule in topo.reglas.items():
        try:
            # Conserva compatibilidad con tu diccionario actual. Próximo refactor:
            # almacenar el nombre del método en vez de una expresión ejecutable.
            expression = rule["funcion"]
            eval(expression, {"topo": topo})
        except Exception as exc:
            execution_errors.append({"rule": rule_name, "message": str(exc)})

    rule_results = []
    total = 0
    for name in topo.reglas.keys():
        detail = topo.errores.get(name, {})
        count = int(detail.get("cantidad", 0) or 0)
        total += count
        rule_results.append({
            "name": name,
            "count": count,
            "time": detail.get("tiempo", ""),
            "status": "error" if count else "ok",
        })

    return {
        "layer": layer_name,
        "status": "completed" if not execution_errors else "completed_with_errors",
        "rule_count": len(topo.reglas),
        "error_count": total,
        "rules": rule_results,
        "execution_errors": execution_errors,
    }
