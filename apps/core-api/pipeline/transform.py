from typing import Any
from typing import Any as AnyType

import jmespath

from .functions.currency import to_minor

FUNCTIONS = {"to_minor": to_minor}


def apply_function(func_name: str, args: list):
    if func_name not in FUNCTIONS:
        raise ValueError(f"Unknown function: {func_name}")
    return FUNCTIONS[func_name](*args)


def split_args(s: str):
    buf, out, in_str = "", [], False
    for ch in s:
        if ch == "'" and not in_str:
            in_str = True
            buf += ch
            continue
        if ch == "'" and in_str:
            in_str = False
            buf += ch
            continue
        if ch == "," and not in_str:
            out.append(buf.strip())
            buf = ""
            continue
        buf += ch
    if buf.strip():
        out.append(buf.strip())
    return out


def set_deep(obj: dict[str, Any], dotted: str, value: AnyType):
    parts = dotted.split(".")
    cur = obj
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def transform(payload: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for target_path, expr in mapping.get("assign", {}).items():
        value = None
        if isinstance(expr, str):
            if "(" in expr and expr.endswith(")") and expr.split("(")[0] in FUNCTIONS:
                name = expr.split("(")[0]
                args_str = expr[len(name) + 1 : -1]
                args = []
                if args_str.strip():
                    parts = split_args(args_str)
                    for part in parts:
                        part = part.strip()
                        if part.startswith("'") and part.endswith("'"):
                            args.append(part[1:-1])
                        else:
                            args.append(jmespath.search(part, payload))
                value = apply_function(name, args)
            else:
                value = jmespath.search(expr, payload)
        else:
            value = expr
        set_deep(out, target_path, value)
    return out
