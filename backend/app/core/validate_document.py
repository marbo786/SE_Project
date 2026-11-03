"""One-shot parser subprocess: parent enforces wall time; Linux enforces address space."""
import json
import sys


def main():
    budgets = json.loads(sys.argv[2])
    if sys.platform != "win32":
        import resource
        maximum = budgets["PARSER_MEMORY_MB"] * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))
    from fastapi import HTTPException
    from .config import get_settings
    from .uploads import validate_document
    settings = get_settings()
    for key, value in budgets.items():
        setattr(settings, key, value)
    try:
        content = sys.stdin.buffer.read(settings.MAX_UPLOAD_SIZE + 1)
        mode = sys.argv[3] if len(sys.argv) > 3 else "validate"
        if mode.startswith("uml:"):
            from .uploads import validate_uml
            from ..pipeline.uml.parser import parse_plantuml
            validate_uml(content, sys.argv[1])
            _, kind, diagram_id = mode.split(":", 2)
            print(json.dumps({"extraction": parse_plantuml(content.decode("utf-8-sig"), kind, diagram_id)}))
            return
        format = validate_document(content, sys.argv[1])
        result = {"format": format}
        if mode == "extract":
            from io import BytesIO
            from ..pipeline.srs.parser import parse_srs
            result["extraction"] = parse_srs(BytesIO(content), format)
    except HTTPException as error:
        result = {"error": error.detail}
    except Exception:
        result = {"error": "Document could not be validated within the supported limits"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
