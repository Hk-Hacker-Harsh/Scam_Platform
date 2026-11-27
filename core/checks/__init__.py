"""Every check lives in core/checks/<group>/<check_id>.py and registers itself with @check.
load_all() imports them all, so adding a file is enough to add a check."""
import importlib
import pkgutil

_loaded = False


def load_all():
    global _loaded
    if _loaded:
        return
    for m in pkgutil.walk_packages(__path__, __name__ + "."):
        importlib.import_module(m.name)
    _loaded = True
