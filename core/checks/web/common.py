"""Helpers shared by the web checks."""
from ...extract import parse_url
from bs4 import BeautifulSoup


def _page_host(ctx):
    for u in ctx.ids.get("urls", [])[:1]:
        if ctx.kind == "url":
            return (parse_url(ctx.final_url)["host"] if ctx.final_url else u["host"])
    return None


def _soup(ctx):
    if not hasattr(ctx, "_soup"):
        ctx._soup = BeautifulSoup(ctx.html, "lxml")
    return ctx._soup
