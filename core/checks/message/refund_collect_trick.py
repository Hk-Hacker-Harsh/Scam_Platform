"""refund_collect_trick: keyword-lexicon check. Edit the patterns in core/data.py -> KW['refund_collect']."""
from .common import lexicon_check


lexicon_check('refund_collect_trick', 'refund_collect', 'H', 40,
              'Refund/cashback that needs you to scan a QR, approve a collect request or enter a PIN', 'refund trick')
