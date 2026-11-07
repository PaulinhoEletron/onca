"""Download em streaming para o disco, com timeout, repetições e limite de tamanho."""

import time
from collections.abc import Callable
from pathlib import Path

import httpx

USER_AGENT = "OncaGuardia/0.1 (+environmental-risk research project)"
MAX_BYTES = 50 * 1024 * 1024
TIMEOUT = httpx.Timeout(30.0, read=60.0)
ATTEMPTS = 3
BACKOFF_SECONDS = 2.0
_RETRY_STATUS = {429, 500, 502, 503, 504}


class DownloadError(Exception):
    """Falha definitiva no download."""


def _fetch_once(client: httpx.Client, url: str, dest: Path, max_bytes: int) -> None:
    with client.stream("GET", url, follow_redirects=True) as response:
        if response.status_code in _RETRY_STATUS:
            raise httpx.TransportError(f"HTTP {response.status_code}")
        if response.status_code >= 400:
            raise DownloadError(f"HTTP {response.status_code} em {url}")
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            raise DownloadError(f"arquivo maior que o limite de {max_bytes // 1024 // 1024} MB")
        size = 0
        with dest.open("wb") as out:
            for block in response.iter_bytes(64 * 1024):
                size += len(block)
                if size > max_bytes:
                    raise DownloadError(
                        f"arquivo maior que o limite de {max_bytes // 1024 // 1024} MB"
                    )
                out.write(block)


def download(
    url: str,
    dest: Path,
    client: httpx.Client | None = None,
    max_bytes: int = MAX_BYTES,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """Baixa `url` para `dest` sem carregar o arquivo inteiro na memória."""
    own_client = client is None
    http = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    try:
        last: Exception | None = None
        for attempt in range(1, ATTEMPTS + 1):
            try:
                _fetch_once(http, url, dest, max_bytes)
                return dest
            except httpx.TransportError as exc:  # inclui timeouts e erros de rede
                last = exc
                dest.unlink(missing_ok=True)
                if attempt < ATTEMPTS:
                    sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
            except DownloadError:
                dest.unlink(missing_ok=True)
                raise
        raise DownloadError(f"falha ao baixar {url} após {ATTEMPTS} tentativas: {last}") from last
    finally:
        if own_client:
            http.close()
