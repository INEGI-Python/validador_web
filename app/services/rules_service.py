import json
import math
import re
import tempfile
from copy import deepcopy
from pathlib import Path

from flask import current_app, has_app_context

from engine.reglas import topologicas as DEFAULT_RULES


RULE_METHODS = {
    "noSeparado": "No_Separado",
    "fueraDe": "Fuera_De",
    "pseudonodos": "Pseudonodos",
    "sobreponerse": "Sobreponerse",
    "sobreponerse_mismo": "Sobreponerse_Mismo",
    "intersecar_mismo": "Intersecar_Mismo",
    "multiparte": "Multiparte",
    "sobreponerse_con": "Sobreponerse_Con",
    "extremos_no_conectan": "Extremos_No_Conectan",
}
METHODS_REQUIRING_LAYERS = {"fueraDe", "sobreponerse_con", "extremos_no_conectan"}
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")


def load_rules():
    if not has_app_context():
        return deepcopy(DEFAULT_RULES)

    rules_path = Path(current_app.config["RULES_FILE"])
    if not rules_path.exists():
        return deepcopy(DEFAULT_RULES)
    try:
        with rules_path.open(encoding="utf-8") as file:
            rules = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("No se pudo leer la configuración de reglas.") from exc
    if not isinstance(rules, dict):
        raise RuntimeError("La configuración de reglas tiene un formato inválido.")
    return rules


def save_rules(rules):
    rules_path = Path(current_app.config["RULES_FILE"])
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=rules_path.parent,
            prefix=f".{rules_path.name}-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(rules, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary_path.replace(rules_path)
    except OSError as exc:
        raise RuntimeError("No se pudo guardar la configuración de reglas.") from exc
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def add_layer_rules(payload):
    if not isinstance(payload, dict):
        raise ValueError("La solicitud de configuración no es válida.")

    layer_name = payload.get("layer", "")
    if not isinstance(layer_name, str) or not NAME_PATTERN.fullmatch(layer_name):
        raise ValueError("El nombre de la capa solo puede contener letras, números, guiones y guiones bajos.")

    rules_input = payload.get("rules")
    if not isinstance(rules_input, list) or not rules_input:
        raise ValueError("Selecciona al menos una regla para la capa.")

    rules = load_rules()
    if any(existing.casefold() == layer_name.casefold() for existing in rules):
        raise ValueError(f"La capa {layer_name} ya tiene reglas configuradas.")

    layer_rules = {}
    selected_methods = set()
    for item in rules_input:
        if not isinstance(item, dict):
            raise ValueError("La configuración de una regla no es válida.")
        method = item.get("method")
        if not isinstance(method, str) or method not in RULE_METHODS:
            raise ValueError("Se seleccionó un método topológico no disponible.")
        if method in selected_methods:
            raise ValueError(f"El método {method} está repetido.")
        selected_methods.add(method)

        name = item.get("name", RULE_METHODS[method])
        if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
            raise ValueError("El nombre de cada regla solo puede contener letras, números, guiones y guiones bajos.")
        if name in layer_rules:
            raise ValueError(f"La regla {name} está repetida.")

        rule = {
            "funcion": f"topo.{method}('{name}')",
            "metodo": method,
        }
        related_layers = item.get("layers", [])
        if not isinstance(related_layers, list):
            raise ValueError(f"Las capas relacionadas de {name} no son válidas.")
        normalized_layers = []
        for related_layer in related_layers:
            if not isinstance(related_layer, str) or not NAME_PATTERN.fullmatch(related_layer):
                raise ValueError(f"El nombre de una capa relacionada en {name} no es válido.")
            if related_layer not in normalized_layers:
                normalized_layers.append(related_layer)
        if method in METHODS_REQUIRING_LAYERS and not normalized_layers:
            raise ValueError(f"El método {method} requiere al menos una capa relacionada.")
        if normalized_layers:
            rule["capas"] = normalized_layers

        tolerance = item.get("tolerance")
        if tolerance not in (None, ""):
            try:
                tolerance = float(tolerance)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"La tolerancia de {name} debe ser numérica.") from exc
            if not math.isfinite(tolerance) or tolerance < 0:
                raise ValueError(f"La tolerancia de {name} debe ser finita y no negativa.")
            rule["tolerancia"] = tolerance

        exceptions = item.get("exceptions", "")
        if not isinstance(exceptions, str):
            raise ValueError(f"Las excepciones de {name} no son válidas.")
        if exceptions.strip():
            rule["excepciones"] = exceptions.strip()[:500]
        layer_rules[name] = rule

    rules[layer_name] = layer_rules
    save_rules(rules)
    return layer_name, layer_rules


def delete_rule(layer_name, rule_name):
    rules = load_rules()
    if layer_name not in rules:
        raise ValueError(f"No existe la capa {layer_name}.")
    if rule_name not in rules[layer_name]:
        raise ValueError(f"No existe la regla {rule_name} en {layer_name}.")

    del rules[layer_name][rule_name]
    if not rules[layer_name]:
        del rules[layer_name]
    save_rules(rules)
    return rules
