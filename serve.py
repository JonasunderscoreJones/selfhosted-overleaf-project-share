import http.server
import socketserver
import os
from urllib.parse import unquote

PORT = 8001
BASE_DIR = os.path.abspath("public")

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(path)

        # /project/<id> should always serve overleaf.html
        if path.startswith("/project/"): #and ("/" not in path[len("/project/"):]):
            print(f"Serving Overleaf for project: {path}")
            return os.path.join(BASE_DIR, "overleaf.html")

        # /project/<id>/file -> serve from projects/<id>/file
        if path.startswith("/project/"):
            sub_path = path[len("/project/"):]
            return os.path.join(BASE_DIR, "projects", sub_path)

        # Default: serve from public/
        if path in ["/", ""]:
            path = "/index.html"

        return os.path.join(BASE_DIR, path.lstrip("/"))

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()
