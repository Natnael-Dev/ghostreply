"""Enforce architectural lane boundaries and verify isolated module imports."""
import ast
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Lanes and allowed internal imports
# Pure contracts lane can only import from app.contracts.*
# Each lane can import:
# 1. Standard library / third-party modules
# 2. Modules within its own lane (e.g. app.channels.* can import app.channels.*)
# 3. app.contracts.*

ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    "app/contracts": {"app.contracts"},
    "app/gate": {"app.gate", "app.contracts"},
    "app/channels": {"app.channels", "app.contracts"},
    "app/approvals": {"app.approvals", "app.contracts"},
    "app/security": {"app.security", "app.contracts"},
}

# Explicitly documented legacy exemptions
# Any new exemption MUST fail this test.
LEGACY_EXEMPTIONS: dict[str, set[str]] = {
    "app/approvals/legacy.py": {
        "app.dashboard",
        "app.memory",
        "app.contacts",
        "app.db",
    },
    "app/channels/whatsapp.py": {
        "app.contacts",
    },
}

# Integrator files that orchestrate multiple lanes
INTEGRATOR_FILES: set[str] = {
    "app/main.py",
    "app/dashboard.py",
    "app/assistant.py",
    "app/agent_graph.py",
    "app/controls.py",
    "app/memory.py",
    "app/stt.py",
    "app/tts.py",
    "app/contacts.py",
    "app/db.py",
    "app/llm.py",
    "app/log.py",
    "app/style_retrieval.py",
    "app/vision.py",
    "app/lang.py",
}


def _get_lane(file_path: Path) -> str | None:
    rel = file_path.relative_to(REPO_ROOT).as_posix()
    for lane_prefix in ALLOWED_INTERNAL_IMPORTS:
        if rel.startswith(lane_prefix + "/") or rel == lane_prefix:
            return lane_prefix
    return None


def test_ast_lane_boundaries():
    """Verify that no lane imports from another lane except via app.contracts."""
    violations: list[str] = []

    for py_file in (REPO_ROOT / "app").rglob("*.py"):
        rel_path = py_file.relative_to(REPO_ROOT).as_posix()
        lane = _get_lane(py_file)
        if not lane:
            # Integrator or utility outside strict lanes
            continue

        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        allowed_prefixes = ALLOWED_INTERNAL_IMPORTS[lane]
        legacy_allowed = LEGACY_EXEMPTIONS.get(rel_path, set())

        for node in ast.walk(tree):
            imported_modules: list[str] = []
            if isinstance(node, ast.ImportFrom):
                if node.module == "app":
                    for alias in node.names:
                        imported_modules.append(f"app.{alias.name}")
                elif node.module:
                    imported_modules.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)

            for mod in imported_modules:
                # We check all app.* or top-level app imports
                if mod == "app" or mod.startswith("app."):
                    # Check if allowed by lane rule
                    is_allowed = any(
                        mod == allowed or mod.startswith(allowed + ".")
                        for allowed in allowed_prefixes
                    )
                    # Check legacy exemptions
                    is_legacy_exempt = any(
                        mod == exempt or mod.startswith(exempt + ".")
                        for exempt in legacy_allowed
                    )
                    if not is_allowed and not is_legacy_exempt:
                        violations.append(
                            f"{rel_path}:{getattr(node, 'lineno', '?')} illegal import '{mod}' in {lane} lane"
                        )

    assert not violations, "Lane boundary violations detected:\n" + "\n".join(violations)


def test_no_extra_legacy_exemptions():
    """Fail if new exemptions are added beyond the documented legacy exemptions."""
    assert set(LEGACY_EXEMPTIONS.keys()) == {
        "app/approvals/legacy.py",
        "app/channels/whatsapp.py",
    }


@pytest.mark.parametrize(
    "module_name",
    [
        "app.gate",
        "app.channels",
        "app.approvals",
        "app.security",
        "app.main",
    ],
)
def test_isolated_interpreter_imports(module_name: str):
    """Confirm each lane and main can be imported in a clean interpreter process without side effects or circular imports."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"Failed to import {module_name} in fresh interpreter:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
