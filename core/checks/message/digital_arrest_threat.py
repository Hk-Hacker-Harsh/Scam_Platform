"""digital_arrest_threat: keyword-lexicon check. Edit the patterns in core/data.py -> KW['digital_arrest']."""
from .common import lexicon_check


lexicon_check('digital_arrest_threat', 'digital_arrest', 'H', 45,
              "Police/CBI/customs 'digital arrest', parcel-with-drugs or video-call investigation threat", 'authority threat')
