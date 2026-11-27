"""prize_lottery: keyword-lexicon check. Edit the patterns in core/data.py -> KW['prize']."""
from .common import lexicon_check


lexicon_check('prize_lottery', 'prize', 'S', 25,
              'Lottery, prize, reward-points or cashback claim', 'prize lure')
