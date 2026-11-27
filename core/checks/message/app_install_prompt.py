"""app_install_prompt: keyword-lexicon check. Edit the patterns in core/data.py -> KW['app_install']."""
from .common import lexicon_check


lexicon_check('app_install_prompt', 'app_install', 'S', 30,
              'Asks you to download/install an app or APK from a link', 'install prompt')
