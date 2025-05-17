"""Tests for the Flask app.

Run with pytest:

    pytest flask_test/test_app.py
"""

from app import app


def test_index():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b"WireGuard Tunnel Test" in response.data

