import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from app.config import get_settings


_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}
settings = get_settings()


class UnsafeUrlError(ValueError):
    pass


class SafeSession(requests.Session):
    def __init__(self, max_redirects: int = 5):
        super().__init__()
        self.max_redirects = max_redirects
        self.verify = _resolve_verify_target()

    def get(self, url: str, **kwargs) -> requests.Response:
        return safe_get(url, session=self, max_redirects=self.max_redirects, **kwargs)


def _is_forbidden_ip(ip: ipaddress._BaseAddress) -> bool:
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def _resolve_verify_target() -> str | bool:
    if not settings.fetch_verify_ssl:
        return False

    candidates = (
        os.getenv("REQUESTS_CA_BUNDLE"),
        os.getenv("SSL_CERT_FILE"),
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/etc/ssl/certs/ca-certificates.crt",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return True


def resolve_hostname(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Unable to resolve hostname '{hostname}'.") from exc

    addresses: list[str] = []
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        address = sockaddr[0]
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise UnsafeUrlError(f"Unable to resolve hostname '{hostname}'.")
    return addresses


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"URL scheme '{parsed.scheme}' not allowed. Use http or https.")
    if not parsed.hostname:
        raise UnsafeUrlError("Invalid URL: no hostname.")
    hostname = parsed.hostname.strip().lower()
    if hostname in _BLOCKED_HOSTNAMES:
        raise UnsafeUrlError("URLs pointing to local hostnames are not allowed.")

    try:
        ip = ipaddress.ip_address(hostname)
        addresses = [str(ip)]
    except ValueError:
        addresses = resolve_hostname(hostname)

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if _is_forbidden_ip(ip):
            raise UnsafeUrlError("URLs pointing to private, local, or otherwise non-public networks are not allowed.")


def safe_get(
    url: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 20,
    headers: dict | None = None,
    max_redirects: int = 5,
) -> requests.Response:
    current_url = url
    client = session or requests.Session()

    for _ in range(max_redirects + 1):
        validate_public_url(current_url)
        response = requests.Session.request(
            client,
            method="GET",
            url=current_url,
            timeout=timeout,
            headers=headers,
            allow_redirects=False,
        )
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            if not location:
                raise UnsafeUrlError("Redirect response missing Location header.")
            current_url = urljoin(current_url, location)
            continue
        response.raise_for_status()
        validate_public_url(response.url)
        return response

    raise UnsafeUrlError(f"Too many redirects while fetching '{url}'.")
