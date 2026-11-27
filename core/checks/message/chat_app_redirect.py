"""chat_app_redirect: keyword-lexicon check. Edit the patterns in core/data.py -> KW['chat_move']."""
from .common import lexicon_check


lexicon_check('chat_app_redirect', 'chat_move', 'S', 20,
              'Moves you to WhatsApp/Telegram group or chat link', 'chat redirect')
