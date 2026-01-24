import os
import sys
import zipfile
import platform
import tempfile
import shutil
import uuid

def load_vendored_zstandard(bundle_path: str) -> None:
    """
    Extracts vendored zstandard from the given bundle (.apworld/zip)
    and adds it to sys.path for runtime import.

    Handles:
      - Windows/Linux
      - Python 3.11–3.13
      - Frozen apps and multiprocessing
      - Avoids .pyd locking issues by using unique extraction folders
    """
    if "zstandard" in sys.modules:
        return

    py_tag = f"py{sys.version_info.major}{sys.version_info.minor}"

    system = platform.system()
    if system == "Windows":
        os_key = "win"
    elif system == "Linux":
        os_key = "linux"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    source_prefix = f"cotnd/vendor/zstandard/{os_key}_{py_tag}/zstandard/"

    # Unique temp folder per process to avoid pyd locking issues
    extract_root = os.path.join(tempfile.gettempdir(), f"vendored_zstandard_{uuid.uuid4().hex}")
    os.makedirs(extract_root, exist_ok=True)

    extracted_any = False

    with zipfile.ZipFile(bundle_path) as zf:
        for member in zf.namelist():
            if member.startswith(source_prefix):
                relative_path = os.path.relpath(member, source_prefix)
                target_path = os.path.join(extract_root, "zstandard", relative_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zf.open(member) as src_file, open(target_path, "wb") as dst_file:
                    dst_file.write(src_file.read())
                extracted_any = True

    if not extracted_any:
        raise RuntimeError(f"No zstandard binaries found for {os_key}_{py_tag}")

    # Add the extracted folder to sys.path
    sys.path.insert(0, os.path.join(extract_root))

    # Optional: clean up on exit (works only if no child processes are still using the files)
    import atexit
    atexit.register(lambda: shutil.rmtree(extract_root, ignore_errors=True))
