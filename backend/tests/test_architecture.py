"""4계층 의존성 규칙 검사: import 문을 분석해 역방향·금지 참조를 찾습니다."""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

FORBIDDEN = {
    "domain": {"presentation", "application", "infrastructure", "database",
               "fastapi", "sqlalchemy", "pydantic", "starlette"},
    "application": {"presentation", "fastapi"},
    "infrastructure": {"presentation", "application"},
    "presentation": {"infrastructure"},
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_layer_dependencies() -> None:
    violations = []
    for layer, banned in FORBIDDEN.items():
        for file in (SRC / layer).rglob("*.py"):
            bad = _imports(file) & banned
            if bad:
                violations.append(f"{file.relative_to(SRC)} → {sorted(bad)}")
    assert not violations, "계층 의존성 위반:\n" + "\n".join(violations)


def test_every_package_has_init() -> None:
    missing = [
        str(d.relative_to(SRC))
        for layer in FORBIDDEN
        for d in [SRC / layer, *(p for p in (SRC / layer).rglob("*") if p.is_dir() and p.name != "__pycache__")]
        if not (d / "__init__.py").exists()
    ]
    assert not missing, f"__init__.py 누락: {missing}"
