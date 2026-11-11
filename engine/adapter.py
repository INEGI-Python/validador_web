"""Puente entre Flask y el motor topológico existente.

Coloca tus archivos reglas.py y topologias.py en este directorio (engine/) o ajusta
los imports. El adaptador evita que la capa web conozca detalles de GeoPandas/Dask.
"""
from pathlib import Path
import ast

from app.services.rules_service import RULE_METHODS, load_rules

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


def _run_rule(topo, rule_name, rule):
    method_name = rule.get("metodo")
    if method_name:
        if method_name not in RULE_METHODS:
            raise ValueError(f"Método topológico no permitido: {method_name}")
        getattr(topo, method_name)(rule_name)
        return

    expression = ast.parse(rule["funcion"], mode="eval").body
    if (
        not isinstance(expression, ast.Call)
        or not isinstance(expression.func, ast.Attribute)
        or not isinstance(expression.func.value, ast.Name)
        or expression.func.value.id != "topo"
        or expression.func.attr not in RULE_METHODS
        or expression.keywords
        or len(expression.args) != 1
        or not isinstance(expression.args[0], ast.Constant)
        or not isinstance(expression.args[0].value, str)
    ):
        raise ValueError(f"La definición de la regla {rule_name} no es válida.")
    getattr(topo, expression.func.attr)(expression.args[0].value)


def validate_layer(folder: Path, layer_name: str):
    if IMPORT_ERROR:
        raise RuntimeError(
            "Falta integrar engine/reglas.py y engine/topologias.py. "
            f"Detalle: {IMPORT_ERROR}"
        )
    rules = load_rules().get(layer_name)
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
            _run_rule(topo, rule_name, rule)
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
