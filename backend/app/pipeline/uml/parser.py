"""Normalized symbols for the documented PlantUML subset; never execute source."""
import re
import hashlib
from ...core.config import get_settings

ELEMENT = r'(?:"[^"\n]+"|\([^\n)]+\)|:[^:\n]+:|[\w.$]+)'
ARROW = r'[<|o*]*[-.]+(?:left|right|up|down)?[-.]*[>|o*]*'
DECLARATION = re.compile(rf'^\s*(actor|usecase|participant|boundary|control|entity|database|collections|queue|class|interface|abstract\s+class)\s+({ELEMENT})(?:\s+as\s+([\w.$]+))?', re.I)
DECORATION = re.compile(r"^(?:@(?:start|end)uml|title\b|skinparam\b|hide\b|show\b|left to right direction|top to bottom direction|autonumber\b|activate\b|deactivate\b|return\b|newpage\b|scale\b|\}|$)", re.I)


def label(value):
    return value.strip().strip('"').strip("()").strip(":").strip()


def split_parameters(value):
    if not value.strip():
        return []
    parts, start, depth, quote, escaped = [], 0, 0, None, False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char in "(<[":
            depth += 1
        elif char in ")>]":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            parts.append(value[start:index].strip()); start = index + 1
    parts.append(value[start:].strip())
    return parts


def operation_signature(value):
    clean = re.sub(r"\{(?:static|abstract|method)\}", "", value).strip()
    match = re.search(r"([\w$]+)\s*\((.*)\)\s*(?::\s*(.+))?$", clean)
    if not match:
        return None
    parameters = split_parameters(match[2])
    return {"name": match[1], "parameters": parameters, "arity": len(parameters),
        "return_type": match[3], "visibility": clean[0] if clean[:1] in {"+", "-", "#", "~"} else None,
        "text": value}


def detect_diagram_type(text):
    if re.search(r"(?m)^\s*(?:abstract\s+)?(?:class|interface)\b", text):
        return "class"
    if re.search(r"(?m)^\s*(?:participant|boundary|control|entity|database)\b", text):
        return "sequence"
    if re.search(r"\busecase\b|\([^)]*\)", text) and not re.search(r"->[^\n]+:", text):
        return "usecase"
    if re.search(r"(?m)^\s*actor\b", text) and not re.search(r"->[^\n]+:", text):
        return "usecase"
    return "sequence" if re.search(ARROW, text) else "unknown"


def parse_plantuml(text, diagram_type=None, diagram_id="diagram"):
    kind = diagram_type or detect_diagram_type(text)
    model = {"type": kind, "diagram_id": diagram_id, "parser_version": "uml-2", "warnings": [],
        "actors": [], "use_cases": [], "classes": [], "participants": [], "messages": [],
        "relationships": [], "associations": []}
    symbols, pending, namespaces = {}, [], []
    current_class = None
    block_comment = False

    def add(collection, name, alias, line, implicit=False):
        if alias in symbols:
            if not implicit:
                model["warnings"].append(f"Line {line}: duplicate alias {alias}; references are ambiguous.")
            return symbols[alias]
        symbol_key = alias if len(alias) <= 300 else hashlib.sha256(alias.encode()).hexdigest()
        element = {"name": name, "alias": alias, "id": f"{diagram_id}:{collection}:{symbol_key}",
            "source_ref": f"Line {line}", "source_spans": [{"kind": "uml", "line": line, "diagram_id": diagram_id}], "implicit": implicit}
        model[collection].append(element); symbols[alias] = element
        if sum(len(model[key]) for key in ["actors", "use_cases", "classes", "participants", "messages"]) > get_settings().MAX_UML_ELEMENTS:
            raise ValueError("Diagram exceeds the supported element count")
        return element

    def member(value):
        value = value.strip()
        if not value or re.fullmatch(r"[-=_.]+", value):
            return
        signature = operation_signature(value)
        if signature:
            current_class["operations"].append(value)
            current_class["operation_signatures"].append(signature)
        else:
            current_class["attributes"].append(value)

    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("/'"):
            block_comment = True
        if block_comment:
            if "'/" in line:
                block_comment = False
            continue
        if not line or line.startswith("'"):
            continue
        if current_class is not None:
            if line == "}":
                current_class = None
            else:
                member(line)
            continue
        namespace = re.match(r'^(?:namespace|package)\s+([\w.]+)\s*\{', line)
        if namespace:
            namespaces.append(namespace[1]); continue
        if line == "}" and namespaces:
            namespaces.pop(); continue
        declaration = DECLARATION.match(line)
        if declaration:
            token, name, alias = declaration.groups()
            token, name = token.lower(), label(name)
            if kind == "class" and token in {"class", "interface", "abstract class"}:
                qualified = ".".join([*namespaces, name])
                current_class = add("classes", qualified, alias or qualified, number)
                current_class.update(attributes=[], operations=[], operation_signatures=[], declaration=token)
                if "{" in line:
                    body = line.split("{", 1)[1]
                    if "}" in body:
                        member(body.rsplit("}", 1)[0]); current_class = None
                    elif body.strip():
                        member(body)
                else:
                    current_class = None
                continue
            collection = "actors" if kind == "usecase" and token == "actor" else "use_cases" if kind == "usecase" and token == "usecase" else "participants" if kind == "sequence" else None
            if collection:
                add(collection, name, alias or name, number); continue
        relation = re.match(rf'^({ELEMENT})\s*("[^"\n]*")?\s*({ARROW})\s*("[^"\n]*")?\s*({ELEMENT})(?:\s*:\s*(.*))?$', line)
        if relation:
            source, source_multiplicity, arrow, target_multiplicity, target, caption = relation.groups()
            # Arrow direction is semantic for sequence calls, not visual left-to-right order.
            if kind == "sequence" and arrow.startswith("<") and not arrow.endswith(">"):
                source, target = target, source
            if kind == "usecase":
                for endpoint in [source, target]:
                    if endpoint.startswith("("):
                        add("use_cases", label(endpoint), label(endpoint), number, implicit=True)
                    elif endpoint.startswith(":"):
                        add("actors", label(endpoint), label(endpoint), number, implicit=True)
            pending.append({"source": label(source), "target": label(target), "relation": arrow,
                "label": caption or "", "source_multiplicity": source_multiplicity,
                "target_multiplicity": target_multiplicity, "line": number})
            continue
        if kind == "usecase":
            implicit = re.fullmatch(r'(\([^)]*\)|:[^:]+:)(?:\s+as\s+([\w.$]+))?', line)
            if implicit:
                name = label(implicit[1]); add("use_cases" if line.startswith("(") else "actors", name, implicit[2] or name, number)
                continue
        if not DECORATION.match(line):
            model["warnings"].append(f"Line {number}: unsupported syntax; review this diagram's extraction.")

    def resolve(value):
        if value in symbols:
            return symbols[value]
        candidates = [item for item in symbols.values() if item["name"] == value]
        return candidates[0] if len(candidates) == 1 else None

    for relation in pending:
        source, target = resolve(relation["source"]), resolve(relation["target"])
        if kind == "sequence":
            source = source or add("participants", relation["source"], relation["source"], relation["line"], implicit=True)
            target = target or add("participants", relation["target"], relation["target"], relation["line"], implicit=True)
            signature = operation_signature(relation["label"])
            message = {"id": f"{diagram_id}:message:{relation['line']}",
                "from": source["alias"], "to": target["alias"], "from_id": source["id"], "to_id": target["id"],
                "receiver": target["name"], "message": relation["label"], "arrow": relation["relation"],
                "operation": signature["name"] if signature else None, "arity": signature["arity"] if signature else None,
                "is_reply": relation["relation"].startswith("--"),
                "source_ref": f"Line {relation['line']}", "source_spans": [{"kind": "uml", "line": relation["line"], "diagram_id": diagram_id}]}
            model["messages"].append(message)
        else:
            relation.update(source_id=source["id"] if source else None, target_id=target["id"] if target else None,
                source_name=source["name"] if source else relation["source"], target_name=target["name"] if target else relation["target"],
                source_ref=f"Line {relation['line']}")
            model["associations" if kind == "class" else "relationships"].append(relation)
    if current_class is not None:
        model["warnings"].append("A class body is missing its closing brace.")
    if not any(model[key] for key in ["actors", "use_cases", "classes", "participants", "messages"]):
        model["warnings"].append("No supported diagram elements were extracted.")
    if sum(len(model[key]) for key in ["actors", "use_cases", "classes", "participants", "messages"]) > get_settings().MAX_UML_ELEMENTS:
        raise ValueError("Diagram exceeds the supported element count")
    return model


def parse_usecase_diagram(text):
    return parse_plantuml(text, "usecase")


def parse_class_diagram(text):
    return parse_plantuml(text, "class")


def parse_sequence_diagram(text):
    return parse_plantuml(text, "sequence")
