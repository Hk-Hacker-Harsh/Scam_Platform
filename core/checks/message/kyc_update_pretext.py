"""kyc_update_pretext: keyword-lexicon check. Edit the patterns in core/data.py -> KW['kyc']."""
from .common import lexicon_check


lexicon_check('kyc_update_pretext', 'kyc', 'S', 30,
              "KYC/PAN/Aadhaar 'update or your account will be blocked' pretext", 'KYC pretext')
