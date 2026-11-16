import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

GRAPH = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns"
         xmlns:y="http://www.yworks.com/xml/graphml">
  <graph id="G" edgedefault="directed">
    <node id="n0"><data key="d0"><y:NodeLabel>a:a.py</y:NodeLabel></data></node>
    <node id="n1"><data key="d0"><y:NodeLabel>b:b.py</y:NodeLabel></data></node>
    <edge source="n0" target="n1"><data key="d1"><y:EdgeLabel>0x1_x</y:EdgeLabel></data></edge>
  </graph>
</graphml>
"""


def _write(tmp_path, bom):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("print('a')\n")
    (src / "b.py").write_text("print('b')\n")
    wf = tmp_path / "w.graphml"
    wf.write_bytes((b"\xef\xbb\xbf" if bom else b"") + GRAPH.encode("utf-8"))
    return wf, src


def _mkconcore_nodes(tmp_path, bom):
    wf, src = _write(tmp_path, bom)
    out = tmp_path / "out"
    env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp1252")
    # Simulate a Windows-style default encoding for open()
    code = (
        "import builtins, sys, runpy\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        "orig = builtins.open\n"
        "def op(f, mode='r', *a, **k):\n"
        "    if 'b' not in mode and 'encoding' not in k and len(a) < 2:\n"
        "        k['encoding'] = 'cp1252'\n"
        "    return orig(f, mode, *a, **k)\n"
        "builtins.open = op\n"
        f"sys.argv = ['mkconcore.py', {str(wf)!r}, {str(src)!r}, {str(out)!r}, 'posix']\n"
        f"runpy.run_path({str(REPO_ROOT / 'mkconcore.py')!r}, run_name='__main__')\n"
    )
    subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True
    )
    return sorted(p.name for p in (out / "src").glob("*.py"))


def test_mkconcore_builds_same_with_and_without_bom(tmp_path):
    plain = tmp_path / "plain"
    bom = tmp_path / "bom"
    plain.mkdir()
    bom.mkdir()
    with_bom = _mkconcore_nodes(bom, True)
    assert with_bom == _mkconcore_nodes(plain, False)
    assert with_bom != []


@pytest.mark.parametrize("bom", [False, True])
def test_validate_accepts_bom(tmp_path, bom):
    from concore_cli.commands.validate import validate_workflow

    class C:
        def print(self, *a, **k):
            pass

    wf, src = _write(tmp_path, bom)
    assert validate_workflow(str(wf), str(src), C()) is True
