"""Distribution, metadata, update, and release contract tests."""
from __future__ import annotations

from support import REPO_ROOT, SKILL_ROOT, check, skip

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
import zipfile
from pathlib import Path


PACKAGE_MAX_BYTES = 6_000_000


PACKAGE_ROOT_NAME = "kami"


PACKAGE_FORBIDDEN_EXACT = {
    ".claude-plugin/marketplace.json",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "assets/images/1.png",
    "assets/images/2.png",
    "assets/images/3.png",
    "assets/fonts/TsangerJinKai02-W04.ttf",
    "assets/fonts/TsangerJinKai02-W05.ttf",
    "assets/fonts/SourceHanSerifKR-Regular.otf",
    "assets/fonts/SourceHanSerifKR-Medium.otf",
    "index.html",
    "index-en.html",
    "index-ja.html",
    "index-ko.html",
    "index-tw.html",
    "index-zh.html",
    "llms.txt",
    "robots.txt",
    "scripts/build_metadata.py",
    "scripts/draft-release-notes.py",
    "scripts/package-skill.sh",
    "sitemap.xml",
    "styles.css",
    "vercel.json",
}


PACKAGE_FORBIDDEN_PREFIXES = (
    ".agents/",
    ".claude/",
    ".github/",
    "assets/demos/",
    "assets/examples/",
    "assets/illustrations/",
    "assets/showcase/",
    "plugins/",
    "scripts/tests/",
)


PACKAGE_REQUIRED_ENTRIES = {
    "SKILL.md",
    "CHEATSHEET.md",
    "VERSION",
    "LICENSE",
    "assets/images/logo.svg",
    "assets/fonts/JetBrainsMono.woff2",
    "assets/fonts/LICENSE-JetBrainsMono.txt",
    "assets/templates/resume.html",
    "assets/templates/landing-page.html",
    "assets/diagrams/sequence.html",
    "references/design.md",
    "scripts/build.py",
    "scripts/ensure-fonts.sh",
    "scripts/ensure_mathjax.sh",
    "scripts/math_render.py",
    "scripts/mathjax_svg.js",
    "scripts/package.json",
    "scripts/mathjax-runtime/package.json",
    "scripts/mathjax-runtime/package-lock.json",
    "scripts/site_facts.py",
    "scripts/html_visibility.py",
}


def test_render_examples_are_ignored_and_untracked() -> None:
    """A clean build must not add placeholder PDFs or decks to source control."""
    tracked = subprocess.run(
        ["git", "ls-files", "--", "skills/kami/assets/examples/"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    check("render examples are not tracked", not tracked.stdout.strip(), tracked.stdout)
    for path in ("skills/kami/assets/examples/resume.pdf", "skills/kami/assets/examples/slides.pptx"):
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", path], cwd=REPO_ROOT,
        )
        check(f"generated output is ignored: {path}", result.returncode == 0)
    source = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "skills/kami/assets/templates/resume.html"],
        cwd=REPO_ROOT,
    )
    check("template source remains trackable", source.returncode == 1)


def test_dist_package_contents() -> None:
    """Build the archive the way the release workflow does and audit it.

    dist/kami.zip is no longer tracked: CI packages from skills/kami at release
    time and uploads the result, so the audit runs on a fresh candidate.
    """
    script = REPO_ROOT / "scripts" / "package-skill.sh"
    with tempfile.TemporaryDirectory() as d:
        archive = Path(d) / "kami.zip"
        r = subprocess.run(["bash", str(script), str(archive)], capture_output=True, text=True, cwd=REPO_ROOT)
        check("package-skill.sh builds a candidate archive", r.returncode == 0 and archive.exists(), r.stderr[-800:])
        if not archive.exists():
            return

        size_bytes = archive.stat().st_size
        check("kami.zip stays below 6MB",
              size_bytes <= PACKAGE_MAX_BYTES,
              f"{size_bytes} bytes > {PACKAGE_MAX_BYTES} bytes")

        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())

        bad_root = sorted(name for name in names if not name.startswith(f"{PACKAGE_ROOT_NAME}/"))
        check("kami.zip uses a Claude-friendly top-level skill folder",
              not bad_root,
              f"entries outside {PACKAGE_ROOT_NAME}/: {', '.join(bad_root)}")

        payload_names = {
            name.removeprefix(f"{PACKAGE_ROOT_NAME}/")
            for name in names
            if name.startswith(f"{PACKAGE_ROOT_NAME}/")
        }
        forbidden = sorted(
            name for name in payload_names
            if name.startswith(PACKAGE_FORBIDDEN_PREFIXES)
            or name in PACKAGE_FORBIDDEN_EXACT
        )
        check("kami.zip excludes site, CI, tests, demos, generated mirrors, and large bundled fonts",
              not forbidden,
              f"forbidden entries: {', '.join(forbidden)}")
        missing_required = sorted(PACKAGE_REQUIRED_ENTRIES - payload_names)
        check("kami.zip keeps required runtime skill files",
              not missing_required,
              f"missing entries: {', '.join(missing_required)}")

        stale: list[str] = []
        absent: list[str] = []
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                source = SKILL_ROOT / name.removeprefix(f"{PACKAGE_ROOT_NAME}/")
                if not source.exists():
                    absent.append(name)
                    continue
                if hashlib.sha256(zf.read(name)).digest() != hashlib.sha256(source.read_bytes()).digest():
                    stale.append(name)
        check("kami.zip matches skills/kami byte for byte", not stale,
              f"{len(stale)} stale entr(ies): {', '.join(sorted(stale)[:5])}")
        check("kami.zip carries no entry missing from skills/kami", not absent,
              f"entries with no source: {', '.join(sorted(absent)[:5])}")


def test_package_failure_preserves_last_good_archive() -> None:
    """A failed audit must not replace the last archive users can install."""
    script = REPO_ROOT / "scripts" / "package-skill.sh"
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        out = root / "kami.zip"
        out.write_bytes(b"last-good")
        env = dict(os.environ, KAMI_PACKAGE_MAX_BYTES="1")
        result = subprocess.run(
            ["bash", str(script), str(out)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        leftovers = list(root.glob(".kami-package.*"))
        check("failed package audit preserves the last good archive",
              result.returncode == 1 and out.read_bytes() == b"last-good",
              (result.stdout + result.stderr).strip())
        check("failed package audit removes its candidate directory",
              leftovers == [], str(leftovers))


def test_plugin_metadata_generated() -> None:
    """Claude Code / Codex marketplaces and plugin mirrors must stay generated."""
    script = REPO_ROOT / "scripts" / "build_metadata.py"
    check("build_metadata.py exists", script.exists(), f"missing {script}")
    if not script.exists():
        return

    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    detail = (result.stdout + result.stderr).strip()
    check("plugin metadata matches generator", result.returncode == 0, detail)


def test_claude_plugin_marketplace_version_matches_version_file() -> None:
    """Claude Code uses this version instead of falling back to a commit hash."""
    version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    marketplace_file = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    check("Claude plugin marketplace metadata exists", marketplace_file.exists())
    if not marketplace_file.exists():
        return

    marketplace = json.loads(marketplace_file.read_text(encoding="utf-8"))
    plugins = marketplace.get("plugins", [])
    kami_plugin = next((plugin for plugin in plugins if plugin.get("name") == "kami"), None)
    check("Claude plugin marketplace includes kami", kami_plugin is not None)
    if not kami_plugin:
        return

    check("Claude plugin marketplace version matches VERSION",
          kami_plugin.get("version") == version,
          f"marketplace={kami_plugin.get('version')!r}, VERSION={version!r}")
    check("Claude plugin marketplace installs the lightweight plugin directory",
          kami_plugin.get("source") == "./plugins/kami",
          f"source={kami_plugin.get('source')!r}")

    plugin_file = REPO_ROOT / "plugins" / "kami" / ".claude-plugin" / "plugin.json"
    check("Claude plugin manifest exists in generated plugin tree", plugin_file.exists())
    if not plugin_file.exists():
        return

    plugin = json.loads(plugin_file.read_text(encoding="utf-8"))
    check("Claude plugin manifest version matches VERSION",
          plugin.get("version") == version,
          f"plugin={plugin.get('version')!r}, VERSION={version!r}")
    check("Claude plugin manifest exposes skills directory",
          plugin.get("skills") == "./skills/",
          f"skills={plugin.get('skills')!r}")


def test_build_metadata_reads_tokens_from_root_argument() -> None:
    from build_metadata import build_codex_plugin, read_token_value

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "references").mkdir()
        (root / "references" / "tokens.json").write_text('{"--brand":"#123456"}\n', encoding="utf-8")

        brand_color = read_token_value(root, "brand")
        plugin = build_codex_plugin("9.9.9", brand_color)
        check("build_metadata reads brand token from provided root",
              plugin["interface"]["brandColor"] == "#123456",
              f"brandColor={plugin['interface']['brandColor']}")


def test_catalog_lists_pptx_for_slides() -> None:
    from build_metadata import build_catalog_feed

    catalog = json.loads(build_catalog_feed(SKILL_ROOT))
    slide = next(
        entry["item"]
        for entry in catalog["itemListElement"]
        if entry["item"].get("identifier") == "slides"
    )
    pptx_mime = (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    check("catalog advertises the editable PPTX slide format",
          pptx_mime in slide.get("encodingFormat", []),
          str(slide.get("encodingFormat")))


def test_catalog_lists_every_public_document_template() -> None:
    from build_metadata import DOCUMENT_TEMPLATE_NOTES, build_catalog_feed
    from shared import public_document_template_kinds

    catalog = json.loads(build_catalog_feed(SKILL_ROOT))
    listed = {entry["item"].get("identifier") for entry in catalog["itemListElement"]}
    kinds = public_document_template_kinds()
    check("the catalog notes every public document template",
          set(DOCUMENT_TEMPLATE_NOTES) == kinds,
          f"missing={sorted(kinds - set(DOCUMENT_TEMPLATE_NOTES))} "
          f"extra={sorted(set(DOCUMENT_TEMPLATE_NOTES) - kinds)}")
    check("the catalog feed lists every public document template",
          kinds <= listed, str(sorted(kinds - listed)))


def test_site_schema_count_matches_the_schemas() -> None:
    from shared import content_schema_types
    from site_facts import _schema_counts

    count = len(content_schema_types())
    check("schema count sentences are read",
          _schema_counts("ships nine JSON content schemas. Ten schemas live under") == [9, 10])
    check("a page stating a stale schema count is caught",
          count not in _schema_counts(f"ships {count - 1} content schemas"))


def test_readme_locales_state_the_template_count() -> None:
    from site_facts import _readme_template_counts, readme_count_issues

    stale = ["内置 8 种文档模板", "內建 8 種文件範本", "inklusive acht Dokumentvorlagen",
             "avec huit modèles de documents", "with eight built-in document templates",
             "8 種類の文書テンプレート", "8종의 문서 템플릿"]
    check("every locale's template count sentence is read",
          all(_readme_template_counts(t) == [8] for t in stale),
          str({t: _readme_template_counts(t) for t in stale}))
    check("every README locale states the registry's template count", not readme_count_issues(),
          str(readme_count_issues()))


def test_check_update_script() -> None:
    """check-update.sh notifies on a newer remote, stays silent when current,
    throttles through a local cache marker, and fails silently offline. It GETs
    only a version file and uploads no document/task content; KAMI_UPDATE_URL
    points it at a fixture."""
    script = SKILL_ROOT / "scripts" / "check-update.sh"
    check("check-update.sh exists", script.exists())
    if not script.exists():
        return
    if shutil.which("bash") is None or shutil.which("curl") is None:
        skip("check-update.sh behavior", "bash/curl unavailable", ci_required=True)
        return
    local_ver = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    def run(cache: str, url: str) -> tuple[int, str]:
        env = dict(os.environ, XDG_CACHE_HOME=cache, KAMI_UPDATE_URL=url)
        r = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env)
        return r.returncode, r.stdout.strip()

    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        newer = dp / "newer"; newer.write_text("9.9.9\n")
        same = dp / "same"; same.write_text(local_ver + "\n")

        rc, out = run(str(dp / "c1"), newer.as_uri())
        check("check-update notifies on a newer remote", rc == 0 and "9.9.9" in out, out)
        check("check-update default command uses plugin bundle path",
              "npx skills add tw93/kami -a claude-code codex cursor -g -y" in out and "skills update" not in out,
              out)

        rc, out = run(str(dp / "c2"), same.as_uri())
        check("check-update is silent when current", rc == 0 and out == "", out)

        c3 = str(dp / "c3")
        run(c3, newer.as_uri())
        _, out2 = run(c3, newer.as_uri())
        check("check-update throttles to once per day", out2 == "", out2)

        rc, out = run(str(dp / "c4"), (dp / "nope").as_uri())
        check("check-update fails silently when offline", rc == 0 and out == "", out)

        no_home_env = dict(os.environ, KAMI_UPDATE_URL=newer.as_uri())
        no_home_env.pop("HOME", None)
        no_home_env.pop("XDG_CACHE_HOME", None)
        result = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, env=no_home_env)
        check("check-update is silent without a cache home",
              result.returncode == 0 and result.stdout == "" and result.stderr == "",
              result.stdout + result.stderr)

        unwritable_cache_env = dict(
            os.environ,
            XDG_CACHE_HOME="/dev/null",
            KAMI_UPDATE_URL=newer.as_uri(),
        )
        result = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, env=unwritable_cache_env)
        check("check-update is silent when the cache root is unusable",
              result.returncode == 0 and result.stdout == "" and result.stderr == "",
              result.stdout + result.stderr)


def test_check_update_defaults_to_latest_published_release() -> None:
    script = SKILL_ROOT / "scripts" / "check-update.sh"
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        fake_curl = bin_dir / "curl"
        fake_curl.write_text(
            "#!/usr/bin/env bash\n"
            "case \" $* \" in\n"
            "  *\" https://github.com/tw93/Kami/releases/latest \"*)\n"
            "    printf '%s' 'https://github.com/tw93/Kami/releases/tag/V9.9.9'\n"
            "    ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_curl.chmod(0o755)
        env = dict(
            os.environ,
            XDG_CACHE_HOME=str(root / "cache"),
            PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        )
        env.pop("KAMI_UPDATE_URL", None)
        result = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, env=env)
        check("check-update defaults to GitHub's latest published release tag",
              result.returncode == 0 and "Kami 9.9.9 is available" in result.stdout,
              result.stdout + result.stderr)


def test_check_update_uses_codex_plugin_update_command() -> None:
    """When installed through Codex plugin cache, the update hint should use
    plugin marketplace refresh commands instead of the legacy npx skill update.
    """
    script = SKILL_ROOT / "scripts" / "check-update.sh"
    check("check-update.sh exists for Codex command test", script.exists())
    if not script.exists():
        return
    if shutil.which("bash") is None or shutil.which("curl") is None:
        skip("check-update Codex command", "bash/curl unavailable", ci_required=True)
        return

    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        newer = dp / "newer"
        newer.write_text("9.9.9\n")

        roots = [
            dp / ".codex" / "plugins" / "cache" / "kami" / "kami" / "1.7.4" / "skills" / "kami",
            dp / "custom-codex-home" / "plugins" / "cache" / "kami" / "kami" / "1.7.4" / "skills" / "kami",
        ]
        for index, install_root in enumerate(roots, start=1):
            (install_root / "scripts").mkdir(parents=True)
            shutil.copy2(script, install_root / "scripts" / "check-update.sh")
            (install_root / "VERSION").write_text("1.7.4\n")

            env = dict(os.environ, XDG_CACHE_HOME=str(dp / f"cache-{index}"), KAMI_UPDATE_URL=newer.as_uri())
            result = subprocess.run(
                ["bash", str(install_root / "scripts" / "check-update.sh")],
                capture_output=True,
                text=True,
                env=env,
            )
            out = result.stdout.strip()
            check(f"check-update uses Codex plugin update command ({install_root.parent.parent.parent.name})",
                  result.returncode == 0 and "codex plugin marketplace upgrade kami" in out,
                  out)


def test_check_update_uses_claude_plugin_update_command() -> None:
    """When installed through Claude Code's plugin cache, the update hint should
    use Claude's plugin updater instead of generic npx skill install.
    """
    script = SKILL_ROOT / "scripts" / "check-update.sh"
    check("check-update.sh exists for Claude command test", script.exists())
    if not script.exists():
        return
    if shutil.which("bash") is None or shutil.which("curl") is None:
        skip("check-update Claude command", "bash/curl unavailable", ci_required=True)
        return

    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        newer = dp / "newer"
        newer.write_text("9.9.9\n")
        install_root = dp / ".claude" / "plugins" / "cache" / "kami" / "kami" / "1.9.1" / "skills" / "kami"
        (install_root / "scripts").mkdir(parents=True)
        shutil.copy2(script, install_root / "scripts" / "check-update.sh")
        (install_root / "VERSION").write_text("1.9.1\n")

        env = dict(os.environ, XDG_CACHE_HOME=str(dp / "cache"), KAMI_UPDATE_URL=newer.as_uri())
        result = subprocess.run(
            ["bash", str(install_root / "scripts" / "check-update.sh")],
            capture_output=True,
            text=True,
            env=env,
        )
        out = result.stdout.strip()
        check("check-update uses Claude plugin update command",
              result.returncode == 0 and "claude plugin update kami" in out and "npx skills" not in out,
              out)


def test_release_gate_rejects_identity_mismatches() -> None:
    from release_gate import release_identity_issues

    good = release_identity_issues("V1.2.3", "1.2.3", "same", "same")
    wrong_tag = release_identity_issues("V1.2.4", "1.2.3", "same", "same")
    wrong_sha = release_identity_issues("V1.2.3", "1.2.3", "head", "tag")
    check("release identity accepts an exact tag, version, and SHA", good == [], str(good))
    check("release identity rejects a tag/version mismatch",
          any("does not match VERSION" in issue for issue in wrong_tag), str(wrong_tag))
    check("release identity rejects a tag/checkout SHA mismatch",
          any("does not match checkout HEAD" in issue for issue in wrong_sha), str(wrong_sha))


def test_release_gate_resolves_only_the_tag_namespace() -> None:
    import release_gate as release_gate_mod

    calls = []
    original_git = release_gate_mod._git
    try:
        release_gate_mod._git = lambda *args: calls.append(args) or "tag-sha"
        resolved = release_gate_mod.resolve_tag_commit("V1.2.3")
    finally:
        release_gate_mod._git = original_git
    check("release gate cannot resolve a same-named branch as a tag",
          resolved == "tag-sha"
          and calls == [("rev-parse", "--verify", "refs/tags/V1.2.3^{commit}")],
          str(calls))


def test_release_gate_requires_main_push_provenance() -> None:
    from release_gate import check_run_issues

    pr_run = [{
        "headSha": "candidate",
        "headBranch": "feature/release",
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
    }]
    main_run = [{
        "headSha": "candidate",
        "headBranch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }]
    check("release gate rejects successful PR-only checks",
          bool(check_run_issues(pr_run, "candidate")), str(pr_run))
    check("release gate accepts exact-SHA checks from a main push",
          check_run_issues(main_run, "candidate") == [], str(main_run))


def test_release_gate_requires_mainline_reachability() -> None:
    import release_gate as release_gate_mod

    original_git = release_gate_mod._git
    original_run = release_gate_mod.subprocess.run
    try:
        release_gate_mod._git = lambda *args: "main-sha"
        release_gate_mod.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="")
        issues = release_gate_mod.mainline_issues("tag-sha", "origin/main")
    finally:
        release_gate_mod._git = original_git
        release_gate_mod.subprocess.run = original_run
    check("release gate rejects commits outside origin/main",
          len(issues) == 1 and "not reachable from origin/main" in issues[0],
          str(issues))


def test_release_gate_compares_zip_payloads_not_container_bytes() -> None:
    from release_gate import archive_payload_issues

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        tracked = root / "tracked.zip"
        equivalent = root / "equivalent.zip"
        changed = root / "changed.zip"
        duplicated = root / "duplicated.zip"
        with zipfile.ZipFile(tracked, "w") as archive:
            archive.writestr("kami/VERSION", "1.2.3")
        with zipfile.ZipFile(equivalent, "w") as archive:
            info = zipfile.ZipInfo("kami/VERSION", date_time=(2026, 1, 2, 3, 4, 6))
            archive.writestr(info, "1.2.3")
        with zipfile.ZipFile(changed, "w") as archive:
            archive.writestr("kami/VERSION", "1.2.4")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(duplicated, "w") as archive:
                archive.writestr("kami/VERSION", "first")
                archive.writestr("kami/VERSION", "second")

        same_issues = archive_payload_issues(tracked, equivalent)
        changed_issues = archive_payload_issues(tracked, changed)
        duplicate_issues = archive_payload_issues(duplicated, tracked)
        check("release gate ignores ZIP container timestamp differences",
              tracked.read_bytes() != equivalent.read_bytes() and same_issues == [],
              str(same_issues))
        check("release gate rejects changed entry payloads",
              changed_issues == ["candidate payload differs: kami/VERSION"],
              str(changed_issues))
        check("release gate rejects duplicate ZIP entry names",
              len(duplicate_issues) == 1
              and "duplicate ZIP entry: kami/VERSION" in duplicate_issues[0],
              str(duplicate_issues))


def test_release_workflow_reads_back_required_reactions() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8")
    expected = ("+1", "eyes", "heart", "hooray", "laugh", "rocket")
    check("release workflow reads reactions back after posting",
          "gh api --paginate" in workflow
          and "release reactions missing" in workflow
          and all(workflow.count(reaction) >= 2 for reaction in expected),
          "release workflow lacks a final reaction-set assertion")


def test_release_workflow_preserves_published_version_payloads() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8")
    check("release workflow requires main push provenance",
          "--json headSha,headBranch,event,status,conclusion" in workflow
          and "--main-ref origin/main" in workflow
          and "--checks-json /tmp/kami-check-runs.json" in workflow,
          "release workflow can accept non-main CI")
    check("release workflow refuses same-version payload replacement",
          "--clobber" not in workflow
          and "gh release download" in workflow
          and "existing kami.zip already matches this release" in workflow,
          "release workflow can overwrite a published archive")


def test_release_note_help_matches_placeholder_flow() -> None:
    draft = (REPO_ROOT / "scripts" / "draft-release-notes.py").read_text(
        encoding="utf-8")
    release_doc = (REPO_ROOT / "docs" / "release.md").read_text(encoding="utf-8")
    check("release-note help edits the workflow-created placeholder",
          "gh release edit --notes-file" in draft
          and "gh release create --notes-file" not in draft
          and '"--match", "V[0-9]*.[0-9]*.[0-9]*"' in draft
          and "V<prev>..HEAD" in release_doc
          and "let CI create the placeholder" in release_doc,
          "draft-release-notes.py and docs/release.md disagree")


def test_release_note_scaffold_matches_published_shape() -> None:
    """The scaffold keeps the fixed subtitle, current tagline, and a Thanks slot."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "draft_release_notes", REPO_ROOT / "scripts" / "draft-release-notes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = module.parse_args(["draft", "V1.0.0..HEAD"])
    out = module.render(
        version="V9.9.9", title="Test", subtitle_en=args.subtitle_en,
        rev_range="V1.0.0..HEAD", commits=[("abc1234", "fix: sample")])
    check("release-note scaffold uses the fixed subtitle",
          "<em>Good content deserves good paper.</em>" in out, out[:400])
    check("release-note scaffold closes with Thanks then the current tagline",
          "### Thanks" in out
          and out.index("### Thanks") < out.index("> Kami helps AI agents create clear, consistent professional documents.")
          and "quiet design system" not in out,
          out[-400:])


def test_plugin_mirror_follows_tracked_files() -> None:
    """Like package-skill.sh, the plugin mirror skips untracked files in a checkout."""
    from build_metadata import skill_source_files

    if shutil.which("git") is None:
        skip("plugin mirror follows git ls-files", "git unavailable", ci_required=True)
        return
    with tempfile.TemporaryDirectory() as d:
        skill = Path(d) / "skills" / "kami"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("x\n", encoding="utf-8")
        (skill / "scratch.txt").write_text("x\n", encoding="utf-8")
        outside = {p.name for p in skill_source_files(skill)}
        subprocess.run(["git", "init", "-q", d], check=True)
        subprocess.run(["git", "-C", d, "add", "skills/kami/SKILL.md"], check=True)
        inside = {p.name for p in skill_source_files(skill)}
    check("plugin mirror walks the disk outside git",
          outside == {"SKILL.md", "scratch.txt"}, str(sorted(outside)))
    check("plugin mirror drops untracked files inside git",
          inside == {"SKILL.md"}, str(sorted(inside)))


def test_mcp_server_card_install_path_matches_developer_docs() -> None:
    from build_metadata import build_mcp_server_card

    card = build_mcp_server_card("0.0.0", "2025-06-18", [])
    install = card["packages"][0]["install"]
    developers = (REPO_ROOT / "site" / "developers.md").read_text(encoding="utf-8")
    check("MCP server card install path matches developers.md",
          "<checkout>/skills/kami/scripts/mcp_server.py" in install
          and "<checkout>/skills/kami/scripts/mcp_server.py" in developers,
          install)
