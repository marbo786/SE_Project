from app.pipeline.uml.parser import parse_plantuml
from app.pipeline.checks.uml_checks import run_all_uml_checks


def test_aliases_retain_distinct_equal_labels_and_source():
    model = parse_plantuml('actor User\nusecase "Login" as A\nusecase "Login" as B\nUser --> A', "usecase", "a-1")
    assert [element["alias"] for element in model["use_cases"]] == ["A", "B"]
    assert len({element["id"] for element in model["use_cases"]}) == 2
    findings = run_all_uml_checks(model)
    disconnected = [f for f in findings if f["rule_id"] == "FR-602"]
    assert len(disconnected) == 1 and disconnected[0]["element_id"].endswith(":B")
    assert disconnected[0]["source_ref"] == "Line 3"


def test_usecase_requires_path_to_actor_and_supports_include_chain():
    model = parse_plantuml('actor User\nusecase "Login" as A\nusecase "Validate" as B\nUser --> A\nA ..> B : include', "usecase")
    assert not run_all_uml_checks(model)
    model = parse_plantuml('actor User\nactor Admin\nUser --> Admin\nusecase Lonely', "usecase")
    assert {f["rule_id"] for f in run_all_uml_checks(model)} == {"FR-601", "FR-602"}


def test_receiver_operation_and_overload_arity():
    classes = parse_plantuml('class Auth {\n+login(name: String): bool\n+login(name: String, password: String): bool\n}\nclass Store {\n+save()\n}', "class")
    sequence = parse_plantuml('participant "Auth" as A\nparticipant "Store" as S\nUser -> A: login("name")\nUser -> S: login("name")\nUser -> A: login()', "sequence")
    failures = run_all_uml_checks(sequence, classes)
    assert len(failures) == 2
    assert 'receiver "Store"' in failures[0]["explanation"]
    assert failures[1]["quoted_text"] == "login()"


def test_namespace_interface_and_leftward_reply():
    classes = parse_plantuml('namespace accounts {\ninterface Auth {\n+login(): bool\n}\n}', "class")
    sequence = parse_plantuml('participant "accounts.Auth" as A\nUser -> A: login()\nUser <-- A: true', "sequence")
    assert not run_all_uml_checks(sequence, classes)
    assert sequence["messages"][1]["from"] == "A"
    assert sequence["messages"][1]["to"] == "User"


def test_unsupported_syntax_is_reported():
    model = parse_plantuml('component Unsupported\nclass Valid { +run() }', "class")
    assert model["warnings"]
    assert model["classes"][0]["operation_signatures"][0]["name"] == "run"
