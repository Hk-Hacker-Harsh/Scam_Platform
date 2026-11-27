"""remote_access_app: keyword-lexicon check. Edit the patterns in core/data.py -> KW['remote_app']."""
from .common import lexicon_check


lexicon_check('remote_access_app', 'remote_app', 'H', 40,
              'Tells you to install or open a remote-access/screen-share app (AnyDesk, TeamViewer...)', 'remote-access app')
