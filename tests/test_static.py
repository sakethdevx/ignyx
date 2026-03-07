from ignyx import Ignyx
from ignyx.staticfiles import StaticFiles
from ignyx.testclient import TestClient


def test_serve_file(tmp_path):
    # Create an app
    app = Ignyx()

    # Create a temporary directory with a test file
    test_dir = tmp_path / "static"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("hello world")

    app.mount("/static", StaticFiles(directory=str(test_dir)))

    client = TestClient(app)
    r = client.get("/static/test.txt")
    assert r.status_code == 200
    assert r.text == "hello world"

def test_missing_file(tmp_path):
    app = Ignyx()
    test_dir = tmp_path / "static"
    test_dir.mkdir()
    app.mount("/static", StaticFiles(directory=str(test_dir)))

    client = TestClient(app)
    r = client.get("/static/missing.txt")
    assert r.status_code == 404

def test_path_traversal():
    import pytest
    from ignyx.exceptions import HTTPException
    from ignyx.staticfiles import StaticFiles

    fs = StaticFiles(directory="tests")

    with pytest.raises(HTTPException) as exc:
        fs("../secret.txt")
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        fs("/../../etc/passwd")
    assert exc.value.status_code == 403
