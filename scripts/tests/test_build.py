"""Test entry point: python3 scripts/tests/test_build.py. Discovers sibling suites."""
from __future__ import annotations

import support
from support import REPO_ROOT, check, run_build_args, silently, skip

import importlib
import importlib.util
import inspect
import os
import shared as shared_mod
import sys
import tempfile
from build import (
    DIAGRAM_TARGETS,
    HTML_TARGETS,
    PPTX_TARGETS,
    SCREEN_TARGETS,
)
from pathlib import Path
from shared import (
    DIAGRAMS,
    DIAGRAM_TEMPLATES,
    HTML_TEMPLATES,
    MARP_TEMPLATES,
    PARCHMENT_RGB,
    SCREEN_TEMPLATES,
    TEMPLATES,
    build_targets,
    diagram_targets,
    marp_targets,
    pptx_targets,
    screen_targets,
)


def test_registry_consistency() -> None:
    check("HTML_TEMPLATES has 27 entries", len(HTML_TEMPLATES) == 27,
          f"got {len(HTML_TEMPLATES)}")
    check("SCREEN_TARGETS has 3 entries", len(SCREEN_TARGETS) == 3,
          f"got {len(SCREEN_TARGETS)}")
    check("build_targets matches HTML_TEMPLATES key set",
          set(build_targets()) == set(HTML_TEMPLATES))
    check("screen_targets matches SCREEN_TARGETS key set",
          set(screen_targets()) == set(SCREEN_TARGETS))
    check("HTML_TARGETS in build.py matches build_targets()",
          dict(HTML_TARGETS) == build_targets())
    check("DIAGRAM_TARGETS has 18 entries", len(DIAGRAM_TARGETS) == 18,
          f"got {len(DIAGRAM_TARGETS)}")
    check("DIAGRAM_TARGETS in build.py matches shared.diagram_targets()",
          dict(DIAGRAM_TARGETS) == diagram_targets() == dict(DIAGRAM_TEMPLATES))
    check("PPTX_TARGETS has 2 entries", len(PPTX_TARGETS) == 2,
          f"got {len(PPTX_TARGETS)}")
    check("PPTX_TARGETS in build.py matches shared.pptx_targets()",
          dict(PPTX_TARGETS) == pptx_targets())
    registered_sources = {
        **{f"html:{name}": TEMPLATES / spec.source
           for name, spec in HTML_TEMPLATES.items()},
        **{f"screen:{name}": TEMPLATES / source
           for name, source in SCREEN_TEMPLATES.items()},
        **{f"pptx:{name}": TEMPLATES / source
           for name, source in pptx_targets().items()},
        **{f"diagram:{name}": DIAGRAMS / source
           for name, source in DIAGRAM_TEMPLATES.items()},
        **{f"marp:{name}": TEMPLATES / source
           for name, source in MARP_TEMPLATES.items()},
    }
    missing_sources = sorted(
        f"{name} -> {path.relative_to(REPO_ROOT)}"
        for name, path in registered_sources.items()
        if not path.is_file()
    )
    check("every registered template source exists",
          missing_sources == [], ", ".join(missing_sources))
    check("Marp registry maps authoring entries with matching CSS",
          marp_targets() == MARP_TEMPLATES
          and all(
              (TEMPLATES / source).exists()
              and (TEMPLATES / source).with_suffix(".css").exists()
              for source in MARP_TEMPLATES.values()
          ),
          str(MARP_TEMPLATES))
    check("PARCHMENT_RGB is canonical", PARCHMENT_RGB == (0xF5, 0xF4, 0xED))


def test_ci_builds_registered_hard_page_and_pptx_targets() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "check.yml").read_text(
        encoding="utf-8")
    check("CI installs the editable PPTX runtime dependency",
          "python-pptx" in workflow)
    check("CI derives hard-page verification from the shared registry",
          "from shared import HTML_TEMPLATES" in workflow
          and "if spec.build_max_pages" in workflow)
    check("CI verifies both editable PPTX targets",
          "--verify slides\n" in workflow and "--verify slides-en" in workflow)


def test_public_document_kinds_derive_new_registry_entries() -> None:
    from shared import TemplateSpec, public_document_template_kinds

    shared_mod.HTML_TEMPLATES["invoice"] = TemplateSpec("invoice.html", 1)
    try:
        kinds = public_document_template_kinds()
    finally:
        shared_mod.HTML_TEMPLATES.pop("invoice", None)
    check("new registry kinds cannot disappear behind the public-kind allowlist",
          "invoice" in kinds,
          str(sorted(kinds)))


def test_threshold_fallback_includes_resume_balance() -> None:
    original = shared_mod.CHECKS_THRESHOLDS_FILE
    with tempfile.TemporaryDirectory() as d:
        shared_mod.CHECKS_THRESHOLDS_FILE = Path(d) / "missing-thresholds.json"
        shared_mod.load_checks_thresholds.cache_clear()
        try:
            resume = shared_mod.load_checks_thresholds().get("resume_balance")
        finally:
            shared_mod.CHECKS_THRESHOLDS_FILE = original
            shared_mod.load_checks_thresholds.cache_clear()
    check("threshold fallback keeps the resume balance contract",
          resume == {
              "min_fill_pct": 0.83,
              "max_fill_pct": 0.95,
              "max_gap_pct": 0.12,
              "dpi": 36,
          },
          repr(resume))


def test_checkout_detection_does_not_depend_on_site_presence() -> None:
    """A missing site must not turn an incomplete checkout into an installed skill."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d).resolve()
        module_path = root / "skills" / "kami" / "scripts" / "shared.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text(Path(shared_mod.__file__).read_text(encoding="utf-8"), encoding="utf-8")
        marker = root / "scripts" / "package-skill.sh"
        marker.parent.mkdir()
        marker.write_text("#!/bin/sh\n", encoding="utf-8")

        def load():
            spec = importlib.util.spec_from_file_location("shared_layout_fixture", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        checkout = load()
        check("checkout keeps its site boundary when the site directory is missing",
              checkout.REPO_ROOT == root and checkout.SITE_ROOT == root / "site")
        marker.unlink()
        installed = load()
        check("standalone installed skill has no repository or site boundary",
              installed.REPO_ROOT is None and installed.SITE_ROOT is None)


def test_runner_auto_discovers_tests() -> None:
    names = [name for name, _ in _test_functions()]
    check("test runner auto-discovers Codex update command test",
          "test_check_update_uses_codex_plugin_update_command" in names)
    check("test runner auto-discovers this test",
          "test_runner_auto_discovers_tests" in names)


def test_build_cli_rejects_unexpected_flags() -> None:
    rc, out = run_build_args(["resume", "--verify"])
    check("build.py rejects flags after target",
          rc == 2 and "ERROR: unexpected argument: --verify" in out,
          out.strip())

    rc, out = run_build_args(["--check-density", "-v"])
    check("build.py rejects unknown flags for path-based checks",
          rc == 2 and "ERROR: unexpected argument: -v" in out,
          out.strip())

    rc, out = run_build_args(["--verify", "-v"])
    check("build.py rejects unknown --verify flags",
          rc == 2 and "ERROR: unexpected argument: -v" in out,
          out.strip())

    rc, out = run_build_args(["--check-markdown", "-v"])
    check("build.py rejects unknown --check-markdown flags",
          rc == 2 and "ERROR: unexpected argument: -v" in out,
          out.strip())


def test_ci_required_skip_is_a_failure_not_a_pass() -> None:
    """A missing heavy dependency in CI must turn the suite red."""
    original_fail, original_skip = support._FAIL, support._SKIP
    original_ci = os.environ.get("CI")
    try:
        os.environ["CI"] = "1"
        silently(skip, "negative-control fixture", ci_required=True)
        rejected = support._FAIL == original_fail + 1 and support._SKIP == original_skip + 1
    finally:
        support._FAIL, support._SKIP = original_fail, original_skip
        if original_ci is None:
            os.environ.pop("CI", None)
        else:
            os.environ["CI"] = original_ci
    check("CI-required skip increments failure and skip counters", rejected)


def test_build_cli_dispatches_new_checks() -> None:
    rc, out = run_build_args(["--check-content"])
    check("build.py --check-content without args is a usage error",
          rc == 2 and "usage" in out, out.strip()[:120])
    rc, out = run_build_args(["--check-visual"])
    check("build.py --check-visual without args is a usage error",
          rc == 2 and "usage" in out, out.strip()[:120])
    rc, out = run_build_args(["--doctor"])
    check("build.py --doctor reports capability status",
          rc in {0, 1} and "Kami doctor" in out
          and "visual verification" in out,
          out.strip()[:300])


def _test_functions():
    """Discover every sibling suite and this entry point without a manual test list."""
    modules = [sys.modules[__name__]]
    modules.extend(
        importlib.import_module(path.stem)
        for path in sorted(Path(__file__).parent.glob("test_*.py"))
        if path.stem != "test_build"
    )
    tests = []
    names = set()
    for module in modules:
        for name, func in vars(module).items():
            if not name.startswith("test_") or not callable(func):
                continue
            if getattr(func, "__module__", None) != module.__name__:
                continue
            if name in names:
                raise ValueError(f"duplicate test name: {name}")
            names.add(name)
            tests.append((name, func))
    return tests


def main() -> int:
    for name, func in _test_functions():
        signature = inspect.signature(func)
        if signature.parameters:
            params = ", ".join(signature.parameters)
            check(f"{name} has no parameters", False, f"parameters: {params}")
            continue
        func()
    print()
    print(f"Passed: {support._PASS} | Skipped: {support._SKIP} | Failed: {support._FAIL}")
    return 0 if support._FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
