import os
import sys

from core.utils import get_app_root

import sys
import shutil
import subprocess

# Mencegah crash Segfault (cuInit UNKNOWN ERROR 303 / libtriton.so) pada sistem Linux
# dengan driver NVIDIA bermasalah saat memuat TensorFlow/PyTorch via DeepFace.
os.environ["TRITON_DISABLE"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Blokir pemuatan modul 'triton' secara total karena libtriton.so rentan terhadap
# Segmentation Fault pada saat inisialisasi di sistem dengan GPU AMD/driver rusak.
# PyTorch tetap dapat berjalan normal tanpa triton (hanya torch.compile yang terdampak).
sys.modules["triton"] = None  # type: ignore

# Matikan deteksi CUDA secara paksa jika sistem tidak memiliki driver NVIDIA (mis. AMD/Intel)
# Ini penting karena PyTorch C++ backend akan tetap mencoba probing CUDA meskipun hw_accel='cpu'
if not shutil.which("nvidia-smi"):
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
else:
    try:
        subprocess.run(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Bootstrapping: Set working directory globally to the app root.
# This ensures that all output folders (clips, config, cred, logs, assets)
# are localized to the app folder, making the application portable.
app_root = get_app_root()
os.chdir(app_root)
if app_root not in sys.path:
    sys.path.insert(0, app_root)
