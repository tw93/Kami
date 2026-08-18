"""Content IR checks: schema validation and content-to-HTML coverage.

The content IR is a JSON file the agent writes before filling a template:

    {"type": "resume", "lang": "cn", "brief": {...}, "content": {...}}

`type` selects a contract from `references/schemas/<type>.json` (a lean JSON
Schema subset). Validation happens before layout, so structural defects
(too few metric cards, missing impact rows, an over-long tagline) are caught
as data problems instead of surfacing later as sparse or overflowing pages.

The coverage check runs after filling: every short atomic value from the
content file must appear in the filled HTML's visible text, which catches
silently dropped facts. Long prose fields are exempt because filling is
editorial, not verbatim.
"""
from __future__ import annotations

import json
import posixpath
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from checks import (
    _HtmlVisibilityParser,
    _css_hidden_filters,
    _document_custom_properties,
    visible_html_evidence,
    visible_html_text,
)
from shared import (
    HTML_TEMPLATES,
    MARP_TEMPLATES,
    PPTX_TEMPLATES,
    ROOT,
    SCHEMAS_DIR,
    SCREEN_TEMPLATES,
    content_schema_types,
    rel_to_root,
)

# Strings longer than this are treated as prose the agent may rephrase while
# filling; only shorter atomic values (names, metrics, dates) must survive
# verbatim into the rendered document.
COVERAGE_MAX_LEN = 80
MAX_COVERAGE_VALUES = 5000
MAX_COVERAGE_ISSUES = 200

_CJK = re.compile(r"[\u3000-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")
_LANG_TAG = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
_ENVELOPE_FIELDS = {"type", "lang", "brief", "content"}

_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}

BRIEF_SCHEMA = {
    "type": "object",
    "required": ["audience", "job", "template", "formats", "acceptance_checks"],
    "additionalProperties": False,
    "properties": {
        "audience": {"type": "string", "minLength": 1, "maxLength": 240},
        "job": {"type": "string", "minLength": 1, "maxLength": 240},
        "template": {"type": "string", "minLength": 1, "maxLength": 80},
        "formats": {
            "type": "array", "minItems": 1, "maxItems": 4,
            "items": {
                "type": "string",
                "enum": ["html", "md", "pdf", "pptx", "png"],
            },
        },
        "page_target": {"type": "integer", "minimum": 1, "maximum": 200},
        "length_target": {"type": "string", "minLength": 1, "maxLength": 120},
        "narrative": {"type": "string", "minLength": 1, "maxLength": 800},
        "required_facts": {
            "type": "array", "maxItems": 100,
            "items": {"type": "string", "minLength": 1, "maxLength": 240},
        },
        "required_assets": {
            "type": "array", "maxItems": 100,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "acceptance_checks": {
            "type": "array", "minItems": 1, "maxItems": 100,
            "items": {"type": "string", "minLength": 1, "maxLength": 240},
        },
        "target": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "surface": {"type": "string", "minLength": 1, "maxLength": 120},
                "page": {"type": "integer", "minimum": 1, "maximum": 200},
                "viewport": {"type": "string", "minLength": 1, "maxLength": 80},
                "state": {"type": "string", "minLength": 1, "maxLength": 120},
                "element": {"type": "string", "minLength": 1, "maxLength": 160},
            },
        },
        "preserve": {
            "type": "array", "maxItems": 100,
            "items": {"type": "string", "minLength": 1, "maxLength": 240},
        },
        "evidence": {
            "type": "array", "maxItems": 100,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "explicit_deviations": {
            "type": "array", "maxItems": 100,
            "items": {"type": "string", "minLength": 1, "maxLength": 240},
        },
    },
}


class _HtmlAttributeParser(_HtmlVisibilityParser):
    """Collect resource-bearing HTML attributes for asset coverage checks."""

    _RESOURCE_ATTRS = {
        "audio": {"src"},
        "image": {"href"},
        "img": {"src", "srcset"},
        "source": {"src", "srcset"},
        "use": {"href"},
        "video": {"poster", "src"},
    }
    _SKIP_TAGS = {
        "clippath", "defs", "head", "mask", "metadata", "noembed", "noframes",
        "noscript", "pattern", "rp", "script", "style", "symbol", "template",
    }

    def __init__(
        self,
        hidden_classes: set[str],
        hidden_ids: set[str],
        hidden_tags: set[str],
        hidden_attrs: set[tuple[str, str | None]],
        ambiguous_classes: set[str],
        ambiguous_ids: set[str],
        ambiguous_tags: set[str],
        ambiguous_attrs: set[tuple[str, str | None]],
        visibility_ambiguous: bool,
        *,
        custom_properties: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            hidden_classes,
            hidden_ids,
            hidden_tags,
            hidden_attrs,
            ambiguous_classes,
            ambiguous_ids,
            ambiguous_tags,
            ambiguous_attrs,
            visibility_ambiguous,
            skip_tags=self._SKIP_TAGS,
            fail_closed=True,
            custom_properties=custom_properties,
        )
        self.values: set[str] = set()
        self.base_href: str | None = None
        self.ambiguous_resources = False
        self._picture_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {name.lower(): (value or "") for name, value in attrs}
        if tag == "picture":
            self._picture_depth += 1
        if tag == "base" and self.base_href is None:
            self.base_href = next(
                (value.strip() for name, value in attrs
                 if name.lower() == "href" and value and value.strip()),
                None,
            )
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        super().handle_endtag(tag)
        if tag.lower() == "picture" and self._picture_depth:
            self._picture_depth -= 1

    def _handle_visible_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]],
    ) -> None:
        attrs_map = {name.lower(): (value or "") for name, value in attrs}
        if tag in {"picture", "source"} or attrs_map.get("srcset"):
            self.ambiguous_resources = True
        if self._picture_depth or tag == "source":
            return
        if tag == "source" and (attrs_map.get("media") or attrs_map.get("type")):
            return
        if tag in {"img", "source"} and attrs_map.get("srcset"):
            candidates = [
                part.strip().split()
                for part in attrs_map["srcset"].split(",")
                if part.strip()
            ]
            if len(candidates) == 1 and len(candidates[0]) == 1:
                self.values.add(candidates[0][0])
            return
        allowed = self._RESOURCE_ATTRS.get(tag, set())
        for name, value in attrs:
            if name.lower() not in allowed or not value:
                continue
            if name.lower() == "srcset":
                continue
            else:
                self.values.add(value.strip())

    def _handle_ambiguous_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attrs_map = {name.lower(): (value or "") for name, value in attrs}
        allowed = self._RESOURCE_ATTRS.get(tag, set())
        if any(name in attrs_map and attrs_map[name] for name in allowed):
            self._visibility_ambiguous = True
        if tag in {"picture", "source"} or attrs_map.get("srcset"):
            self.ambiguous_resources = True


def load_schema(doc_type: str) -> dict:
    path = SCHEMAS_DIR / f"{doc_type}.json"
    if not path.exists():
        known = ", ".join(content_schema_types()) or "none"
        raise FileNotFoundError(f"no schema for type {doc_type!r} (known: {known})")
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(value, expected: str) -> bool:
    py = _TYPE_CHECKS.get(expected)
    if py is None:
        return True
    if isinstance(value, bool) and expected in ("number", "integer"):
        return False
    return isinstance(value, py)


def validate_node(value, schema: dict, path: str = "content") -> list[str]:
    """Validate `value` against a JSON Schema subset; return issue strings.

    Supported keywords: type, required, properties, additionalProperties
    (False only), items, minItems, maxItems, minLength, maxLength, minimum,
    maximum, enum.
    `$comment` and `description` carry authoring guidance and are ignored.
    """
    issues: list[str] = []

    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(repr(v) for v in schema["enum"])
        issues.append(f"{path}: {value!r} not in ({allowed})")
        return issues

    expected = schema.get("type")
    if expected and not _type_ok(value, expected):
        issues.append(f"{path}: expected {expected}, got {type(value).__name__}")
        return issues

    if isinstance(value, str):
        n = len(value.strip())
        if "minLength" in schema and n < schema["minLength"]:
            issues.append(f"{path}: too short ({n} < {schema['minLength']} chars)")
        if "maxLength" in schema and n > schema["maxLength"]:
            issues.append(f"{path}: too long ({n} > {schema['maxLength']} chars)")

    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            issues.append(f"{path}: too small ({value} < {schema['minimum']})")
        if "maximum" in schema and value > schema["maximum"]:
            issues.append(f"{path}: too large ({value} > {schema['maximum']})")

    elif isinstance(value, list):
        n = len(value)
        if "minItems" in schema and n < schema["minItems"]:
            issues.append(f"{path}: too few items ({n} < {schema['minItems']})")
        if "maxItems" in schema and n > schema["maxItems"]:
            issues.append(f"{path}: too many items ({n} > {schema['maxItems']})")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                issues.extend(validate_node(item, item_schema, f"{path}[{i}]"))

    elif isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                issues.append(f"{path}: missing required field {key!r}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    issues.append(f"{path}: unknown field {key!r}")
        for key, sub in props.items():
            if key in value and isinstance(sub, dict):
                issues.extend(validate_node(value[key], sub, f"{path}.{key}"))

    return issues


def _brief_contract_issues(
    brief: dict,
    doc_type: str,
    lang: str | None = None,
) -> list[str]:
    """Cross-check the artifact brief against the selected document contract."""
    issues: list[str] = []
    if "page_target" not in brief and "length_target" not in brief:
        issues.append("brief: requires page_target or length_target")

    template_names = {
        *HTML_TEMPLATES,
        *MARP_TEMPLATES,
        *PPTX_TEMPLATES,
        *SCREEN_TEMPLATES,
    }
    template = brief.get("template")
    if not isinstance(template, str):
        return issues

    allowed_templates = {
        name for name in template_names
        if name == doc_type or name.startswith(f"{doc_type}-")
    }
    allowed_templates.add(doc_type)
    if template not in allowed_templates:
        allowed = ", ".join(sorted(allowed_templates)) or doc_type
        issues.append(
            f"brief.template: {template!r} does not match content type "
            f"{doc_type!r} (allowed: {allowed})"
        )
        return issues

    formats = brief.get("formats")
    if isinstance(formats, list):
        if template in MARP_TEMPLATES:
            supported_formats = {"html", "md", "pdf", "pptx"}
        elif doc_type == "slides":
            # A slide deliverable combines the WeasyPrint source/PDF with the
            # editable python-pptx fallback, even though `template` names the
            # primary authoring path.
            supported_formats = {"html", "pdf", "pptx", "png"}
        elif template in HTML_TEMPLATES:
            supported_formats = {"html", "pdf", "png"}
        elif template in SCREEN_TEMPLATES:
            supported_formats = {"html", "png"}
        elif template in PPTX_TEMPLATES:
            supported_formats = {"pptx"}
        else:
            supported_formats = set()
        unsupported = sorted(
            value for value in formats
            if isinstance(value, str) and value not in supported_formats
        )
        if unsupported:
            issues.append(
                f"brief.formats: template {template!r} does not support "
                f"{', '.join(unsupported)} (allowed: "
                f"{', '.join(sorted(supported_formats)) or 'none'})"
            )

    if isinstance(lang, str):
        lang_key = lang.casefold()
        if lang_key == "cn" or lang_key.startswith("zh-") or lang_key == "zh":
            requested_family = "cn"
        elif lang_key == "en" or lang_key.startswith("en-"):
            requested_family = "en"
        elif lang_key == "ko" or lang_key.startswith("ko-"):
            requested_family = "ko"
        else:
            requested_family = None
        template_family = (
            "en" if template.endswith("-en")
            else "ko" if template.endswith("-ko")
            else "cn"
        )
        korean_pptx_fallback = (
            template == "slides-en"
            and requested_family == "ko"
            and isinstance(formats, list)
            and "pptx" in formats
        )
        korean_marp_fallback = (
            template == "slides-marp"
            and requested_family == "ko"
        )
        if (
            requested_family is not None
            and requested_family != template_family
            and not korean_pptx_fallback
            and not korean_marp_fallback
        ):
            issues.append(
                f"brief.template: {template!r} is the {template_family} variant "
                f"and does not match language {lang!r}"
            )

    page_target = brief.get("page_target")
    print_spec = HTML_TEMPLATES.get(template) or HTML_TEMPLATES.get(doc_type)
    max_pages = print_spec.build_max_pages if print_spec is not None else 0
    if (
        doc_type == "resume"
        and isinstance(page_target, int)
        and not isinstance(page_target, bool)
        and page_target != 2
    ):
        issues.append(
            f"brief.page_target: resume templates require exactly 2 pages, got {page_target}"
        )
    elif (
        isinstance(page_target, int)
        and not isinstance(page_target, bool)
        and max_pages > 0
        and page_target > max_pages
    ):
        issues.append(
            f"brief.page_target: {page_target} exceeds template "
            f"{template!r} maximum {max_pages}"
        )
    return issues


def validate_content_file(data) -> tuple[str | None, list[str]]:
    """Validate a parsed content IR envelope. Returns (doc_type, issues)."""
    if not isinstance(data, dict):
        return None, ["content file must be a JSON object"]
    issues = [
        f"top-level: unknown field {key!r}"
        for key in sorted(set(data) - _ENVELOPE_FIELDS)
    ]
    lang = data.get("lang")
    if not isinstance(lang, str) or not _LANG_TAG.fullmatch(lang):
        issues.append(
            "top-level 'lang' must be a language tag such as cn, en, ko, or zh-TW"
        )
    doc_type = data.get("type")
    if not isinstance(doc_type, str) or doc_type not in content_schema_types():
        known = ", ".join(content_schema_types()) or "none"
        issues.append(f"top-level 'type' must be one of: {known}")
        return None, issues
    body = data.get("content")
    if not isinstance(body, dict):
        issues.append("top-level 'content' must be an object")
        return doc_type, issues
    brief = data.get("brief")
    if brief is not None:
        issues.extend(validate_node(brief, BRIEF_SCHEMA, "brief"))
        if isinstance(brief, dict):
            issues.extend(_brief_contract_issues(brief, doc_type, lang))
    issues.extend(validate_node(body, load_schema(doc_type)))
    return doc_type, issues


# ---------- coverage: content values must survive into the filled HTML ----------

def _normalize(text: str, *, cjk: bool) -> str:
    """Collapse whitespace; for CJK values drop it entirely.

    Filling may legitimately insert spaces between CJK and Latin runs, so
    CJK needles compare whitespace-free.
    """
    if cjk:
        return re.sub(r"\s+", "", text)
    return " ".join(text.split())


def _contains_atomic(haystack: str, needle: str) -> bool:
    """Match an atomic value without accepting it inside a larger token.

    ASCII letters and digits get explicit boundaries, so `62%` cannot pass
    against `162%` and `Ada` cannot pass against `Adams`. CJK edges stay
    unbounded because adjacent Han characters are normal sentence flow.
    """
    if not needle:
        return True
    left = r"(?<![A-Za-z0-9_])" if re.match(r"[A-Za-z0-9_]", needle[0]) else ""
    right = r"(?![A-Za-z0-9_])" if re.match(r"[A-Za-z0-9_]", needle[-1]) else ""
    return re.search(left + re.escape(needle) + right, haystack) is not None


def html_resource_evidence(raw: str) -> tuple[set[str], bool]:
    custom_properties = _document_custom_properties(raw)
    parser = _HtmlAttributeParser(
        *_css_hidden_filters(
            raw,
            fail_closed=True,
            custom_properties=custom_properties,
        ),
        custom_properties=custom_properties,
    )
    parser.feed(raw)
    if parser._ambiguous_markup:
        return set(), True
    if parser.base_href:
        values = {urljoin(parser.base_href, value) for value in parser.values}
    else:
        values = parser.values
    return values, (
        parser._visibility_ambiguous or parser.ambiguous_resources
    )


def html_resource_attributes(raw: str) -> set[str]:
    return html_resource_evidence(raw)[0]


def _asset_present(needle: str, attributes: set[str]) -> bool:
    expected_url = urlsplit(needle)
    expected_path = posixpath.normpath(unquote(expected_url.path))
    expected_is_url = bool(expected_url.scheme or expected_url.netloc)
    expected_is_absolute = expected_path.startswith("/")
    for raw in attributes:
        actual_url = urlsplit(raw)
        actual_path = posixpath.normpath(unquote(actual_url.path))
        actual_is_url = bool(actual_url.scheme or actual_url.netloc)
        if expected_is_url:
            if (
                actual_url.scheme.casefold() == expected_url.scheme.casefold()
                and actual_url.netloc.casefold() == expected_url.netloc.casefold()
                and actual_path == expected_path
            ):
                return True
        elif actual_is_url:
            continue
        elif expected_is_absolute:
            if actual_path == expected_path:
                return True
        elif (
            actual_path == expected_path
            or actual_path.endswith(f"/{expected_path}")
        ):
            return True
    return False


def _leaf_values(node, path: str):
    if isinstance(node, dict):
        for key, sub in node.items():
            yield from _leaf_values(sub, f"{path}.{key}")
    elif isinstance(node, list):
        for i, sub in enumerate(node):
            yield from _leaf_values(sub, f"{path}[{i}]")
    else:
        yield path, node


def coverage_issues(
    content: dict | list,
    html_text: str,
    html_attributes: set[str] | None = None,
    *,
    root_path: str = "content",
    force_assets: bool = False,
) -> tuple[list[str], int, int]:
    """Return (issues, checked, skipped) for content-to-HTML coverage.

    Only short atomic values are held verbatim; image paths and long prose
    are skipped (skipped counts the prose fields).
    """
    plain = _normalize(html_text, cjk=False)
    plain_cjk = _normalize(html_text, cjk=True)
    issues: list[str] = []
    checked = skipped = 0

    for index, (path, value) in enumerate(_leaf_values(content, root_path)):
        if index >= MAX_COVERAGE_VALUES:
            issues.append(f"content: too many atomic values to check (limit {MAX_COVERAGE_VALUES})")
            break
        if len(issues) >= MAX_COVERAGE_ISSUES:
            issues.append(
                f"content: coverage issue limit reached ({MAX_COVERAGE_ISSUES}); "
                "remaining values not checked"
            )
            break
        if isinstance(value, bool) or value is None:
            continue
        needle = str(value).strip()
        if not needle:
            continue
        if isinstance(value, str):
            is_asset = force_assets or bool(
                re.search(r"\.image(s\[\d+\])?$", path)
                or re.search(r"\.(png|jpe?g|svg|webp)$", needle, re.I)
            )
            # Asset paths are consumed by attributes, not visible text. Check
            # them before the prose-length cutoff: a long URL is still a
            # required resource, not prose that may be rephrased.
            if is_asset:
                if html_attributes is not None:
                    checked += 1
                    if not _asset_present(needle, html_attributes):
                        issues.append(f"{path}: asset not found in document attributes: {needle!r}")
                continue
            if len(needle) > COVERAGE_MAX_LEN:
                skipped += 1
                continue
        checked += 1
        cjk = bool(_CJK.search(needle))
        normalized = _normalize(needle, cjk=cjk)
        present = _contains_atomic(plain_cjk if cjk else plain, normalized)
        # Whitespace-stripped fallback: markup can split a compact value across
        # sibling nodes ("<span>62</span><span>%</span>" extracts as "62\n%"),
        # which whitespace collapse alone cannot rejoin. Do not apply this to
        # space-separated Latin values: `12 34` is not the same fact as `1234`.
        if not present and (cjk or not re.search(r"\s", needle)):
            present = _contains_atomic(plain_cjk, _normalize(needle, cjk=True))
        if not present:
            issues.append(f"{path}: value not found in document text: {needle!r}")

    return issues, checked, skipped


def check_content(
    paths: list[str],
    *,
    phase_codes: dict[str, int] | None = None,
) -> int:
    """CLI: --check-content content.json [filled.html]

    Validates the content IR against its schema; with a filled HTML file,
    also verifies every short atomic value made it into the visible text.
    """
    def finish(phase: str, code: int) -> int:
        if phase_codes is not None:
            phase_codes[phase] = code
        return code

    args = [p for p in paths if not p.startswith("-")]
    if not args or len(args) > 2:
        known = ", ".join(content_schema_types()) or "none"
        print("ERROR: usage: --check-content content.json [filled.html]")
        print(f"  known types: {known}")
        return finish("contract", 2)

    content_path = Path(args[0])
    if not content_path.is_absolute():
        content_path = ROOT / content_path
    rel = rel_to_root(content_path)
    if not content_path.exists():
        print(f"ERROR: {args[0]}: file not found")
        return finish("contract", 2)
    try:
        data = json.loads(content_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: {rel}: invalid JSON: {exc}")
        return finish("contract", 1)

    doc_type, issues = validate_content_file(data)
    if issues:
        print(f"ERROR: {rel}: {len(issues)} schema issue(s)")
        for issue in issues:
            print(f"  {issue}")
        return finish("contract", 1)
    print(f"OK: {rel}: valid {doc_type} content")
    finish("contract", 0)

    if len(args) == 1:
        return 0

    html_path = Path(args[1])
    if not html_path.is_absolute():
        html_path = ROOT / html_path
    html_rel = rel_to_root(html_path)
    if not html_path.exists():
        print(f"ERROR: {args[1]}: file not found")
        return finish("coverage", 2)
    html_raw = html_path.read_text(encoding="utf-8", errors="replace")
    html_text, text_ambiguous = visible_html_evidence(html_raw, fail_closed=True)
    html_attributes, resource_ambiguous = html_resource_evidence(html_raw)
    content_missing, checked, skipped = coverage_issues(
        data["content"], html_text, html_attributes
    )
    text_missing = [
        issue for issue in content_missing
        if "asset not found in document attributes" not in issue
    ]
    asset_missing = [
        issue for issue in content_missing
        if "asset not found in document attributes" in issue
    ]
    required_assets = (data.get("brief") or {}).get("required_assets", [])
    if required_assets:
        required_asset_missing, asset_checked, _ = coverage_issues(
            required_assets,
            html_text,
            html_attributes,
            root_path="brief.required_assets",
            force_assets=True,
        )
        asset_missing.extend(required_asset_missing)
        checked += asset_checked
    missing = [*text_missing, *asset_missing]
    if missing:
        definite_missing = [
            *(text_missing if not text_ambiguous else []),
            *(asset_missing if not resource_ambiguous else []),
        ]
        indeterminate = [
            *(text_missing if text_ambiguous else []),
            *(asset_missing if resource_ambiguous else []),
        ]
        if not definite_missing:
            print(
                f"ERROR: {html_rel}: content coverage is indeterminate because "
                "visibility or resource selection could not be proven statically"
            )
            for issue in missing:
                print(f"  {issue}")
            return finish("coverage", 2)
        print(
            f"ERROR: {html_rel}: {len(definite_missing)} content value(s) "
            "definitely missing from document"
        )
        for issue in definite_missing:
            print(f"  {issue}")
        if indeterminate:
            print(
                f"  NOTE: {len(indeterminate)} additional value(s) could not be "
                "proven because visibility or resource selection is indeterminate"
            )
            for issue in indeterminate:
                print(f"    {issue}")
        return finish("coverage", 1)
    note = f" ({skipped} prose field(s) not held verbatim)" if skipped else ""
    print(f"OK: {html_rel}: all {checked} atomic content values present{note}")
    return finish("coverage", 0)
