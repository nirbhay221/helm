"""Every inline script on the console and the control room must parse, or the whole page goes dead."""
import re
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from ui.app import app

NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("path", ["/", "/live"])
def test_inline_scripts_parse(path, tmp_path):
    html = TestClient(app).get(path).text
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert scripts
    for i, src in enumerate(scripts):
        f = tmp_path / f"s{i}.js"
        f.write_text(src, encoding="utf8")
        r = subprocess.run([NODE, "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{path} script {i}: {r.stderr[:400]}"
