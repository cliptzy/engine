import os
import sys

from core.utils import get_app_root

# Bootstrapping: Set working directory globally to the app root.
# This ensures that all output folders (clips, config, cred, logs, assets)
# are localized to the app folder, making the application portable.
app_root = get_app_root()
os.chdir(app_root)
if app_root not in sys.path:
    sys.path.insert(0, app_root)
