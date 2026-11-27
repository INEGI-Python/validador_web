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
    raise ValueError("La opción para agregar capas fue eliminada.")


def set_layer_enabled(layer_name, enabled):
    if not isinstance(enabled, bool):
        raise ValueError("El estado de la capa debe ser verdadero o falso.")

    rules = load_rules()
    if layer_name not in rules:
        raise KeyError(f"No existe la capa {layer_name}.")

    layer_rules = rules[layer_name]
    for rule_name, rule in layer_rules.items():
        if rule_name != "_enabled":
            rule["enabled"] = enabled
    layer_rules.pop("_enabled", None)
    save_rules(rules)
    return rules


def set_rule_enabled(layer_name, rule_name, enabled):
    if not isinstance(enabled, bool):
        raise ValueError("El estado de la regla debe ser verdadero o falso.")

    rules = load_rules()
    if layer_name not in rules:
        raise KeyError(f"No existe la capa {layer_name}.")
    layer_rules = rules[layer_name]
    if rule_name not in layer_rules or rule_name == "_enabled":
        raise KeyError(f"No existe la regla {rule_name} en {layer_name}.")

    if layer_rules.get("_enabled") is False:
        for current_rule_name, rule in layer_rules.items():
            if current_rule_name != "_enabled":
                rule["enabled"] = False
    layer_rules.pop("_enabled", None)
    layer_rules[rule_name]["enabled"] = enabled
    save_rules(rules)
    return rules
