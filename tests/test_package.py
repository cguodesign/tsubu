"""The npm package: one version everywhere, the ES module and the declarations saying what the
script exports, and the files that would be published.

The declarations are checked by name here, without a compiler, and by the TypeScript compiler
(tests/types) where it is installed with `npm ci`.
"""

import json
import os
import re
import shutil
import subprocess

import pytest

from support import ROOT

PACKAGE = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
VERSION = r"(\d+\.\d+\.\d+)"


def node(script, *args):
    found = shutil.which("node")
    assert found, "the package tests need Node on PATH"
    done = subprocess.run([found, "--input-type=module", "-e", script, *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", timeout=60, check=True)
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def loaded():
    """What Node sees through require() and through import, for both scripts."""
    return node("""
        import { createRequire } from "node:module";
        import { pathToFileURL } from "node:url";
        const base = pathToFileURL(process.cwd() + "/"), require = createRequire(base);
        const script = require("./tsubu.js"), exporter = require("./tsubu-export.js");
        const module = await import(new URL("tsubu.mjs", base)), exporterModule = await import(new URL("tsubu-export.mjs", base));
        const named = (m) => Object.keys(m).filter((k) => k !== "default");
        console.log(JSON.stringify({
          version: script.version,
          keys: Object.keys(script), exporterKeys: Object.keys(exporter),
          named: named(module), exporterNamed: named(exporterModule),
          sameObject: module.default === script && exporterModule.default === exporter,
          sameValues: named(module).every((k) => module[k] === script[k])
            && named(exporterModule).every((k) => exporterModule[k] === exporter[k]),
        }));
    """)


def members(declarations, interface):
    """The member names of an interface in a declaration file."""
    body = re.search(r"interface " + interface + r"\b[^{]*\{(.*?)\n  \}", declarations, re.S).group(1)
    return re.findall(r"^\s+(?:readonly )?(\w+)\??[(:]", body, re.M)


def declared_constants(declarations):
    return re.findall(r"^export declare const (\w+)", declarations, re.M)


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_the_version_is_the_same_in_the_package_the_script_and_the_changelog(loaded):
    newest = re.search(r"^## \[?" + VERSION, read("CHANGELOG.md"), re.M).group(1)
    assert PACKAGE["version"] == loaded["version"] == newest


def test_a_release_tag_names_the_version():
    # In the release workflow, the tag that triggered it; elsewhere there is no tag to compare.
    if os.environ.get("GITHUB_REF_TYPE") != "tag":
        pytest.skip("not running for a tag")
    assert os.environ["GITHUB_REF_NAME"] == "v" + PACKAGE["version"]


def test_the_agent_guide_targets_a_version_that_exists():
    target = re.search(r"\*\*Targets tsubu:\*\* " + VERSION, read("docs/agents/segmenting.md")).group(1)
    as_tuple = lambda v: tuple(int(n) for n in v.split("."))
    assert as_tuple(target) <= as_tuple(PACKAGE["version"])


def test_the_es_modules_are_the_scripts_objects(loaded):
    assert loaded["sameObject"] and loaded["sameValues"]
    assert sorted(loaded["named"]) == sorted(loaded["keys"])
    assert sorted(loaded["exporterNamed"]) == sorted(loaded["exporterKeys"])


def test_every_exported_name_is_declared(loaded):
    assert sorted(members(read("tsubu.d.ts"), "API")) == sorted(loaded["keys"])
    assert sorted(declared_constants(read("tsubu.d.mts"))) == sorted(loaded["keys"])
    assert sorted(members(read("tsubu-export.d.ts"), "API")) == sorted(loaded["exporterKeys"])
    assert sorted(declared_constants(read("tsubu-export.d.mts"))) == sorted(loaded["exporterKeys"])


def test_every_option_is_declared():
    script = read("tsubu.js")
    body = script[script.index("function sentence("):script.index("function spanOf(")]
    # Options read as opts.name, and those checked in a loop over their names.
    sentence_options = set(re.findall(r"\bopts\.(\w+)", body))
    for names in re.findall(r"for \(const key of \[([^\]]*)\]\)", body):
        sentence_options |= set(re.findall(r'"(\w+)"', names))
    declarations = read("tsubu.d.ts")
    assert sentence_options == set(members(declarations, "Options"))

    contrast = script[script.index("function checkContrast("):script.index("function checkFit(")]
    assert set(re.findall(r"\bopts\.(\w+)", contrast)) == set(members(declarations, "ContrastOptions"))
    fit = script[script.index("function checkFit("):]
    assert set(re.findall(r"\bopts\.(\w+)", fit)) == set(members(declarations, "FitOptions"))
    assert set(members(declarations, "Thresholds")) == set(re.findall(r'"(\w+)"', re.search(r"const LAYERS = [^;]*", script).group(0)))

    exporter, export_declarations = read("tsubu-export.js"), read("tsubu-export.d.ts")
    lists = {name: re.findall(r'"(\w+)"', body) for name, body in re.findall(r"const (\w+_OPTIONS) = Object\.freeze\(\[([^\]]*)\]", exporter)}
    assert set(lists["WEBVTT_OPTIONS"]) == set(members(export_declarations, "WebVTTOptions"))
    assert set(lists["ASS_OPTIONS"]) == set(members(export_declarations, "ASSOptions"))
    assert set(lists["SRT_OPTIONS"]) == set(members(export_declarations, "SRTOptions"))


def test_the_declarations_compile():
    tsc = ROOT / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        pytest.skip("TypeScript is not installed (npm ci)")
    done = subprocess.run([str(tsc), "-p", "tests/types"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr


def test_every_path_the_package_names_exists_and_is_published():
    targets = [PACKAGE["main"], PACKAGE["module"], PACKAGE["types"], PACKAGE["style"]]
    def walk(value):
        if isinstance(value, str):
            targets.append(value)
        else:
            for inner in value.values():
                walk(inner)
    walk(PACKAGE["exports"])
    for target in targets:
        assert (ROOT / target).is_file(), target
        assert target == "./package.json" or target.removeprefix("./") in PACKAGE["files"], target


def test_the_published_files_are_these_and_no_others():
    npm = shutil.which("npm")
    if not npm:
        pytest.skip("npm is not installed")
    done = subprocess.run([npm, "pack", "--dry-run", "--json", "--ignore-scripts"], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", timeout=120, check=True)
    published = sorted(f["path"] for f in json.loads(done.stdout)[0]["files"])
    assert published == sorted(PACKAGE["files"] + ["LICENSE", "README.md", "package.json"])


def test_the_es_module_loads_in_the_browser(browser):
    # Served from a made-up origin, since browsers refuse module scripts from file://.
    page = browser.new_page()
    types = {".mjs": "text/javascript", ".js": "text/javascript", ".html": "text/html"}
    def serve(route):
        name = route.request.url.removeprefix("https://tsubu.test/") or "index.html"
        if name == "index.html":
            route.fulfill(content_type="text/html", body="""<!doctype html><meta charset="utf-8"><script type="module">
                import Tsubu, { sentence } from "./tsubu.mjs";
                import TsubuExport, { toSRT } from "./tsubu-export.mjs";
                const input = { segments: [{ parts: [{ text: "雨" }], start: 0, end: 1 }] };
                window.result = { keys: Object.keys(Tsubu), same: Tsubu === window.Tsubu && sentence === Tsubu.sentence,
                  exporter: TsubuExport === window.TsubuExport && toSRT(input).includes("雨") };
            </script>""")
        else:
            route.fulfill(path=str(ROOT / name), content_type=types[os.path.splitext(name)[1]])
    try:
        page.route("https://tsubu.test/**", serve)
        page.goto("https://tsubu.test/")
        page.wait_for_function("window.result !== undefined")
        result = page.evaluate("window.result")
    finally:
        page.close()
    assert result["same"] and result["exporter"]
    assert sorted(result["keys"]) == sorted(members(read("tsubu.d.ts"), "API"))


def test_every_integrity_in_the_readmes_is_the_hash_of_that_release():
    # A CDN example names a version; its hash must be that of the file at the version's tag.
    import base64
    import hashlib
    pattern = re.compile(r'(?:src|href)="https://cdn\.jsdelivr\.net/npm/[\w-]+@' + VERSION + r'/([\w.-]+)"\s+integrity="([^"]+)"')
    found = 0
    for readme in ("README.md", "README.zh-CN.md"):
        for version, name, integrity in pattern.findall(read(readme)):
            shown = subprocess.run(["git", "show", f"v{version}:{name}"], cwd=ROOT, capture_output=True)
            if shown.returncode != 0:
                pytest.skip(f"the tag v{version} is not in this checkout")
            assert integrity == "sha384-" + base64.b64encode(hashlib.sha384(shown.stdout).digest()).decode(), (readme, name)
            found += 1
    assert found >= 4
