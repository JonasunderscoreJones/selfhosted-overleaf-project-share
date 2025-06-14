import http.server
import socketserver
import os
from urllib.parse import unquote
import io
import zipfile
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 8000))  # Default port is 8000 if not set
BASE_DIR = os.path.abspath("public")
GRAB_SYMLINKS = os.getenv("GRAB_SYMLINKS", "true").lower() == "true"  # Toggle symlink grabbing
SYMLINK_DIR = os.getenv("SYMLINK_DIR", "symlinks")  # Directory where symlinks are stored
STATIC_SHARE_RESTRICTION = os.getenv("STATIC_SHARE_RESTRICTION", "true").lower() == "true"  # Restrict access to .staticshare

def create_symlink_to_dir(symlink_target, link_path):
    try:
        if os.path.islink(link_path) or os.path.exists(link_path):
            os.remove(link_path)
        # Ensure the parent directory exists
        os.makedirs(os.path.dirname(link_path), exist_ok=True)
        os.symlink(symlink_target, link_path)
        print(f"Symlink created: {link_path} -> {symlink_target}")
    except OSError as e:
        print(f"Failed to create symlink: {e}")

def get_project_directory(project_id):
    project_dir = os.path.join(BASE_DIR, "projects", project_id)
    if GRAB_SYMLINKS and not os.path.exists(project_dir):
        # If the project does not exist in the projects dir, check if it exists in the symlinks dir
        if not os.path.exists(SYMLINK_DIR) or not os.path.isdir(SYMLINK_DIR):
            return None
        # Find the symlink directory that starts with the project_id
        symlink_dirs = [d for d in os.listdir(SYMLINK_DIR) if os.path.isdir(os.path.join(SYMLINK_DIR, d))]
        # Sort by last modified time (descending)
        symlink_dirs.sort(
            key=lambda d: os.path.getmtime(os.path.join(SYMLINK_DIR, d)),
            reverse=True
        )
        for symlink_dir in symlink_dirs:
            if symlink_dir == project_id or symlink_dir.startswith(project_id + "-"):
                symlink_dir = os.path.join(SYMLINK_DIR, symlink_dir)
                if os.path.exists(symlink_dir):
                    create_symlink_to_dir(symlink_dir, project_dir)
                    break
    return project_dir

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(path)

        if path.startswith("/project/"):
            parts = path[len("/project/"):].split("/", 1)
            project_id = parts[0]
            project_dir = get_project_directory(project_id)

            if not project_dir:
                return os.path.join(BASE_DIR, "404.html")
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

            project_dir = get_project_directory(project_id)

            if not project_dir:
                self.send_response(404)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                with open(os.path.join(BASE_DIR, "404.html"), "rb") as f:
                    self.wfile.write(f.read())
                return

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
