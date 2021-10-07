from .main import app

import pkg_resources
try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = None

app.version = __version__