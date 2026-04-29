#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from wsgiref.simple_server import WSGIServer, make_server
from socketserver import ThreadingMixIn

ROOT = "/Users/raymonddavis/nexus-ai"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from control_center.control_center_server import app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main() -> int:
    host = os.getenv("CONTROL_CENTER_HOST", "127.0.0.1")
    port = int(os.getenv("CONTROL_CENTER_PORT", "4000"))
    with make_server(host, port, app, server_class=ThreadingWSGIServer) as httpd:
        print(f"Control Center WSGI listening on http://{host}:{port}", flush=True)
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
