"""One entry point for the assistant, shared by the website (ui_api.py) and the extension / bot API (api.py)."""
from . import assistant as A
from .analysis import analyze


class AssistantError(ValueError):
    def __init__(self, msg, code=400):
        super().__init__(msg)
        self.code = code


def run(db, data, mode="citizen", ai=False, network=False, source="public"):
    """data: {message, case_id?, lang?}. mode: citizen | police.
    One call runs the tools (analysis, lookup, guide) and, with ai=True, lets the local model write the reply. If the model is
    off, slow or its reply fails the checks, the checked rules answer is returned instead (source="rules")."""
    msg = str(data.get("message") or "").strip()[:2000]
    if not msg:
        raise AssistantError("Type a question or paste a message.")
    lang = "hi" if str(data.get("lang", "en")).lower() == "hi" else "en"
    if mode == "police":
        return A.answer_police(db, msg, use_llm=ai)
    cid = data.get("case_id")
    st = A.smalltalk(msg, lang, case_id=cid or None)
    if st:
        return st
    if cid not in (None, "", 0):
        try:
            c = db.get_case(int(cid))
        except (TypeError, ValueError):
            c = None
        if not c:
            raise AssistantError("That case does not exist.", 404)
        if A.case_intent(msg) or not (A._faq(msg) or len(msg) >= 8):
            return A.answer_case(c, msg, lang, use_llm=ai)
        # a general question asked on a result page ("what is phishing?"): answer it, keep the case context
        out = A.answer_general(db, msg, lang, run_analysis=None, use_llm=ai)
        if out.get("action") == "help":
            return A.answer_case(c, msg, lang, use_llm=ai)
        return out
    run_analysis = (lambda kind, text: analyze(db, kind, text=text, network=network, source=source))
    return A.answer_general(db, msg, lang, run_analysis=run_analysis, use_llm=ai)
