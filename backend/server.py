from __future__ import annotations

import json
import os
import sqlite3
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "database"
DB_PATH = DB_DIR / "smart_event.db"
FRONTEND = ROOT / "frontend"
SCHEMA = DB_DIR / "schema.sql"
SEED = DB_DIR / "seed.sql"

DB_DIR.mkdir(parents=True, exist_ok=True)


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    con = connect()
    with open(SCHEMA, "r", encoding="utf-8") as f:
        con.executescript(f.read())
    count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if count == 0:
        with open(SEED, "r", encoding="utf-8") as f:
            con.executescript(f.read())
    con.commit()
    con.close()


def now():
    return datetime.now().isoformat(timespec="seconds")


def rows(sql, params=()):
    con = connect()
    try:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def one(sql, params=()):
    con = connect()
    try:
        r = con.execute(sql, params).fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def execute(sql, params=()):
    con = connect()
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def execute_script(sql):
    con = connect()
    try:
        con.executescript(sql)
        con.commit()
    finally:
        con.close()


def json_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    return json.loads(raw) if raw else {}


def send(handler, status, data, content_type="application/json"):
    if isinstance(data, (dict, list)):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    elif isinstance(data, str):
        body = data.encode("utf-8")
    else:
        body = bytes(data)
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def ok(handler, data): send(handler, 200, data)
def created(handler, data): send(handler, 201, data)
def bad(handler, message): send(handler, 400, {"error": message})
def not_found(handler): send(handler, 404, {"error": "Not found"})


def dashboard():
    event_count = one("SELECT COUNT(*) c FROM events")['c']
    attendee_count = one("SELECT COUNT(*) c FROM attendees")['c']
    vendor_count = one("SELECT COUNT(*) c FROM vendors")['c']
    resource_count = one("SELECT COUNT(*) c FROM resources")['c']
    budget = one("SELECT COALESCE(SUM(amount),0) v FROM budgets")['v']
    spent = one("SELECT COALESCE(SUM(amount),0) v FROM expenses")['v']
    unread = one("SELECT COUNT(*) c FROM notifications WHERE is_read=0")['c']
    allocated = one("SELECT COUNT(*) c FROM allocations WHERE status='Allocated'")['c']
    total_resources = max(resource_count, 1)
    return {
        "events": event_count, "attendees": attendee_count, "vendors": vendor_count,
        "resources": resource_count, "budget": budget, "spent": spent,
        "remaining": budget-spent, "unread": unread,
        "resource_utilization": round(allocated*100/total_resources, 1),
        "upcoming_events": rows("SELECT * FROM events WHERE date >= date('now') ORDER BY date, time LIMIT 8"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "SmartEvent/1.0"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PUT(self): self.route("PUT")
    def do_DELETE(self): self.route("DELETE")

    def route(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path.startswith("/api/"):
                self.api(method, path, query)
            else:
                self.static(path)
        except sqlite3.IntegrityError as e:
            bad(self, f"Database constraint: {e}")
        except json.JSONDecodeError:
            bad(self, "Invalid JSON request body")
        except Exception as e:
            print("ERROR:", repr(e))
            send(self, 500, {"error": str(e)})

    def static(self, path):
        if path == "/": path = "/index.html"
        rel = urllib.parse.unquote(path.lstrip("/"))
        file = (FRONTEND / rel).resolve()
        if not str(file).startswith(str(FRONTEND.resolve())) or not file.is_file():
            return not_found(self)
        ctype = {
            ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8", ".svg": "image/svg+xml",
            ".json": "application/json", ".png": "image/png"
        }.get(file.suffix.lower(), "application/octet-stream")
        send(self, 200, file.read_bytes(), ctype)

    def api(self, method, path, query):
        if path == "/api/health": return ok(self, {"status":"ok", "database": str(DB_PATH), "time":now()})
        if path == "/api/dashboard" and method == "GET": return ok(self, dashboard())
        if path == "/api/events" and method == "GET": return ok(self, rows("SELECT * FROM events ORDER BY date, time"))
        if path == "/api/events" and method == "POST":
            b=json_body(self); required=["name","date","time","venue","capacity"]
            missing=[x for x in required if b.get(x) in (None,"")]
            if missing: return bad(self, "Missing required fields: "+", ".join(missing))
            if int(b["capacity"]) <= 0: return bad(self,"Capacity must be greater than zero")
            eid=execute("INSERT INTO events(name,date,time,venue,capacity,event_type,status,budget,description,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(b["name"],b["date"],b["time"],b["venue"],int(b["capacity"]),b.get("event_type","Workshop"),b.get("status","Planning"),float(b.get("budget",0)),b.get("description",""),now(),now()))
            return created(self, one("SELECT * FROM events WHERE id=?",(eid,)))
        if path.startswith("/api/events/"):
            parts=path.split("/"); eid=int(parts[3])
            if len(parts)==4:
                if method=="GET":
                    e=one("SELECT * FROM events WHERE id=?",(eid,)); return ok(self,e) if e else not_found(self)
                if method=="PUT":
                    b=json_body(self); current=one("SELECT * FROM events WHERE id=?",(eid,))
                    if not current:return not_found(self)
                    vals={k:b.get(k,current[k]) for k in ["name","date","time","venue","capacity","event_type","status","budget","description"]}
                    if not vals["name"]: return bad(self,"Event name is required")
                    execute("UPDATE events SET name=?,date=?,time=?,venue=?,capacity=?,event_type=?,status=?,budget=?,description=?,updated_at=? WHERE id=?",(vals["name"],vals["date"],vals["time"],vals["venue"],int(vals["capacity"]),vals["event_type"],vals["status"],float(vals["budget"]),vals["description"],now(),eid))
                    return ok(self,one("SELECT * FROM events WHERE id=?",(eid,)))
                if method=="DELETE":
                    execute("DELETE FROM events WHERE id=?",(eid,)); return ok(self,{"message":"Event deleted"})
            if len(parts)==5 and parts[4]=="registrations" and method=="GET": return ok(self,rows("SELECT r.*,a.name attendee_name FROM registrations r JOIN attendees a ON a.id=r.attendee_id WHERE r.event_id=? ORDER BY r.registered_at DESC",(eid,)))

        if path == "/api/resources" and method == "GET": return ok(self,rows("SELECT * FROM resources ORDER BY name"))
        if path == "/api/resources" and method == "POST":
            b=json_body(self); required=["name","category","quantity"]
            if any(b.get(x) in (None,"") for x in required): return bad(self,"name, category and quantity are required")
            rid=execute("INSERT INTO resources(name,category,quantity,available,unit,location,status,created_at) VALUES(?,?,?,?,?,?,?,?)",(b["name"],b["category"],int(b["quantity"]),int(b.get("available",b["quantity"])),b.get("unit","units"),b.get("location",""),b.get("status","Available"),now()))
            return created(self,one("SELECT * FROM resources WHERE id=?",(rid,)))
        if path == "/api/allocations" and method == "GET": return ok(self,rows("SELECT al.*,e.name event_name,r.name resource_name FROM allocations al JOIN events e ON e.id=al.event_id JOIN resources r ON r.id=al.resource_id ORDER BY al.id DESC"))
        if path == "/api/allocations" and method == "POST":
            b=json_body(self); required=["event_id","resource_id","quantity"]
            if any(b.get(x) in (None,"") for x in required): return bad(self,"event_id, resource_id and quantity are required")
            event_id=int(b["event_id"]); resource_id=int(b["resource_id"]); qty=int(b["quantity"])
            if not one("SELECT id FROM events WHERE id=?",(event_id,)) or not one("SELECT id FROM resources WHERE id=?",(resource_id,)): return bad(self,"Event or resource does not exist")
            conflict=one("SELECT a.id FROM allocations a JOIN events e ON e.id=a.event_id WHERE a.resource_id=? AND a.status IN ('Allocated','Pending') AND e.date=(SELECT date FROM events WHERE id=?) AND a.event_id<>?",(resource_id,event_id,event_id))
            if conflict:return bad(self,"Resource conflict: this resource is already allocated to another event on the same date")
            rid=execute("INSERT INTO allocations(event_id,resource_id,quantity,status,allocated_at) VALUES(?,?,?,?,?)",(event_id,resource_id,qty,b.get("status","Allocated"),now()))
            return created(self,one("SELECT al.*,e.name event_name,r.name resource_name FROM allocations al JOIN events e ON e.id=al.event_id JOIN resources r ON r.id=al.resource_id WHERE al.id=?",(rid,)))

        if path == "/api/attendees" and method == "GET": return ok(self,rows("SELECT * FROM attendees ORDER BY name"))
        if path == "/api/attendees" and method == "POST":
            b=json_body(self)
            if not b.get("name") or not b.get("email"):return bad(self,"name and email are required")
            aid=execute("INSERT INTO attendees(name,email,phone,organization,role,created_at) VALUES(?,?,?,?,?,?)",(b["name"],b["email"],b.get("phone",""),b.get("organization",""),b.get("role","Attendee"),now()))
            return created(self,one("SELECT * FROM attendees WHERE id=?",(aid,)))
        if path == "/api/registrations" and method == "GET": return ok(self,rows("SELECT r.*,a.name attendee_name,a.email attendee_email,e.name event_name FROM registrations r JOIN attendees a ON a.id=r.attendee_id JOIN events e ON e.id=r.event_id ORDER BY r.registered_at DESC"))
        if path == "/api/registrations" and method == "POST":
            b=json_body(self); event_id=b.get("event_id"); attendee_id=b.get("attendee_id")
            if not event_id or not attendee_id:return bad(self,"event_id and attendee_id are required")
            event=one("SELECT * FROM events WHERE id=?",(int(event_id),)); attendee=one("SELECT * FROM attendees WHERE id=?",(int(attendee_id),))
            if not event or not attendee:return bad(self,"Event or attendee does not exist")
            if one("SELECT id FROM registrations WHERE event_id=? AND attendee_id=?",(event_id,attendee_id)):return bad(self,"Attendee is already registered for this event")
            current=one("SELECT COUNT(*) c FROM registrations WHERE event_id=?",(event_id,))["c"]
            if current>=event["capacity"]:return bad(self,"Event capacity has been reached")
            ticket=f"TKT-{datetime.now().strftime('%Y%m%d')}-{int(event_id):03d}-{int(attendee_id):04d}"
            rid=execute("INSERT INTO registrations(event_id,attendee_id,ticket_code,qr_token,status,checked_in,registered_at) VALUES(?,?,?,?,?,?,?)",(event_id,attendee_id,ticket,ticket,"Confirmed",0,now()))
            return created(self,one("SELECT r.*,a.name attendee_name,e.name event_name FROM registrations r JOIN attendees a ON a.id=r.attendee_id JOIN events e ON e.id=r.event_id WHERE r.id=?",(rid,)))
        if path.startswith("/api/registrations/"):
            parts=path.split("/"); rid=int(parts[3])
            if len(parts)==5 and parts[4]=="checkin" and method=="POST":
                r=one("SELECT * FROM registrations WHERE id=?",(rid,));
                if not r:return not_found(self)
                execute("UPDATE registrations SET checked_in=1,status='Checked In',checked_in_at=? WHERE id=?",(now(),rid)); return ok(self,one("SELECT * FROM registrations WHERE id=?",(rid,)))

        if path == "/api/vendors" and method == "GET": return ok(self,rows("SELECT * FROM vendors ORDER BY company_name"))
        if path == "/api/vendors" and method == "POST":
            b=json_body(self)
            if not b.get("company_name") or not b.get("contact_name"):return bad(self,"company_name and contact_name are required")
            vid=execute("INSERT INTO vendors(company_name,contact_name,email,phone,category,status,contract_value,service,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(b["company_name"],b["contact_name"],b.get("email",""),b.get("phone",""),b.get("category","General"),b.get("status","Onboarding"),float(b.get("contract_value",0)),b.get("service",""),now()))
            return created(self,one("SELECT * FROM vendors WHERE id=?",(vid,)))

        if path == "/api/budgets" and method == "GET": return ok(self,rows("SELECT b.*,e.name event_name FROM budgets b JOIN events e ON e.id=b.event_id ORDER BY b.id DESC"))
        if path == "/api/budgets" and method == "POST":
            b=json_body(self)
            if not b.get("event_id") or not b.get("amount"):return bad(self,"event_id and amount are required")
            bid=execute("INSERT INTO budgets(event_id,category,amount,notes,created_at) VALUES(?,?,?,?,?)",(int(b["event_id"]),b.get("category","General"),float(b["amount"]),b.get("notes",""),now()))
            return created(self,one("SELECT * FROM budgets WHERE id=?",(bid,)))
        if path == "/api/expenses" and method == "GET": return ok(self,rows("SELECT x.*,e.name event_name FROM expenses x JOIN events e ON e.id=x.event_id ORDER BY x.expense_date DESC,x.id DESC"))
        if path == "/api/expenses" and method == "POST":
            b=json_body(self)
            if not b.get("event_id") or not b.get("amount") or not b.get("description"):return bad(self,"event_id, description and amount are required")
            eid=execute("INSERT INTO expenses(event_id,category,description,amount,expense_date,approval_status,vendor_id,created_at) VALUES(?,?,?,?,?,?,?,?)",(int(b["event_id"]),b.get("category","General"),b["description"],float(b["amount"]),b.get("expense_date",datetime.now().date().isoformat()),b.get("approval_status","Pending"),b.get("vendor_id"),now()))
            return created(self,one("SELECT * FROM expenses WHERE id=?",(eid,)))

        if path == "/api/notifications" and method == "GET": return ok(self,rows("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50"))
        if path == "/api/notifications/read-all" and method == "POST": execute("UPDATE notifications SET is_read=1 WHERE is_read=0"); return ok(self,{"message":"Notifications marked as read"})
        if path == "/api/reports" and method == "GET":
            return ok(self,{"events":rows("SELECT e.*,COUNT(r.id) registrations,COALESCE(SUM(x.amount),0) spent FROM events e LEFT JOIN registrations r ON r.event_id=e.id LEFT JOIN expenses x ON x.event_id=e.id GROUP BY e.id ORDER BY e.date"),"vendors":rows("SELECT * FROM vendors"),"resources":rows("SELECT r.*,COUNT(a.id) allocations FROM resources r LEFT JOIN allocations a ON a.resource_id=r.id GROUP BY r.id")})
        if path == "/api/approvals" and method == "GET": return ok(self,rows("SELECT ap.*,x.description expense_description FROM approvals ap LEFT JOIN expenses x ON x.id=ap.expense_id ORDER BY ap.created_at DESC"))
        if path == "/api/approvals" and method == "POST":
            b=json_body(self)
            if not b.get("expense_id"):return bad(self,"expense_id is required")
            aid=execute("INSERT INTO approvals(expense_id,approver,status,comments,created_at,updated_at) VALUES(?,?,?,?,?,?)",(int(b["expense_id"]),b.get("approver","Organizer"),b.get("status","Pending"),b.get("comments",""),now(),now()))
            return created(self,one("SELECT * FROM approvals WHERE id=?",(aid,)))
        if path == "/api/workflows" and method == "GET": return ok(self,rows("SELECT * FROM workflows ORDER BY created_at DESC"))
        if path == "/api/workflows" and method == "POST":
            b=json_body(self)
            if not b.get("name"):return bad(self,"workflow name is required")
            wid=execute("INSERT INTO workflows(name,trigger_type,action_type,condition_value,is_active,created_at) VALUES(?,?,?,?,?,?)",(b["name"],b.get("trigger_type","Budget"),b.get("action_type","Notify"),b.get("condition_value",""),1,now()))
            return created(self,one("SELECT * FROM workflows WHERE id=?",(wid,)))
        not_found(self)


def main():
    init_db()
    host="127.0.0.1"; port=int(os.environ.get("PORT","8000"))
    print(f"Smart Event Planning Platform running at http://{host}:{port}")
    print(f"Database: {DB_PATH}")
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__ == "__main__": main()
