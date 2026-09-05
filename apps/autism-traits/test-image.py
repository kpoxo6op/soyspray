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
        assert b"/assets/app.js" in response.read()
    with urllib.request.urlopen(url + "/healthz", timeout=10) as response:
        assert response.read() == b"ok\n"
    public = Path(__file__).parent / "app/public"
    images = [path for path in public.rglob("*") if path.is_file()]
    assert images
    for path in images:
        with urllib.request.urlopen(url + "/" + str(path.relative_to(public)), timeout=10) as r:
            assert r.read() == path.read_bytes(), str(path.relative_to(public))
    for path in ("/assets/app.js", "/assets/app.css"):
        with urllib.request.urlopen(url + path, timeout=10) as response:
            assert response.status == 200
            assert len(response.read()) > 1000
    try:
        urllib.request.urlopen(urllib.request.Request(url + "/", method="POST"), timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code == 405
    else:
        raise AssertionError("The static origin accepted POST.")
    print(
        f"PASS: health, privacy headers, static assets, {len(images)} exact images and POST rejection."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173")
    check(parser.parse_args().url.rstrip("/"))
