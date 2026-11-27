"""Countdown timer / 'only X left' pressure widgets"""
import re
from ...engine import check


@check("urgency_countdown_widgets", "Website", "S", 15, "Countdown timer / 'only X left' pressure widgets", needs="html")
def countdown(ctx):
    return "countdown or scarcity widget" if re.search(r"(?i)countdown|hurry up|only \d+ (left|slots|seats)|offer ends in|limited time", ctx.html) else None
