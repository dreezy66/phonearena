# Very small naive repair helper. Keeps original file if nothing done.
import ast, re

def attempt_repair(source_code: str, error_output: str) -> str | None:
    """
    Very naive attempt: if SyntaxError with lineno, comment out offending line.
    Returns new source or None if no change.
    """
    try:
        ast.parse(source_code)
        return None
    except SyntaxError as se:
        lines = source_code.splitlines()
        ln = se.lineno - 1 if se.lineno and se.lineno-1 < len(lines) else None
        if ln is not None:
            # comment line
            lines[ln] = "# [REPAIRED] " + lines[ln]
            return "\n".join(lines)
    except Exception:
        pass
    return None
