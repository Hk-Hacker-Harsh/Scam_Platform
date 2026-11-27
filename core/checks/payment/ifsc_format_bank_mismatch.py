"""IFSC code malformed or does not match the bank named in the text"""
from ...engine import check
from ..url.common import _brand_in


@check("ifsc_format_bank_mismatch", "Payment", "S", 20, "IFSC code malformed or does not match the bank named in the text", needs="ifsc")
def ifsc_check(ctx):
    out = []
    code_map = {"SBIN": "sbi", "HDFC": "hdfc", "ICIC": "icici", "UTIB": "axis", "PUNB": "pnb", "KKBK": "kotak"}
    for code in ctx.ids["ifsc"]:
        b = _brand_in(ctx.text)
        bank = code_map.get(code[:4])
        if b and bank and b != bank and b in code_map.values():
            out.append(f"{code} is a {bank.upper()} code but text names {b}")
        elif code[:4] not in code_map and b in code_map.values():
            out.append(f"{code} bank code is not {b.upper()}'s")
    return out
