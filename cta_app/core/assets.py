"""Asset lookup helpers."""

from __future__ import annotations

import base64
import os


def resolve_asset_path(relative_path: str) -> str:
    """Return an existing asset path from cwd when possible."""
    if os.path.exists(relative_path):
        return relative_path
    return os.path.join(os.getcwd(), relative_path)


def get_base64_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

