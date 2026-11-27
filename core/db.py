"""SQLite layer (stdlib only). One connection per call; WAL for concurrent dashboard reads."""
import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases(
  id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, kind TEXT, title TEXT, content TEXT, sha256 TEXT,
  level TEXT, score REAL, hard INTEGER, ran INTEGER, basis TEXT, why TEXT, source TEXT DEFAULT 'public',
  status TEXT DEFAULT 'open', flagged INTEGER DEFAULT 0, meta TEXT, parent_id INTEGER, origin TEXT);
CREATE TABLE IF NOT EXISTS findings(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER, check_id TEXT, grp TEXT, tier TEXT, weight REAL, status TEXT, detail TEXT, descr TEXT);
CREATE TABLE IF NOT EXISTS identifiers(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER, type TEXT, value TEXT);
CREATE TABLE IF NOT EXISTS labels(
  id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, value TEXT, label TEXT, note TEXT, by_user TEXT, ts TEXT, UNIQUE(type,value));
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER, note TEXT, contact TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, pw_hash TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, user TEXT, action TEXT, target TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS ix_ident ON identifiers(type,value);
CREATE INDEX IF NOT EXISTS ix_ident_case ON identifiers(case_id);
CREATE INDEX IF NOT EXISTS ix_find_case ON findings(case_id);
CREATE INDEX IF NOT EXISTS ix_cases_sha ON cases(sha256);
"""


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


class DB:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA)
            cols = {r[1] for r in c.execute("PRAGMA table_info(cases)")}
            for col, typ in (("parent_id", "INTEGER"), ("origin", "TEXT"), ("ckey", "TEXT"), ("hits", "INTEGER DEFAULT 0"), ("last_seen", "TEXT")):
                if col not in cols:  # migrate databases created by earlier builds
                    c.execute(f"ALTER TABLE cases ADD COLUMN {col} {typ}")
            c.execute("CREATE INDEX IF NOT EXISTS ix_cases_ckey ON cases(ckey)")

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        try:
            yield c
            c.commit()
        finally:
            c.close()

    # ---- cases ----
    def save_case(self, kind, title, content, v, results, pairs, source="public", meta=None, parent_id=None, origin="", ckey=None):
        sha = hashlib.sha256((kind + "\x00" + content).encode("utf-8", "ignore")).hexdigest()
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO cases(created,kind,title,content,sha256,level,score,hard,ran,basis,why,source,meta,parent_id,origin,ckey,hits,last_seen) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)",
                (now(), kind, (title if len(title) <= 160 else title[:157] + "…"), content[:4000], sha, v["level"], v["score"], v["hard"], v["ran"], v["basis"], v["why"], source, json.dumps(meta or {}), parent_id, origin, ckey, now()))
            cid = cur.lastrowid
            c.executemany("INSERT INTO findings(case_id,check_id,grp,tier,weight,status,detail,descr) VALUES(?,?,?,?,?,?,?,?)",
                          [(cid, r["id"], r["group"], r["tier"], r["weight"], r["status"], r["detail"], r["desc"]) for r in results])
            c.executemany("INSERT INTO identifiers(case_id,type,value) VALUES(?,?,?)", [(cid, t, v_) for t, v_ in sorted(set(pairs))])
        return cid

    # ---- result cache ----
    def cached_case(self, ckey, ttl_seconds):
        """Most recent case for this cache key that is younger than ttl_seconds, or None."""
        with self.conn() as c:
            r = c.execute("SELECT id FROM cases WHERE ckey=? AND created>=datetime('now',?) ORDER BY id DESC LIMIT 1",
                          (ckey, f"-{int(ttl_seconds)} seconds")).fetchone()
        return r["id"] if r else None

    def touch_case(self, cid):
        """Count one more submission of the same input (cache hit) instead of creating a new case."""
        with self.conn() as c:
            c.execute("UPDATE cases SET hits=COALESCE(hits,0)+1, last_seen=? WHERE id=?", (now(), cid))

    def times_submitted(self, ckey):
        with self.conn() as c:
            r = c.execute("SELECT COALESCE(SUM(1+COALESCE(hits,0)),0) FROM cases WHERE ckey=?", (ckey,)).fetchone()
        return r[0]

    def update_verdict(self, cid, level, score, basis, why):
        with self.conn() as c:
            c.execute("UPDATE cases SET level=?,score=?,basis=?,why=? WHERE id=?", (level, score, basis, why, cid))

    def update_meta(self, cid, meta):
        with self.conn() as c:
            c.execute("UPDATE cases SET meta=? WHERE id=?", (json.dumps(meta), cid))

    def get_case(self, cid):
        with self.conn() as c:
            r = c.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
            if not r:
                return None
            case = dict(r)
            case["meta"] = json.loads(case.get("meta") or "{}")
            case["findings"] = [dict(x) for x in c.execute("SELECT * FROM findings WHERE case_id=? ORDER BY CASE status WHEN 'fired' THEN 0 WHEN 'clear' THEN 1 WHEN 'error' THEN 2 ELSE 3 END, weight DESC", (cid,))]
            case["ids"] = [dict(x) for x in c.execute("SELECT type,value FROM identifiers WHERE case_id=? ORDER BY type,value", (cid,))]
            case["children"] = [dict(x) for x in c.execute("SELECT id,kind,title,level,origin FROM cases WHERE parent_id=? ORDER BY id", (cid,))]
            case["reports"] = [dict(x) for x in c.execute("SELECT * FROM reports WHERE case_id=? ORDER BY id DESC", (cid,))]
            return case

    def search_cases(self, q="", level="", kind="", status="", flagged=False, limit=200):
        sql, args = "SELECT DISTINCT cases.* FROM cases LEFT JOIN identifiers i ON i.case_id=cases.id WHERE 1=1", []
        if q:
            sql += " AND (i.value LIKE ? OR cases.title LIKE ? OR cases.content LIKE ? OR cases.id=?)"
            args += [f"%{q}%", f"%{q}%", f"%{q}%", q if q.isdigit() else -1]
        for col, val in (("level", level), ("kind", kind), ("status", status)):
            if val:
                sql += f" AND cases.{col}=?"
                args.append(val)
        if flagged:
            sql += " AND cases.flagged=1"
        sql += " ORDER BY cases.id DESC LIMIT ?"
        args.append(limit)
        with self.conn() as c:
            return [dict(r) for r in c.execute(sql, args)]

    def set_status(self, cid, status):
        with self.conn() as c:
            c.execute("UPDATE cases SET status=? WHERE id=?", (status, cid))

    def add_report(self, cid, note, contact):
        with self.conn() as c:
            c.execute("INSERT INTO reports(case_id,note,contact,ts) VALUES(?,?,?,?)", (cid, note[:1000], contact[:120], now()))
            c.execute("UPDATE cases SET flagged=1 WHERE id=?", (cid,))

    # ---- labels (police verdicts) ----
    def labels_for(self, pairs):
        pairs = list(set(pairs))
        if not pairs:
            return []
        with self.conn() as c:
            out = []
            for t, v in pairs:
                r = c.execute("SELECT * FROM labels WHERE type=? AND value=?", (t, v)).fetchone()
                if r:
                    out.append(dict(r))
            return out

    def set_label(self, t, v, label, note, user):
        with self.conn() as c:
            c.execute("INSERT INTO labels(type,value,label,note,by_user,ts) VALUES(?,?,?,?,?,?) ON CONFLICT(type,value) DO UPDATE SET label=excluded.label,note=excluded.note,by_user=excluded.by_user,ts=excluded.ts",
                      (t, v, label, note[:500], user, now()))

    def del_label(self, t, v):
        with self.conn() as c:
            c.execute("DELETE FROM labels WHERE type=? AND value=?", (t, v))

    def all_labels(self):
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM labels ORDER BY id DESC")]

    # ---- linking ----
    LINK_TYPES = ("domain", "phone", "upi", "email", "crypto", "ip", "tgbot", "apk_sha256", "apk_package", "ifsc", "gstin")

    def shared_cases(self, pairs, exclude=None):
        """Other cases that share at least one identifier. Returns [{case_id, level, via:[(type,value)]}]"""
        found = {}
        with self.conn() as c:
            for t, v in set(pairs):
                if t not in self.LINK_TYPES:
                    continue
                for r in c.execute("SELECT DISTINCT i.case_id, cs.level, cs.created, cs.kind FROM identifiers i JOIN cases cs ON cs.id=i.case_id WHERE i.type=? AND i.value=? AND i.case_id IS NOT ?", (t, v, exclude)):
                    d = found.setdefault(r["case_id"], dict(case_id=r["case_id"], level=r["level"], created=r["created"], kind=r["kind"], via=[]))
                    d["via"].append((t, v))
        return sorted(found.values(), key=lambda x: -len(x["via"]))

    def campaigns(self, min_cases=2):
        """Union-find over cases that share a linking identifier."""
        with self.conn() as c:
            rows = c.execute(f"SELECT type,value,case_id FROM identifiers WHERE type IN ({','.join('?'*len(self.LINK_TYPES))})", self.LINK_TYPES).fetchall()
            cases = {r["id"]: dict(r) for r in c.execute("SELECT id,level,kind,created,title FROM cases")}
        parent = {}

        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        by_ident = {}
        for r in rows:
            by_ident.setdefault((r["type"], r["value"]), set()).add(r["case_id"])
        for ident, cs in by_ident.items():
            cs = list(cs)
            for o in cs[1:]:
                parent[find(o)] = find(cs[0])
        groups = {}
        for cid in {r["case_id"] for r in rows}:
            groups.setdefault(find(cid), set()).add(cid)
        out = []
        for g in groups.values():
            if len(g) < min_cases:
                continue
            idents = [(k, sorted(v & g)) for k, v in by_ident.items() if len(v & g) >= 2]
            out.append(dict(cases=sorted(g), size=len(g), shared=[dict(type=k[0], value=k[1], cases=cs) for k, cs in idents],
                            levels=[cases[x]["level"] for x in sorted(g) if x in cases]))
        return sorted(out, key=lambda x: -x["size"])

    def heatlist(self, limit=25):
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                f"""SELECT i.type, i.value, COUNT(DISTINCT i.case_id) n, SUM(cs.flagged) flagged, SUM(1+COALESCE(cs.hits,0)) seen,
                    SUM(CASE WHEN cs.level IN ('High','Confirmed fraud') THEN 1 ELSE 0 END) high, MAX(COALESCE(cs.last_seen, cs.created)) last_seen,
                    (SELECT label FROM labels l WHERE l.type=i.type AND l.value=i.value) label
                    FROM identifiers i JOIN cases cs ON cs.id=i.case_id
                    WHERE i.type IN ({','.join('?'*len(self.LINK_TYPES))})
                    GROUP BY i.type,i.value HAVING n>=1 ORDER BY (high*3 + n + flagged*2 + (seen-n)) DESC, last_seen DESC LIMIT ?""", (*self.LINK_TYPES, limit))]

    def stats(self):
        with self.conn() as c:
            q = lambda s, a=(): c.execute(s, a).fetchone()[0]
            return dict(
                total=q("SELECT COUNT(*) FROM cases"),
                high=q("SELECT COUNT(*) FROM cases WHERE level IN ('High','Confirmed fraud')"),
                flagged=q("SELECT COUNT(*) FROM cases WHERE flagged=1 AND status='open'"),
                today=q("SELECT COUNT(*) FROM cases WHERE date(created)=date('now')"),
                labels=q("SELECT COUNT(*) FROM labels WHERE label='confirmed_fraud'"),
                by_level={r[0]: r[1] for r in c.execute("SELECT level,COUNT(*) FROM cases GROUP BY level")},
                by_kind={r[0]: r[1] for r in c.execute("SELECT kind,COUNT(*) FROM cases GROUP BY kind")},
                by_day=[dict(d=r[0], n=r[1]) for r in c.execute("SELECT date(created) d,COUNT(*) n FROM cases GROUP BY d ORDER BY d DESC LIMIT 14")][::-1],
            )

    # ---- users / audit ----
    def get_user(self, username):
        with self.conn() as c:
            r = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            return dict(r) if r else None

    def add_user(self, username, pw_hash, role):
        with self.conn() as c:
            c.execute("INSERT OR REPLACE INTO users(username,pw_hash,role) VALUES(?,?,?)", (username, pw_hash, role))

    def user_count(self):
        with self.conn() as c:
            return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def log(self, user, action, target="", detail=""):
        with self.conn() as c:
            c.execute("INSERT INTO audit(ts,user,action,target,detail) VALUES(?,?,?,?,?)", (now(), user, action, str(target), detail[:300]))

    def audit(self, limit=300):
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))]

    # ---- graph ----
    def add_finding(self, cid, row):
        with self.conn() as c:
            c.execute("INSERT INTO findings(case_id,check_id,grp,tier,weight,status,detail,descr) VALUES(?,?,?,?,?,?,?,?)",
                      (cid, row["id"], row["group"], row["tier"], row["weight"], row["status"], row["detail"], row["desc"]))

    def findings_as_results(self, cid):
        with self.conn() as c:
            return [dict(id=r["check_id"], group=r["grp"], tier=r["tier"], weight=r["weight"], status=r["status"], detail=r["detail"], desc=r["descr"])
                    for r in c.execute("SELECT * FROM findings WHERE case_id=?", (cid,))]

    def graph(self, focus=None, show_all=False, limit=400):
        """Nodes: cases and shared identifiers. Edges: case-identifier, parent-child (followed link).
        focus=case id -> only that case's connected component."""
        with self.conn() as c:
            cases = {r["id"]: dict(r) for r in c.execute("SELECT id,kind,title,level,parent_id,origin,flagged FROM cases ORDER BY id DESC LIMIT ?", (limit,))}
            ids = c.execute(f"SELECT case_id,type,value FROM identifiers WHERE type IN ({','.join('?'*len(self.LINK_TYPES))})", self.LINK_TYPES).fetchall()
            labels = {(r["type"], r["value"]): r["label"] for r in c.execute("SELECT type,value,label FROM labels")}
        by = {}
        for r in ids:
            if r["case_id"] in cases:
                by.setdefault((r["type"], r["value"]), set()).add(r["case_id"])
        # adjacency for components
        adj = {}
        def link(a, b):
            adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
        for cid, cs in cases.items():
            if cs["parent_id"] in cases:
                link(("c", cid), ("c", cs["parent_id"]))
        for k, cs in by.items():
            if len(cs) >= 2:
                for x in cs:
                    link(("c", x), ("i",) + k)
        keep = None
        if focus:
            seen, stack = set(), [("c", int(focus))]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n); stack += list(adj.get(n, []))
            keep = seen
        nodes, edges = [], []
        used_cases = set()
        for k, cs in by.items():
            shared = len(cs) >= 2
            if not shared and not show_all:
                continue
            nid = "i:%s:%s" % k
            if keep is not None and ("i",) + k not in keep:
                continue
            nodes.append(dict(data=dict(id=nid, label=k[1][:28], kind="identifier", itype=k[0], n=len(cs), police=labels.get(k, ""))))
            for x in cs:
                edges.append(dict(data=dict(id=f"e{x}-{nid}", source=f"c{x}", target=nid, rel="has")))
                used_cases.add(x)
        for cid, cs in cases.items():
            if cs["parent_id"] in cases:
                if keep is not None and ("c", cid) not in keep:
                    continue
                edges.append(dict(data=dict(id=f"p{cid}", source=f"c{cs['parent_id']}", target=f"c{cid}", rel="followed", origin=cs["origin"])))
                used_cases |= {cid, cs["parent_id"]}
        if focus:
            used_cases.add(int(focus))
        for cid in used_cases:
            cs = cases[cid]
            nodes.append(dict(data=dict(id=f"c{cid}", label=f"#{cid} {cs['kind']}", kind="case", level=cs["level"], title=cs["title"], cid=cid, flagged=cs["flagged"])))
        return dict(nodes=nodes, edges=edges)
