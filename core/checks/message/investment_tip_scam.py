"""investment_tip_scam: keyword-lexicon check. Edit the patterns in core/data.py -> KW['investment']."""
from .common import lexicon_check


lexicon_check('investment_tip_scam', 'investment', 'H', 40,
              'Guaranteed returns, VIP stock/crypto tips groups, doubling schemes', 'investment lure')
