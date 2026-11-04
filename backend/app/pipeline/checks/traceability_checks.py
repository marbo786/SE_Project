"""Evidence-bearing candidate links and cycle-safe coverage of typed endpoints."""
from collections import defaultdict, deque
import re
from ...core.config import get_yaml_config
from ..srs.parser import REQ_ID

STOPWORDS = set("a an and are as at be by for from has he in is it its of on that the to was were will with system shall must user allow string int bool void".split())


def requirement_key(requirement, index=0):
    return requirement.get("internal_id") or requirement.get("id") or f"unidentified-{index + 1}"


def element_key(element, label_field="name"):
    return element.get("id") or element.get(label_field, "")


def _get_content_words(text):
    text = REQ_ID.sub(" ", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    words = re.findall(r"[a-z]+", text.lower())
    words = [word[:-1] if word.endswith("s") and not word.endswith("ss") and len(word) > 3 else word for word in words]
    return {word for word in words if word not in STOPWORDS}


def _jaccard(left, right):
    return len(left & right) / len(left | right) if left | right else 0.0


def explicit_id_match(authored_id, text):
    if not authored_id:
        return False
    normalize = lambda value: value.upper().replace("-", "")
    return normalize(authored_id) in {normalize(match.group()) for match in REQ_ID.finditer(text)}


def reachable(links, start, *, confirmed_only=False):
    graph = defaultdict(list)
    for link in links:
        if link.get("status") == "rejected" or link.get("is_stale") or (confirmed_only and link.get("status") != "confirmed"):
            continue
        source, target = (link["source_type"], link["source_id"]), (link["target_type"], link["target_id"])
        graph[source].append((target, link))
    paths, queue = {start: []}, deque([start])
    while queue:
        current = queue.popleft()
        for target, link in graph[current]:
            if target not in paths:
                paths[target] = [*paths[current], link]
                queue.append(target)
    return paths


def build_trace_links(requirements, usecase_model=None, sequence_model=None, class_model=None):
    threshold = get_yaml_config().get("trace_jaccard_threshold", .3)
    cases = (usecase_model or {}).get("use_cases", [])
    messages = [message for message in (sequence_model or {}).get("messages", []) if not message.get("is_reply")]
    participants = (sequence_model or {}).get("participants", [])
    classes = (class_model or {}).get("classes", [])
    links = {}

    def add(source_type, source_id, source_label, target_type, target_id, target_label, origin, similarity, evidence=None):
        key = (source_type, source_id, target_type, target_id)
        candidate = {"source_type": source_type, "source_id": source_id, "source_label": source_label,
            "target_type": target_type, "target_id": target_id, "target_label": target_label,
            "status": "suggested", "origin": origin, "confidence": round(similarity, 3),
            "evidence": evidence or {"method": origin, "note": "Candidate evidence; similarity is not a probability of correctness."}}
        if key not in links or links[key]["confidence"] < similarity:
            links[key] = candidate

    def infer(source_type, source_id, source_label, source_text, target_type, target, target_text, authored_id=None, target_label=None):
        target_id = element_key(target, "message" if target_type == "sequence" else "name")
        explicit = explicit_id_match(authored_id, target_text)
        similarity = _jaccard(_get_content_words(source_text), _get_content_words(target_text))
        if explicit or similarity >= threshold:
            add(source_type, source_id, source_label, target_type, target_id,
                target_label or target.get("name") or target.get("message"),
                "explicit_identifier" if explicit else "lexical_similarity", 1.0 if explicit else similarity,
                {"method": "explicit_identifier" if explicit else "lexical_similarity", "authored_id": authored_id,
                    "similarity": round(similarity, 3), "target_source": target.get("source_spans", [])})

    for index, requirement in enumerate(requirements):
        key, text = requirement_key(requirement, index), requirement.get("text", "")
        display = requirement.get("id") or f"Unidentified requirement {index + 1}"
        for case in cases:
            infer("requirement", key, display, text, "usecase", case, case["name"], requirement.get("id"))
        for message in messages:
            infer("requirement", key, display, text, "sequence", message, message["message"], requirement.get("id"))
        for cls in classes:
            combined = " ".join([cls["name"], *cls.get("attributes", []), *cls.get("operations", [])])
            infer("requirement", key, display, text, "class", cls, combined, requirement.get("id"))
    for case in cases:
        for message in messages:
            infer("usecase", element_key(case), case["name"], case["name"], "sequence", message, message["message"])
    participant_names = {part.get("alias", part["name"]): part["name"] for part in participants}
    for element in [*participants, *messages]:
        receiver = element.get("receiver") or participant_names.get(element.get("to"), element.get("to")) or element.get("name", "")
        receiver = receiver.split(":")[-1].strip()
        matches = [cls for cls in classes if receiver.casefold() in {cls["name"].casefold(), cls.get("alias", cls["name"]).casefold()}]
        if len(matches) == 1:
            cls = matches[0]
            add("sequence", element_key(element, "message" if "message" in element else "name"),
                element.get("message") or element["name"], "class", element_key(cls), cls["name"], "receiver_identity", 1.0)
    direct = list(links.values())
    sources = [("requirement", requirement_key(req, i), req.get("id") or f"Unidentified requirement {i+1}") for i, req in enumerate(requirements)]
    sources += [("usecase", element_key(case), case["name"]) for case in cases]
    for source_type, source_id, display in sources:
        paths = reachable(direct, (source_type, source_id))
        for cls in classes:
            path = paths.get(("class", element_key(cls)))
            if path and len(path) > 1:
                add(source_type, source_id, display, "class", element_key(cls), cls["name"], "transitive",
                    min(edge.get("confidence", 0) for edge in path),
                    {"method": "transitive", "path": [[edge["source_type"], edge["source_id"], edge["target_type"], edge["target_id"]] for edge in path]})
    return list(links.values())


def trace_obligations(requirements, usecase_model=None, sequence_model=None, class_model=None, links=None):
    links = links or []
    cases = (usecase_model or {}).get("use_cases", [])
    messages = [m for m in (sequence_model or {}).get("messages", []) if not m.get("is_reply")]
    classes = (class_model or {}).get("classes", [])
    req_nodes = [("requirement", requirement_key(req, index)) for index, req in enumerate(requirements)]
    case_nodes = [("usecase", element_key(case)) for case in cases]
    seq_nodes = [("sequence", element_key(message, "message")) for message in messages]
    class_nodes = [("class", element_key(cls)) for cls in classes]
    all_starts = set([*req_nodes, *case_nodes])
    candidate_paths = {node: reachable(links, node) for node in all_starts}
    confirmed_paths = {node: reachable(links, node, confirmed_only=True) for node in all_starts}
    obligations = []

    def add(rule, element, source_nodes, target_nodes, explanation):
        candidates = [(source, target) for source in source_nodes for target in target_nodes]
        obligations.append({"rule_id": rule, "element": element, "explanation": explanation,
            "covered": any(target in candidate_paths.get(source, {}) for source, target in candidates),
            "confirmed": any(target in confirmed_paths.get(source, {}) for source, target in candidates)})

    if usecase_model is not None:
        for index, req in enumerate(requirements):
            if req.get("class") != "non_functional":
                add("FR-701", req, [req_nodes[index]], case_nodes, "Requirement has no candidate path to a use case.")
        for case, node in zip(cases, case_nodes):
            add("FR-702", case, req_nodes, [node], "Use case has no candidate path from a requirement.")
            if sequence_model is not None:
                add("FR-703", case, [node], seq_nodes, "Use case has no candidate sequence message.")
        for message, node in zip(messages, seq_nodes):
            add("FR-704", message, case_nodes, [node], "Sequence message has no candidate path from a use case.")
    if class_model is not None:
        for cls, node in zip(classes, class_nodes):
            add("FR-705", cls, req_nodes, [node], "Class has no candidate path from a requirement.")
        if usecase_model is None:
            for index, req in enumerate(requirements):
                add("FR-705", req, [req_nodes[index]], class_nodes, "Requirement has no candidate path to a class.")
    return obligations


def check_traceability(requirements, usecase_model=None, sequence_model=None, class_model=None, existing_links=None):
    severity_keys = {"FR-701": "trace_req_no_usecase", "FR-702": "trace_usecase_no_req", "FR-703": "trace_usecase_no_seq", "FR-704": "trace_seq_no_usecase", "FR-705": "trace_missing_class"}
    rules = get_yaml_config().get("rules", {})
    findings = []
    for obligation in trace_obligations(requirements, usecase_model, sequence_model, class_model, existing_links):
        if obligation["covered"]:
            continue
        element, rule = obligation["element"], obligation["rule_id"]
        findings.append({"rule_id": rule, "severity": rules.get(severity_keys[rule], {}).get("severity", "major"),
            "quoted_text": element.get("text") or element.get("name") or element.get("message"),
            "explanation": obligation["explanation"], "requirement_id": element.get("id") if "text" in element else None,
            "element_id": element.get("internal_id") or element.get("id"),
            "finding_type": "deterministic", "artifact_type": "traceability",
            "source_ref": element.get("source_ref"), "source_spans": element.get("source_spans", [])})
    return findings
