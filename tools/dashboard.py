"""Serve the USB dashboard locally; serial audio/control goes directly to the browser."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?",1)[0]
        if path in ("/", "/dashboard.html"):
            raw = (ROOT/"ui/dashboard.html").read_bytes(); kind="text/html; charset=utf-8"
        elif path == "/results":
            report = {}
            for name in ("primary","dsp","hybrid"):
                file = ROOT/f"models/public_evaluation_{name}.json"
                if file.exists():report[name]=json.loads(file.read_text())
            source = ROOT/"models/public_data_sources.json"
            if source.exists():report["source"]=json.loads(source.read_text())
            raw=json.dumps(report).encode(); kind="application/json"
        else:
            self.send_error(404);return
        self.send_response(200)
        self.send_header("Content-Type",kind); self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.send_header("Permissions-Policy","serial=(self)")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers(); self.wfile.write(raw)

    def log_message(self,*args):
        pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port",type=int,default=8000)
    parser.add_argument("--no-open",action="store_true")
    args=parser.parse_args()
    url=f"http://127.0.0.1:{args.port}"
    with ThreadingHTTPServer(("127.0.0.1",args.port),Handler) as server:
        print(f"Mounam dashboard: {url}\nUse Chrome/Edge. Close the terminal serial console first. Ctrl+C stops this server.",flush=True)
        if not args.no_open:webbrowser.open(url)
        try:server.serve_forever()
        except KeyboardInterrupt:pass


if __name__=="__main__":main()
