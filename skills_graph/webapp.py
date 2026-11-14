"""Real Relate-backed local UI. No mock graph, no fallback to baseline.

Start: python -m skills_graph.webapp --store build/skills_graph-t3-run1.rl
Open:  http://127.0.0.1:8765
"""
from __future__ import annotations
import argparse
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from .core import load_data, plan
from .relate_backend import (_relate, seed, read_model, downstream_paths,
                             occupation_provider_paths_relate)
from .experience import explain, compare_baseline

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT / "web"


class Engine:
    def __init__(self, conn, data):
        self.conn = conn
        self.data = data
        self.scenario = data["scenario"]
        self.default_capacity = self.scenario["capacity_a"]
        self.resource_id = self.scenario["resource"]
        self.relate_version = getattr(_relate(), "__version__", "unknown")
        self.paths = downstream_paths(conn, self.resource_id)
        self.provider_paths = occupation_provider_paths_relate(conn)

    def _capacity(self, value: int) -> None:
        self.conn.execute("MATCH (r:Resource {id: $rid}) SET r.capacity = $cap",
                          {"rid": self.resource_id, "cap": value})

    def evaluate(self, cap: int) -> dict:
        if not isinstance(cap, int) or not 0 <= cap <= 1000:
            raise ValueError("capacity must be an integer between 0 and 1000")
        # A/B/A, with a guaranteed restore even if an intermediate query fails.
        try:
            self._capacity(self.default_capacity)
            original_graph = read_model(self.conn, self.data)
            a = plan(original_graph)
            self._capacity(cap)
            b = plan(read_model(self.conn, self.data))
        finally:
            self._capacity(self.default_capacity)
        restored_graph = read_model(self.conn, self.data)
        final = plan(restored_graph)
        if original_graph != restored_graph:
            raise AssertionError("Graph input did not restore to A")
        ui=explain(original_graph,[a,b,final],self.paths,self.provider_paths,
                   capacity_a=self.default_capacity,capacity_b=cap)
        ui["relate_version"]=self.relate_version
        ui["baseline_parity"]=compare_baseline(self.data,cap,ui)
        if not ui["baseline_parity"]:
            raise AssertionError("Real Relate data differs from independent baseline")
        return ui


class Handler(BaseHTTPRequestHandler):
    engine: Engine
    def do_GET(self):
        parsed=urlsplit(self.path)
        if parsed.path == "/api/evaluate":
            try:
                values=parse_qs(parsed.query,strict_parsing=False).get("capacity",["100"])
                if len(values)!=1 or not values[0].isdigit():
                    raise ValueError("capacity must be a nonnegative integer")
                response=self.engine.evaluate(int(values[0]))
                self.send_json(response,200)
            except (ValueError,KeyError) as exc:
                self.send_json({"error":str(exc)},400)
            except Exception as exc:
                # Fail visibly: never silently substitute baseline.
                self.send_json({"error":"Relate evaluation failed: "+str(exc)},500)
            return
        paths={"/":("index.html","text/html; charset=utf-8"),
               "/styles.css":("styles.css","text/css; charset=utf-8"),
               "/app.js":("app.js","text/javascript; charset=utf-8")}
        target=paths.get(parsed.path)
        if not target:
            self.send_error(404,"Not found");return
        path=WEB/target[0]
        content=path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type",target[1])
        self.send_header("Content-Length",str(len(content)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Security-Policy","default-src 'self'; img-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'")
        self.end_headers();self.wfile.write(content)

    def send_json(self, obj, status):
        content=json.dumps(obj,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(content)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers();self.wfile.write(content)

    def log_message(self,fmt,*args):
        print("[local-ui]",fmt % args)


def main():
    parser=argparse.ArgumentParser(description="SG / Relate — local judge demo UI")
    parser.add_argument("--store",default="build/skills_graph-t3-run1.rl")
    parser.add_argument("--data",default=str(ROOT/"data"/"scenario_synthetic.json"))
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    if args.host not in ("127.0.0.1","localhost","::1"):
        parser.error("Local demo binds only to loopback for safety")
    store=Path(args.store)
    if store.exists():
        parser.error("Store already exists. Use a NEW --store path; existing evidence is preserved.")
    store.parent.mkdir(parents=True,exist_ok=True)
    data=load_data(args.data)
    with _relate().connect(str(store)) as conn:
        seed(conn,data)
        Handler.engine=Engine(conn,data)
        # Exercise the real Relate API and baseline before serving a UI.
        initial=Handler.engine.evaluate(data["scenario"]["capacity_b"])
        if not initial["baseline_parity"] or not initial["restored"]:
            raise RuntimeError("Preflight failed")
        server=HTTPServer((args.host,args.port),Handler)
        print(f"Relate {initial['relate_version']} preflight PASS (A/B/A + baseline parity)")
        print(f"Browser: http://{args.host}:{args.port}/")
        print(f"Real inspectable Relate graph: {store}")
        print("Press Ctrl+C to stop. Do not share local server publicly.")
        try: server.serve_forever()
        except KeyboardInterrupt: print("Stopping UI")
        finally: server.server_close()


if __name__=="__main__":
    main()
