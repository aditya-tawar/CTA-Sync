"""Persistence and lookup for the global allowed-domains list."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_DOMAINS_FILE = (
    Path(__file__).resolve().parent.parent / "allowed_domains.json"
)


def _normalize_domain(domain: str) -> str:
    return domain.strip().lower().lstrip(".")


def load_allowed_domains() -> list[str]:
    if not ALLOWED_DOMAINS_FILE.exists():
        return []
    try:
        data = json.loads(ALLOWED_DOMAINS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    raw = data.get("allowed_domains", []) if isinstance(data, dict) else []
    return [_normalize_domain(d) for d in raw if isinstance(d, str) and d.strip()]


def save_allowed_domains(domains: list[str]) -> None:
    cleaned = []
    seen = set()
    for domain in domains:
        normalized = _normalize_domain(domain)
        if normalized and normalized not in seen:
            cleaned.append(normalized)
            seen.add(normalized)
    ALLOWED_DOMAINS_FILE.write_text(
        json.dumps({"allowed_domains": cleaned}, indent=4)
    )


def add_allowed_domain(domain: str) -> bool:
    normalized = _normalize_domain(domain)
    if not normalized:
        return False
    domains = load_allowed_domains()
    if normalized in domains:
        return False
    domains.append(normalized)
    save_allowed_domains(domains)
    return True


def remove_allowed_domain(domain: str) -> bool:
    normalized = _normalize_domain(domain)
    domains = load_allowed_domains()
    if normalized not in domains:
        return False
    domains.remove(normalized)
    save_allowed_domains(domains)
    return True


def host_of(url: str) -> str:
    try:
        netloc = urlparse(url.strip()).netloc
    except Exception:
        return ""
    return netloc.split(":")[0].lower()


def is_domain_allowed(url: str, allowed_domains: list[str] | None = None) -> bool:
    """Empty allowlist means feature is disabled — everything passes."""
    if allowed_domains is None:
        allowed_domains = load_allowed_domains()
    if not allowed_domains:
        return True
    host = host_of(url)
    if not host:
        return False
    for domain in allowed_domains:
        if host == domain or host.endswith("." + domain):
            return True
    return False
