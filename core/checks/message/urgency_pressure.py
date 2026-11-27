"""urgency_pressure: keyword-lexicon check. Edit the patterns in core/data.py -> KW['urgency']."""
from .common import lexicon_check


lexicon_check('urgency_pressure', 'urgency', 'S', 15,
              'Artificial deadline or threat of blocking/suspension', 'urgency')
