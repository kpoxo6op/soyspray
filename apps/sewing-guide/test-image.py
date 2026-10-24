"""Check the site files and browser privacy headers served by a built image."""

import argparse
import urllib.error
import urllib.request
from pathlib import Path


def check(url):
    with urllib.request.urlopen(url + "/index.html", timeout=10) as response:
        assert response.status == 200
        assert "connect-src 'none'" in response.headers["Content-Security-Policy"]
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert not response.headers.get("Set-Cookie")
        html = response.read()
        assert b"app.js?v=" in html and b"app.css?v=" in html
    with urllib.request.urlopen(url + "/healthz", timeout=10) as response:
        assert response.read() == b"ok\n"
    public = Path(__file__).parent / "app/public"
    files = [path for path in public.rglob("*") if path.is_file()]
    assert files
    for path in files:
        with urllib.request.urlopen(url + "/" + str(path.relative_to(public)), timeout=10) as r:
            assert r.read() == path.read_bytes(), str(path.relative_to(public))
    for path in ("/app.js", "/app.css"):
        with urllib.request.urlopen(url + path, timeout=10) as response:
            assert response.status == 200
            body = response.read()
            assert len(body) > 1000
            if path == "/app.js":
                assert "Трёхступенчатый".encode() in body, "russian content served"
    with urllib.request.urlopen(url + "/stitches/05", timeout=10) as response:
        assert b"app.js?v=" in response.read(), "deep links fall back to the app"
    try:
        urllib.request.urlopen(urllib.request.Request(url + "/", method="POST"), timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code == 405
    else:
        raise AssertionError("The static origin accepted POST.")
    print(
        f"PASS: health, privacy headers, {len(files)} exact public files, bundle and POST rejection."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173")
    check(parser.parse_args().url.rstrip("/"))
