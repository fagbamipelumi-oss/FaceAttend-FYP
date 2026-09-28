"""Download dlib's 68-point facial landmark model, used for blink-based
liveness detection. Not committed to git (large binary); run this once
after cloning.
"""

import bz2
import shutil
import sys
import urllib.request
from pathlib import Path

URL = "https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
DEST_DIR = Path(__file__).resolve().parents[1] / "models"
DEST_FILE = DEST_DIR / "shape_predictor_68_face_landmarks.dat"


def main() -> None:
    if DEST_FILE.exists():
        print(f"Already present: {DEST_FILE}")
        return

    DEST_DIR.mkdir(exist_ok=True)
    archive_path = DEST_DIR / "shape_predictor_68_face_landmarks.dat.bz2"

    print(f"Downloading {URL} ...")
    urllib.request.urlretrieve(URL, archive_path)

    print("Extracting ...")
    with bz2.open(archive_path, "rb") as f_in, open(DEST_FILE, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    archive_path.unlink()
    print(f"Done: {DEST_FILE}")


if __name__ == "__main__":
    sys.exit(main())
