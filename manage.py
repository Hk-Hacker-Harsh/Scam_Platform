"""Admin helper.
  python manage.py adduser <name> <role>      (password is prompted, never stored in code)
  python manage.py newcheck <folder> <check_id>   create a stub check file under core/checks/<folder>/
  python manage.py cleanids [--apply]          re-apply identifier rules and scoring to stored cases (dry run by default)"""
import getpass, sys
from werkzeug.security import generate_password_hash
from core.db import DB
import os
db = DB(os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "ps01.db"))
if len(sys.argv) >= 3 and sys.argv[1] == "adduser":
    pw = getpass.getpass("Password: ")
    db.add_user(sys.argv[2], generate_password_hash(pw), sys.argv[3] if len(sys.argv) > 3 else "officer")
    print("saved")
elif len(sys.argv) == 4 and sys.argv[1] == "newcheck":
    import re
    folder, cid = sys.argv[2], sys.argv[3]
    groups = {"url": "URL", "domain": "Domain", "message": "Message", "phone": "Phone", "payment": "Payment", "email": "Email", "web": "Website", "apk": "APK", "intelligence": "Intelligence"}
    if folder not in groups or not re.fullmatch(r"[a-z][a-z0-9_]{2,60}", cid):
        sys.exit("folder must be one of %s; id must be lower_snake_case" % ", ".join(groups))
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "checks", folder, cid + ".py")
    if os.path.exists(path):
        sys.exit("already exists: " + path)
    open(path, "w").write(f'''"""TODO: one-line description."""
from ...engine import check


@check("{cid}", "{groups[folder]}", "S", 20, "TODO: one-line description", needs="any")
def {cid}(ctx):
    # return None when clear; a string describing what you saw when it fires
    return None
''')
    print("created", path)
elif len(sys.argv) >= 2 and sys.argv[1] == "cleanids":
    # Re-apply the current identifier rules and scoring to stored cases. Dry run unless --apply is given.
    import re, sqlite3
    from core.analysis import _checks  # loads every check
    from core.engine import REGISTRY, verdict
    from core.extract import extract_all, parse_url
    from core.checks.apk.extractor import clean_ids
    apply = "--apply" in sys.argv
    con = sqlite3.connect(db.path)
    con.row_factory = sqlite3.Row
    drop, changed = [], []
    for case in con.execute("SELECT id,kind,content,meta,level,basis FROM cases").fetchall():
        ids = con.execute("SELECT id,type,value FROM identifiers WHERE case_id=?", (case["id"],)).fetchall()
        if case["kind"] == "apk":
            fake = {"urls": [p for p in (parse_url(r["value"]) for r in ids if r["type"] == "domain") if p], "upis": [r["value"] for r in ids if r["type"] == "upi"],
                    "ips": [r["value"] for r in ids if r["type"] == "ip"], "emails": [r["value"] for r in ids if r["type"] == "email"],
                    "phones": [r["value"] for r in ids if r["type"] == "phone"]}
            for u in fake["urls"]:
                u["had_scheme"] = False
            keep = clean_ids(fake)
            ok = {("domain", d) for d in keep["domains"]} | {("upi", v) for v in keep["upis"]} | {("ip", v) for v in keep["ips"]} | \
                 {("email", v) for v in keep["emails"]} | {("phone", v) for v in keep["phones"]}
            bad = [r for r in ids if r["type"] in ("domain", "upi", "ip", "email", "phone") and (r["type"], r["value"]) not in ok]
        else:
            valid = set(extract_all(case["content"] or "")["upis"])
            bad = [r for r in ids if r["type"] == "upi" and r["value"] not in valid]
        drop += [(case["id"], r["id"], r["type"], r["value"]) for r in bad]
        # re-score with today's tiers / weights / High rule
        f = [dict(x) for x in con.execute("SELECT * FROM findings WHERE case_id=?", (case["id"],))]
        no_upi = not any(r["type"] == "upi" for r in ids if r not in bad)
        res = []
        for x in f:
            reg = REGISTRY.get(x["check_id"]) or ({"tier": "H", "weight": 45} if x["check_id"] == "followed_content_malicious" else None)
            tier, w = (reg["tier"], reg["weight"]) if reg else (x["tier"], x["weight"])
            st = "clear" if (x["check_id"] in ("upi_handle_valid", "upi_brand_in_id") and no_upi and x["status"] == "fired") else x["status"]
            res.append(dict(id=x["check_id"], group=x["grp"], tier=tier, weight=w, desc=x["descr"], status=st, detail=x["detail"], _row=x["id"]))
        if case["basis"] == "rules":
            v = verdict(res)
            if v["level"] != case["level"]:
                changed.append((case["id"], case["level"], v["level"]))
            if apply:
                for x in res:
                    con.execute("UPDATE findings SET tier=?,weight=?,status=? WHERE id=?", (x["tier"], x["weight"], x["status"], x["_row"]))
                con.execute("UPDATE cases SET level=?,score=?,hard=?,why=? WHERE id=?", (v["level"], v["score"], v["hard"], v["why"], case["id"]))
    print(f"{len(drop)} false identifier(s):")
    for cid, _, t, v in drop:
        print(f"  case {cid}: {t} {v}")
    print(f"{len(changed)} verdict change(s):")
    for cid, a, b in changed:
        print(f"  case {cid}: {a} -> {b}")
    if apply:
        con.executemany("DELETE FROM identifiers WHERE id=?", [(d[1],) for d in drop])
        con.commit()
        print("applied")
    else:
        print("dry run: nothing changed. Run `python manage.py cleanids --apply` to apply (back up instance/ps01.db first).")
else:
    print(__doc__)
