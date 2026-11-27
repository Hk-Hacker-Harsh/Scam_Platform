"""Helpers shared by the intelligence (linking) checks.

Two guards against the tool building evidence out of its own earlier results:
  * a re-scan of the same thing (same site, same APK) is not a "linked case": earlier cases of the same kind that
    share the input's own subject (its domain, APK hash / package) are ignored
  * an earlier High verdict only counts as campaign evidence if it was earned by a non-linking hard signal or a
    police label, so one false alarm cannot spread from case to case
"""


def linked_cases(ctx):
    if not ctx.db:
        return []
    subject = set(getattr(ctx, "subject", ()) or ())
    out = []
    for s in ctx.db.shared_cases(getattr(ctx, "pairs", [])):
        if s["kind"] == ctx_kind(ctx) and subject & set(s["via"]):
            continue
        out.append(s)
    return out


def ctx_kind(ctx):
    return getattr(ctx, "case_kind", None) or ctx.kind


def earned_high(db, case_ids):
    """Subset of case_ids whose High / Confirmed verdict rests on more than linking."""
    if not case_ids:
        return set()
    q = ",".join("?" * len(case_ids))
    with db.conn() as c:
        rows = c.execute(f"""SELECT DISTINCT cs.id FROM cases cs WHERE cs.id IN ({q}) AND (cs.level='Confirmed fraud' OR EXISTS(
                             SELECT 1 FROM findings f WHERE f.case_id=cs.id AND f.status='fired' AND f.tier='H' AND f.weight>0
                             AND f.check_id NOT IN ('identifier_linking_campaigns','repeat_cases_linked','citizen_repeat_submissions')))""",
                         list(case_ids)).fetchall()
    return {r[0] for r in rows}
