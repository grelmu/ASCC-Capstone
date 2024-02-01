
import sys

# DRAGONS: The assigned names here are less important than getting the <package>.tests modules cached
# for later use
from mppw import tests as mppw_tests
from mppw_clients import tests as mppw_clients_tests
from mppw_web import tests as mppw_web_tests

# Allow the use of submodule test fixtures too
for submodule_name in ["mppw", "mppw_clients", "mppw_web"]:
    sys.path.append(f"./{submodule_name}")
    sys.modules.pop(submodule_name)