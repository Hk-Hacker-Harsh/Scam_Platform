"""ussd_forwarding_code: keyword-lexicon check. Edit the patterns in core/data.py -> KW['ussd']."""
from .common import lexicon_check


lexicon_check('ussd_forwarding_code', 'ussd', 'H', 45,
              'Contains a USSD call-forwarding code (**21*, *401*) that hijacks your calls/OTPs', 'forwarding code')
