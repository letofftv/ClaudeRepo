"""Static checks of the interface — run everywhere, including the server's update gate.

    cd app && python3 -m unittest tests.test_ui_static -v

No browser needed: CSP-safety of the code, imports and icons that exist,
tokens and the vendored kit in sync with their sources, tool metadata.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
STATIC = APP / "static"
REPO = APP.parent
STUDIO = REPO / "coding" / "packs" / "ui-studio"
OWN_JS = [p for p in STATIC.rglob("*.js") if "vendor" not in p.parts]
OWN_HTML = list(STATIC.rglob("*.html"))


def strip_comments(code):
    """Drop /* */ blocks and // comments (outside strings, good enough for our own code), keep line numbers."""
    code = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), code, flags=re.S)
    return re.sub(r"(^|[^:\"'`])//[^\n]*", r"\1", code)


class CspSafetyTest(unittest.TestCase):
    def test_html_has_no_inline_code_or_styles(self):
        for page in OWN_HTML:
            html = page.read_text(encoding="utf-8")
            self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)[^>]*>", f"{page}: inline <script>")
            self.assertNotRegex(html, r"\sstyle\s*=", f"{page}: style= attribute (blocked by CSP)")
            self.assertNotRegex(html, r"\son[a-z]+\s*=", f"{page}: inline event handler")
            self.assertNotIn("<style", html, f"{page}: <style> block")

    def test_js_avoids_unsafe_apis(self):
        banned = {r"\binnerHTML\b": "innerHTML", r"\bouterHTML\b": "outerHTML", r"insertAdjacentHTML": "insertAdjacentHTML",
                  r"\beval\s*\(": "eval", r"new Function\b": "new Function", r"document\.write": "document.write",
                  r"setAttribute\(\s*['\"]style": "setAttribute('style')", r"\.cssText\b": "cssText"}
        for js in OWN_JS:
            code = strip_comments(js.read_text(encoding="utf-8"))
            for pattern, name in banned.items():
                for lineno, line in enumerate(code.splitlines(), 1):
                    if re.search(pattern, line):
                        self.fail(f"{js.relative_to(APP)}:{lineno}: {name} — {line.strip()[:100]}")

    def test_no_external_urls_in_markup(self):
        for page in OWN_HTML:
            html = page.read_text(encoding="utf-8")
            self.assertNotRegex(html, r"(src|href)=\"https?://", f"{page}: external resource (CDN) in markup")


class ModuleGraphTest(unittest.TestCase):
    def test_relative_imports_resolve(self):
        for js in OWN_JS:
            for spec in re.findall(r"""^\s*import\s[^;]*?from\s+["']([^"']+)["']""", js.read_text(encoding="utf-8"), re.M | re.S):
                self.assertTrue(spec.startswith("."), f"{js}: bare import {spec} needs an import map, which CSP blocks")
                self.assertTrue((js.parent / spec).resolve().exists(), f"{js.relative_to(APP)}: missing module {spec}")

    def test_index_references_exist(self):
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        for ref in re.findall(r"""(?:src|href)="/static/([^"]+)\"""", html):
            self.assertTrue((STATIC / ref).exists(), f"index.html: missing /static/{ref}")

    def test_icons_used_exist_in_sprite(self):
        sprite = (STATIC / "kit" / "icons.svg").read_text(encoding="utf-8")
        symbols = set(re.findall(r'<symbol id="([^"]+)"', sprite))
        used = set()
        for js in OWN_JS:
            code = js.read_text(encoding="utf-8")
            used |= set(re.findall(r"""icon\(\s*["']([a-z0-9-]+)["']""", code))
            used |= set(re.findall(r"""\bicon:\s*["']([a-z0-9-]+)["']""", code))
            for block in re.findall(r"TOOL_ICON = \{(.*?)\};", code, re.S) + re.findall(r"GROUP_ICON = \{(.*?)\};", code, re.S) \
                    + re.findall(r"TYPE_ICON = \{(.*?)\};", code, re.S):
                used |= set(re.findall(r""":\s*["']([a-z0-9-]+)["']""", block))
        missing = sorted(used - symbols)
        self.assertFalse(missing, f"icons missing from the sprite (scripts/build_icons.py --add …): {missing}")


class GeneratedFilesTest(unittest.TestCase):
    def test_tokens_css_matches_spec_and_passes_contrast(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tokens.css"
            proc = subprocess.run([sys.executable, str(STUDIO / "scripts" / "tokens.py"), str(APP / "design" / "tokens.json"),
                                   "--out", str(out), "--quiet"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(out.read_text(encoding="utf-8"), (STATIC / "tokens.css").read_text(encoding="utf-8"),
                             "app/static/tokens.css is stale: regenerate it with tokens.py from app/design/tokens.json")

    def test_kit_copy_matches_ui_studio(self):
        proc = subprocess.run([sys.executable, str(STUDIO / "scripts" / "scaffold.py"), "check", str(STATIC / "kit")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class ToolMetadataTest(unittest.TestCase):
    def test_file_params_declare_accepted_types(self):
        data = json.loads((APP / "config" / "tools.json").read_text(encoding="utf-8"))
        allowed = {"audio", "video", "image", "subtitles", "text"}
        for tool in data["tools"]:
            for p in tool.get("params", []):
                if p.get("type") == "file":
                    self.assertTrue(p.get("accept"), f"{tool['id']}.{p['name']}: no accept list")
                    self.assertTrue(set(p["accept"]) <= allowed, f"{tool['id']}.{p['name']}: {p['accept']}")


if __name__ == "__main__":
    unittest.main()
