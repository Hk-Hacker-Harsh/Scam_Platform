"""Official-sounding sender using a free mailbox (gmail, yahoo, outlook...)"""
import re
from ...engine import check
from ...data import FREEMAIL
from .common import _hdr
from email.utils import parseaddr


@check("email_freemail_impersonation", "Email", "S", 30, "Official-sounding sender using a free mailbox (gmail, yahoo, outlook...)", needs="headers")
def freemail(ctx):
    name, addr = parseaddr(_hdr(ctx, "From"))
    dom = addr.split("@")[-1].lower()
    if dom in FREEMAIL and re.search(r"(?i)(bank|support|care|team|official|govt|department|hr|helpdesk|service|kyc|police|revenue)", name + addr.split("@")[0]):
        return f"'{name}' <{addr}> on free mail provider"
