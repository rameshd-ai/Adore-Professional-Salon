"""Helpers for SQLAdmin FileField + URL string columns."""

from __future__ import annotations

from pathlib import Path

from starlette.datastructures import UploadFile

from app.upload_storage import save_gallery_file


async def merge_upload_into_url_field(
    data: dict,
    *,
    upload_key: str,
    url_key: str,
    upload_root: Path,
    keep_existing_if_empty: bool = False,
) -> None:
    """Pop ``upload_key`` and set ``url_key`` from uploaded bytes or trimmed URL text.

    If ``keep_existing_if_empty`` is True and there is no file and no URL text, ``url_key``
    is removed so ORM updates do not overwrite the stored value.
    """
    uf = data.pop(upload_key, None)
    if isinstance(uf, UploadFile) and uf.filename:
        content = await uf.read()
        data[url_key] = save_gallery_file(content, uf.filename, upload_root)
        return

    u = (data.get(url_key) or "").strip()
    if u:
        data[url_key] = u
    elif keep_existing_if_empty:
        data.pop(url_key, None)
    else:
        data[url_key] = u
