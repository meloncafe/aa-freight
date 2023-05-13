# flake8: noqa

from .settings_core import *

# Add any additional apps to this list.
INSTALLED_APPS += [
    "allianceauth.services.modules.discord",
]
