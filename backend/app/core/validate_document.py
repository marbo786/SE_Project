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
        result = {"format": validate_document(sys.stdin.buffer.read(settings.MAX_UPLOAD_SIZE + 1), sys.argv[1])}
    except HTTPException as error:
        result = {"error": error.detail}
    except (MemoryError, Exception):
        result = {"error": "Document could not be validated within the supported limits"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
