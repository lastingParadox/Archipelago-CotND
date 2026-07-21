import os
import sys
import zipfile
import zipimport
import platform
import tempfile
import shutil
import uuid

def load_vendored_zstandard() -> None:
    """
    Ensures zstandard is importable, either from the environment or from the
    vendored binaries bundled inside the .apworld zip.

    Tries a system/environment install first, then falls back to extracting
    the appropriate binary for the current OS and Python version from the
    apworld archive. The archive path is derived automatically from this
    module's own loader, so no external path argument is needed.
    """

    if "zstandard" in sys.modules:
        return

    try:
        __import__("zstandard")
        return
    except ImportError:
        pass

    loader = globals().get("__loader__")
    if not isinstance(loader, zipimport.zipimporter):
        raise RuntimeError(
            "zstandard is not installed and this module is not running from "
            "inside an .apworld zip. Install zstandard via pip, or use the "
            ".apworld bundle."
        )

    bundle_path = loader.archive

    py_tag = f"py{sys.version_info.major}{sys.version_info.minor}"

    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        os_key = f"win_{py_tag}"

    elif system == "Linux":
        os_key = f"linux_{py_tag}"

    elif system == "Darwin":
        if machine in ("arm64", "aarch64"):
            arch = "arm64"
        elif machine in ("x86_64", "amd64"):
            arch = "x86_64"
        else:
            raise RuntimeError(f"Unsupported macOS architecture: {machine}")

        os_key = f"macos_{arch}_{py_tag}"

    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    source_prefix = f"cotnd/vendor/zstandard/{os_key}/zstandard/"

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
        raise RuntimeError(
            f"No vendored zstandard binaries found for {os_key} in {bundle_path}. "
            f"This build may not support your platform or Python version."
        )

    sys.path.insert(0, extract_root)

    import atexit
    atexit.register(lambda: shutil.rmtree(extract_root, ignore_errors=True))
