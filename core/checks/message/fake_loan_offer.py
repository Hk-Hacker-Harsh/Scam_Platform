"""fake_loan_offer: keyword-lexicon check. Edit the patterns in core/data.py -> KW['loan']."""
from .common import lexicon_check


lexicon_check('fake_loan_offer', 'loan', 'S', 30,
              'Instant/pre-approved loan with upfront fees or no documents', 'loan lure')
