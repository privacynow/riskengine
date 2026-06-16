import re
from typing import Any, Dict, List, Optional


def extract_placeholders_from_text(template_str: Optional[str]) -> List[str]:
    if not template_str:
        return []
    pattern = r"%([^%]+)%"
    matches = re.findall(pattern, template_str)
    return sorted(set(m.strip() for m in matches))


def render_template(template_str: str, context: Dict[str, Any]) -> str:
    if not template_str:
        return template_str
    out = template_str
    for match in re.findall(r"%([^%]+)%", template_str):
        key = match.strip()
        token = f"%{key}%"
        out = out.replace(token, str(context[key]) if key in context else "")
    return out


def parse_params_string(params_str: str) -> Dict[str, str]:
    result = {}
    if not params_str or not params_str.strip():
        return result
    for kv_pair in params_str.split("&"):
        kv_pair = kv_pair.strip()
        if "=" not in kv_pair:
            continue
        key, val = kv_pair.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def parse_headers_string(headers_str: str) -> Dict[str, str]:
    headers = {}
    if not headers_str:
        return headers
    for line in headers_str.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        headers[key.strip()] = val.strip()
    return headers


def decorate_dsl_expression(dsl_expression: str, signal_map: Dict[str, Any]) -> str:
    result = dsl_expression
    for sig_name in sorted(signal_map.keys(), key=len, reverse=True):
        pattern = r"\b" + re.escape(sig_name) + r"\b"
        result = re.sub(pattern, f"{sig_name} ({signal_map[sig_name]})", result)
    return result


def build_template_explanation(template_str: Optional[str], param_map: Dict[str, Any]) -> str:
    if not template_str:
        return ""
    out = template_str
    for match in re.findall(r"%([^%]+)%", template_str):
        key = match.strip()
        out = out.replace(f"%{key}%", str(param_map.get(key, "")))
    return out
