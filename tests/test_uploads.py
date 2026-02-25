import httpx

def test_file_upload(app_server, tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"hello ignyx")
    with open(f, "rb") as fh:
        r = httpx.post(f"{app_server}/upload",
            files={"file": ("test.txt", fh, "text/plain")})
    assert r.status_code == 200
    data = r.json()
    assert data["filename"] == "test.txt"
    assert data["size"] == 11
