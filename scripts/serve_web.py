"""Serve web/ for local testing, telling the browser to revalidate every file.

python -m http.server sends no Cache-Control, so browsers cache by heuristic
and keep showing an old palace.glb (or main.js) after a re-export.

    python3 scripts/serve_web.py [port]
"""
import functools
import http.server
import os
import sys

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = functools.partial(NoCacheHandler, directory=WEB)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Serving {WEB} on http://localhost:{port}/?palace=archive")
        server.serve_forever()


if __name__ == "__main__":
    main()
