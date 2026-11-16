import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

GRAPH = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns"
         xmlns:y="http://www.yworks.com/xml/graphml">
  <graph id="G" edgedefault="directed">
    <node id="n0"><data key="d0"><y:NodeLabel>ctrl:ctrl_é.py</y:NodeLabel></data></node>
    <node id="n1"><data key="d0"><y:NodeLabel>плант:плант.py</y:NodeLabel></data></node>
    <edge source="n0" target="n1"><data key="d1"><y:EdgeLabel>u</y:EdgeLabel></data></edge>
    <edge source="n1" target="n0"><data key="d1"><y:EdgeLabel>y</y:EdgeLabel></data></edge>
  </graph>
</graphml>
"""


def _build_with_cp1252_default(tmp_path, build_type):
    """Run mkconcore while text files default to cp1252, like Python on Windows."""
    src = tmp_path / "src"
    src.mkdir()
    for name in ("ctrl_é.py", "плант.py"):
        (src / name).write_text("print('x')\n", encoding="utf-8")
    wf = tmp_path / "w.graphml"
    wf.write_bytes(GRAPH.encode("utf-8"))
    out = tmp_path / "out"
    code = (
        "import builtins, sys, runpy\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        "orig = builtins.open\n"
        "def op(f, mode='r', *a, **k):\n"
        "    if 'b' not in mode and 'encoding' not in k and len(a) < 2:\n"
        "        k['encoding'] = 'cp1252'\n"
        "    return orig(f, mode, *a, **k)\n"
        "builtins.open = op\n"
        f"sys.argv = ['mkconcore.py', {str(wf)!r}, {str(src)!r}, {str(out)!r}, {build_type!r}]\n"
        f"runpy.run_path({str(REPO_ROOT / 'mkconcore.py')!r}, run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True
    )
    return result, out


@pytest.mark.parametrize("build_type", ["posix", "windows", "docker"])
def test_non_ascii_node_names_build_under_cp1252_default(tmp_path, build_type):
    result, out = _build_with_cp1252_default(tmp_path, build_type)
    assert result.returncode == 0, result.stderr[-500:]
    generated = {p.name for p in (out / "src").iterdir()}
    assert {"ctrl_é.py", "плант.py", "плант.iport"} <= generated
    build_script = out / ("build.bat" if build_type == "windows" else "build")
    expected = "docker-ctrl_é" if build_type == "docker" else "плант"
    assert expected in build_script.read_text(encoding="utf-8")
