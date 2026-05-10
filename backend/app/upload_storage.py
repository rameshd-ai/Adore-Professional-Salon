import uuid
from pathlib import Path

_ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def ensure_upload_root(root: Path) -> None:
    (root / "gallery").mkdir(parents=True, exist_ok=True)


def save_gallery_file(content: bytes, original_filename: str, root: Path) -> str:
    """Write bytes under root/gallery and return public URL path /uploads/gallery/..."""
    ensure_upload_root(root)
    suffix = Path(original_filename or "").suffix.lower()
    if suffix not in _ALLOWED:
        suffix = ".jpg"
    name = f"{uuid.uuid4().hex}{suffix}"
    path = root / "gallery" / name
    path.write_bytes(content)
    return f"/uploads/gallery/{name}"
