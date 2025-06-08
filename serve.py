import http.server
import socketserver
import os
from urllib.parse import unquote
import io
import zipfile
from datetime import datetime

PORT = 8000
BASE_DIR = os.path.abspath("public")
GRAB_SYMLINKS = True  # Toggle symlink handling on/off
SYMLINK_DIR = os.path.abspath("symlinks")  # Directory to resolve symlinks to
STATIC_SHARE_RESTRICTION = True  # Toggle restriction on/off

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(path)

        if path.startswith("/project/"):
            parts = path[len("/project/"):].split("/", 1)
            project_id = parts[0]
            project_dir = os.path.join(BASE_DIR, "projects", project_id)

            # Check .staticshare restriction
            if STATIC_SHARE_RESTRICTION:
                staticshare_path = os.path.join(project_dir, ".staticshare")
                if not os.path.isfile(staticshare_path):
                    return os.path.join(BASE_DIR, "404.html")

            # Handle the zip download route
            if len(parts) == 2 and parts[1] == "zip":
                # Signal this special path, translate_path not used here, handle in do_GET
                return project_dir  # Just return project_dir path

            # Serve overleaf.html if just /project/<id> or /project/<id>/
            if len(parts) == 1 or parts[1] == "":
                return os.path.join(BASE_DIR, "overleaf.html")

            # Otherwise serve file inside project folder
            sub_path = parts[1]
            return os.path.join(project_dir, sub_path)

        if path in ["/", ""]:
            path = "/index.html"

        return os.path.join(BASE_DIR, path.lstrip("/"))

    def do_GET(self):
        path = unquote(self.path)
        if path.startswith("/project/"):
            parts = path[len("/project/"):].split("/", 1)
            project_id = parts[0]

            project_dir = os.path.join(BASE_DIR, "projects", project_id)

            if GRAB_SYMLINKS and not os.path.exists(project_dir):
                # if the project does not exist in the projects dir, check if it exists in the symlinks dir
                # get all directories in the symlinks directory
                if not os.path.exists(SYMLINK_DIR) or not os.path.isdir(SYMLINK_DIR):
                    self.send_response(404)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    with open(os.path.join(BASE_DIR, "404.html"), "rb") as f:
                        self.wfile.write(f.read())
                    return
                # find the symlink directory that starts with the project_id
                symlink_dirs = [d for d in os.listdir(SYMLINK_DIR) if os.path.isdir(os.path.join(SYMLINK_DIR, d))]
                for symlink_dir in symlink_dirs:
                    if symlink_dir.startswith(project_id):
                        project_dir = os.path.join(SYMLINK_DIR, symlink_dir)
                        break

            if STATIC_SHARE_RESTRICTION:
                staticshare_path = os.path.join(project_dir, ".staticshare")
                if not os.path.isfile(staticshare_path):
                    self.send_response(404)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    with open(os.path.join(BASE_DIR, "404.html"), "rb") as f:
                        self.wfile.write(f.read())
                    return

            if len(parts) == 2 and parts[1] == "zip":
                # Create ZIP archive in memory
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(project_dir):
                        for file in files:
                            if file.endswith((".tex", ".bib", ".pdf")):
                                filepath = os.path.join(root, file)
                                # archive name relative to project_dir
                                arcname = os.path.relpath(filepath, project_dir)
                                zipf.write(filepath, arcname)

                buffer.seek(0)
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                zip_filename = f"{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                self.send_header("Content-Disposition", f"attachment; filename={zip_filename}")
                self.send_header("Content-Length", str(len(buffer.getvalue())))
                self.end_headers()
                self.wfile.write(buffer.read())
                return

        # For all other requests, fall back to default handling
        super().do_GET()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()
