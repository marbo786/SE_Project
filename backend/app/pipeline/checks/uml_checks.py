"""Deterministic checks over resolved UML symbols and receiver-specific calls."""
from collections import Counter, defaultdict, deque
from ...core.config import get_yaml_config
from ..uml.parser import operation_signature


def issue(rule, severity_key, element, explanation):
    return {"rule_id": rule, "severity": get_yaml_config().get("rules", {}).get(severity_key, {}).get("severity", "major"),
        "quoted_text": element.get("name") or element.get("message"), "explanation": explanation,
        "requirement_id": None, "element_id": element.get("id"), "finding_type": "deterministic", "artifact_type": "uml",
        "source_ref": element.get("source_ref"), "source_spans": element.get("source_spans", [])}


def duplicate_names(elements):
    counts = Counter(element["name"].casefold() for element in elements)
    return [issue("FR-609", "uml_duplicate_name", element, f'Duplicate display name "{element["name"]}"; use distinct names or review the aliases.')
        for element in elements if counts[element["name"].casefold()] > 1]


def check_usecase_diagram(model):
    actors, cases = model.get("actors", []), model.get("use_cases", [])
    symbols = {element.get("alias", element["name"]): element.get("id", element["name"]) for element in [*actors, *cases]}
    graph = defaultdict(set)
    for edge in model.get("relationships", []):
        source = edge.get("source_id") or symbols.get(edge["source"])
        target = edge.get("target_id") or symbols.get(edge["target"])
        if source and target:
            graph[source].add(target); graph[target].add(source)

    def reaches(start, targets):
        queue, seen = deque([start]), {start}
        while queue:
            node = queue.popleft()
            for adjacent in graph[node] - seen:
                if adjacent in targets:
                    return True
                seen.add(adjacent); queue.append(adjacent)
        return False

    actor_ids = {actor.get("id", actor["name"]) for actor in actors}
    case_ids = {case.get("id", case["name"]) for case in cases}
    findings = duplicate_names(cases)
    for actor in actors:
        if not reaches(actor.get("id", actor["name"]), case_ids):
            findings.append(issue("FR-601", "uml_actor_disconnected", actor, f'Actor "{actor["name"]}" has no path to a use case.'))
    for case in cases:
        if not reaches(case.get("id", case["name"]), actor_ids):
            findings.append(issue("FR-602", "uml_usecase_disconnected", case, f'Use case "{case["name"]}" has no path to an actor.'))
    return findings


def check_class_diagram(model):
    findings = duplicate_names(model.get("classes", []))
    names = {value for element in model.get("classes", []) for value in [element["name"], element.get("alias", element["name"])]}
    for element in model.get("classes", []):
        if not element.get("attributes") and not element.get("operations"):
            findings.append(issue("FR-603", "uml_class_empty", element, f'Class "{element["name"]}" has no attributes or operations.'))
    for relation in model.get("associations", []):
        element = {**relation, "name": f'{relation["source"]} {relation["relation"]} {relation["target"]}'}
        if "|" not in relation["relation"] and "." not in relation["relation"] and not relation.get("source_multiplicity") and not relation.get("target_multiplicity"):
            findings.append(issue("FR-604", "uml_assoc_no_multiplicity", element, "Association has no multiplicity at either endpoint."))
        for endpoint in ["source", "target"]:
            if not relation.get(endpoint + "_id") and relation[endpoint] not in names:
                findings.append(issue("FR-605", "uml_undefined_class", element, f'Association refers to undefined class "{relation[endpoint]}".'))
    return findings


def check_sequence_diagram(model, class_model=None):
    findings = duplicate_names([p for p in model.get("participants", []) if not p.get("implicit")])
    if not class_model:
        return findings
    classes = class_model.get("classes", [])
    participants = {p.get("alias", p["name"]): p["name"] for p in model.get("participants", [])}
    for message in model.get("messages", []):
        if message.get("is_reply") or not message.get("operation"):
            continue
        receiver = message.get("receiver") or participants.get(message.get("to"), message.get("to", ""))
        receiver = receiver.split(":")[-1].strip()
        candidates = [c for c in classes if receiver.casefold() in {c["name"].casefold(), c.get("alias", c["name"]).casefold()}]
        signatures = [signature for c in candidates for signature in (c.get("operation_signatures") or [operation_signature(op) for op in c.get("operations", [])]) if signature]
        matches = [signature for signature in signatures if signature["name"].casefold() == message["operation"].casefold()
            and (message.get("arity") is None or signature["arity"] == message["arity"])]
        if not matches:
            findings.append(issue("FR-606", "uml_op_not_in_class", message,
                f'Call "{message["message"]}" has no matching operation/argument count on receiver "{receiver}".'))
    return findings


def run_all_uml_checks(model, class_model=None):
    if model.get("type") == "usecase":
        return check_usecase_diagram(model)
    if model.get("type") == "class":
        return check_class_diagram(model)
    if model.get("type") == "sequence":
        return check_sequence_diagram(model, class_model)
    return []
