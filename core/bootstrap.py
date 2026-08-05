import os
import sys

# Bootstrapping: Automatically redirect working directory to <app_dir>/data 
# when running in bundled (frozen) mode to contain config, clips, logs, and assets.
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
    workdir = os.path.join(app_dir, "data")
    os.makedirs(workdir, exist_ok=True)
    os.chdir(workdir)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
