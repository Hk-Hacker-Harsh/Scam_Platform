# Checks

One file per check: `core/checks/<group>/<check_id>.py`. The file name is the check id.

| Folder | Group | What lives there |
|---|---|---|
| `url/` | URL | homograph, typosquat, redirects, XSS payload, shorteners… (`url/common.py` holds shared helpers) |
| `domain/` | Domain | online lookups: domain age, DNS, SPF (skipped when offline) |
| `message/` | Message | scam-text checks. Most are one-liners using `lexicon_check`; patterns live in `core/data.py` → `KW` |
| `phone/` | Phone | helpline mismatch, foreign number, format |
| `payment/` | Payment | UPI handle, brand in UPI ID, IFSC, crypto, GSTIN, RBI claim |
| `email/` | Email | SPF/DKIM/DMARC, display-name spoof, Reply-To, anchor mismatch, attachments |
| `web/` | Website | page-content checks. `web/fetcher.py` is the SSRF-safe downloader |
| `apk/` | APK | permission, certificate, clone, embedded identifiers. `apk/extractor.py` parses the file |
| `intelligence/` | Intelligence | police labels, campaign linking, official registry |

## Add a check
    python manage.py newcheck <folder> <check_id>      # creates the stub file
Then edit the file. Nothing else to register: `core/checks/__init__.py` imports every file automatically.

## Anatomy
    @check("my_check_id", "URL", "H", 35, "One-line description shown on /catalogue and in reports", needs="urls", net=False)
    def my_check(ctx):
        return "what we saw"      # return None / "" when nothing is wrong, a string (or list) when it fires

* tier `"H"` hard (decides High alone when its weight is 45 or more; otherwise needs a second signal) · `"S"` soft (adds up, caps at Medium) · `"L"` info only
* `needs`: `text`, `urls`, `html`, `headers`, `apk`, `phones`, `upis`, `ifsc`, `any`. The check is skipped as "not applicable" if that input is absent.
* `net=True`: needs internet; skipped when online lookups are off.
* `ctx.ids` holds extracted identifiers, `ctx.text` the message/body, `ctx.html` page HTML, `ctx.apk` APK facts, `ctx.db` the database.
* To remove a check, delete its file. To change a weight or wording, edit the decorator.
* Tune scam keywords in `core/data.py` (`KW`), brand and helpline registry in `BRANDS`.
* The catalogue shown on the website page /catalogue is `core/data/catalogue.json`; ids that match a file are shown as live.
