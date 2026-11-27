"""otp_pin_request: keyword-lexicon check. Edit the patterns in core/data.py -> KW['otp_pin']."""
from .common import lexicon_check


lexicon_check('otp_pin_request', 'otp_pin', 'H', 45,
              'Asks you to share/enter an OTP, PIN, CVV or password', 'asks for secret')
