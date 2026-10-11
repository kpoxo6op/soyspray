"""Real pinned SDK wire contract: binary stdin must close before exec success."""

import base64
import hashlib
import json
import struct
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace

from kubernetes.stream.ws_client import WSClient
from operations.intake import receiver_result, stream_archive

from kubernetes import client


class ExecPeer(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split("?", 1)[0].endswith("/log"):
            body = json.dumps({"status": "installed", "packHash": "a" * 64}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        key = self.headers["Sec-WebSocket-Key"]
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.send_header("Sec-WebSocket-Protocol", "v5.channel.k8s.io")
        self.end_headers()
        self.wfile.flush()
        self.connection.settimeout(3)
        while True:
            first, second = self.rfile.read(2)
            size = second & 127
            if size == 126:
                size = struct.unpack("!H", self.rfile.read(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self.rfile.read(8))[0]
            mask = self.rfile.read(4)
            wire = self.rfile.read(size)
            payload = bytes(value ^ mask[i % 4] for i, value in enumerate(wire))
            if first & 15 != 2 or not second & 128:
                raise ValueError("Expected masked binary client frame")
            if payload == b"\xff\x00":
                self.server.stdin_closed = True
                status = b"\x03" + json.dumps({"status": "Success"}).encode()
                self.wfile.write(bytes([0x82, len(status)]) + status + b"\x88\x00")
                self.wfile.flush()
                return
            if payload[:1] != b"\x00":
                raise ValueError("Unexpected channel")
            self.server.received.extend(payload[1:])


class IntakeStream(unittest.TestCase):
    def test_binary_payload_and_stdin_half_close_precede_success(self):
        server = HTTPServer(("127.0.0.1", 0), ExecPeer)
        server.received = bytearray()
        server.stdin_closed = False
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        config = client.Configuration()
        config.no_proxy = "127.0.0.1,localhost"
        channel = WSClient(config, f"ws://127.0.0.1:{server.server_port}/exec", None, True)
        try:
            with tempfile.TemporaryDirectory() as scratch:
                archive = Path(scratch) / "binary.tar"
                data = bytes(range(256)) * 2500
                archive.write_bytes(data)
                stream_archive(channel, archive, timeout=2)
                self.assertTrue(server.stdin_closed)
                self.assertEqual(bytes(server.received), data)
                self.assertEqual(channel.returncode, 0)
        finally:
            channel.close()
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)

    def test_protocol_without_half_close_is_rejected_before_transfer(self):
        with self.assertRaisesRegex(ValueError, "half-close"):
            stream_archive(SimpleNamespace(subprotocol="v4.channel.k8s.io"), Path("unused"))

    def test_pinned_sdk_receiver_log_keeps_wire_json_intact(self):
        server = HTTPServer(("127.0.0.1", 0), ExecPeer)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        config = client.Configuration()
        config.host = f"http://127.0.0.1:{server.server_port}"
        config.no_proxy = "127.0.0.1,localhost"
        api = client.ApiClient(config)
        try:
            self.assertEqual(
                receiver_result(client.CoreV1Api(api), "receiver", "agents"),
                {"status": "installed", "packHash": "a" * 64},
            )
        finally:
            api.close()
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)
