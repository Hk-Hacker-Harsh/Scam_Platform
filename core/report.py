"""One-case PDF report (reportlab). Includes evidence hash so the document can be tied to the stored input."""
import hashlib
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COL = {"High": "#b3261e", "Confirmed fraud": "#7a0c0c", "Medium": "#b26a00", "Low": "#2e6b34", "Verified official": "#1b5e8c", "Not enough data": "#555555"}


def case_pdf(c) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"Scam check report #{c['id']}")
    st = getSampleStyleSheet()
    S = lambda t, s="BodyText": Paragraph(t, st[s])
    e = escape
    out = [S(f"Satark – Scam Intelligence Report — case #{c['id']}", "Title"),
           S(f"Created (UTC): {e(c['created'])} &nbsp;|&nbsp; Input type: {e(c['kind'])} &nbsp;|&nbsp; Source: {e(c['source'])}")]
    out.append(Spacer(1, 4 * mm))
    colr = COL.get(c["level"], "#333")
    out.append(Paragraph(f'<font color="{colr}" size="16"><b>Risk: {e(c["level"])}</b></font> &nbsp; (score {c["score"]}/100, {c["hard"]} hard signal(s), {c["ran"]} checks ran)', st["BodyText"]))
    out.append(S(e(c["why"])))
    out.append(Spacer(1, 3 * mm))
    out.append(S("Submitted input", "Heading3"))
    out.append(S(e((c["content"] or "")[:1200]).replace("\n", "<br/>")))
    out.append(S("Why — signals that fired", "Heading3"))
    fired = [f for f in c["findings"] if f["status"] == "fired" and f["weight"] > 0]
    if fired:
        rows = [["Check", "Type", "Detail"]] + [[Paragraph(e(f["check_id"]), st["BodyText"]), "Hard" if f["tier"] == "H" else "Soft", Paragraph(e(f["detail"]), st["BodyText"])] for f in fired]
        t = Table(rows, colWidths=[48 * mm, 14 * mm, 114 * mm], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")), ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        out.append(t)
    else:
        out.append(S("No warning signs fired. This is not a guarantee of safety."))
    out.append(S("Extracted identifiers", "Heading3"))
    if c["ids"]:
        out.append(S("<br/>".join(f"{e(i['type'])}: {e(i['value'])}" for i in c["ids"][:60])))
    else:
        out.append(S("None found."))
    ev = hashlib.sha256((c["kind"] + "\x00" + (c["content"] or "")).encode("utf-8", "ignore")).hexdigest()
    out.append(Spacer(1, 4 * mm))
    out.append(S(f"Evidence hash (SHA-256 of stored input): <font size=8>{ev}</font>"))
    out.append(S("<i>Automated decision-support output. Rules produced this result; a person should review before action. "
                 "If money was lost, call 1930 or report at cybercrime.gov.in immediately. This document is not a legal certificate.</i>"))
    doc.build(out)
    return buf.getvalue()
