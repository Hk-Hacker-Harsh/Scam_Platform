"""bill_sim_challan_pretext: keyword-lexicon check. Edit the patterns in core/data.py -> KW['bill_sim']."""
from .common import lexicon_check


lexicon_check('bill_sim_challan_pretext', 'bill_sim', 'S', 25,
              "Electricity, SIM, FASTag or e-challan 'pay now or it's cut' pretext", 'utility pretext')
