from pathlib import Path

import httpx
import pytest

from onca.kb.download import USER_AGENT, DownloadError, download


def client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler, headers={"User-Agent": USER_AGENT})


def test_download_streams_to_file(tmp_path: Path) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["user-agent"])
        return httpx.Response(200, content=b"x" * 200_000)

    dest = download("https://a.org/f", tmp_path / "f", client(httpx.MockTransport(handler)))
    assert dest.stat().st_size == 200_000
    assert seen == [USER_AGENT]


def test_retries_then_succeeds(tmp_path: Path) -> None:
    calls = {"n": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else httpx.Response(200, content=b"ok")

    dest = download(
        "https://a.org/f",
        tmp_path / "f",
        client(httpx.MockTransport(handler)),
        sleep=sleeps.append,
    )
    assert dest.read_bytes() == b"ok"
    assert calls["n"] == 3
    assert sleeps == [2.0, 4.0]


def test_gives_up_after_retries(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("lento")

    with pytest.raises(DownloadError, match="3 tentativas"):
        download(
            "https://a.org/f",
            tmp_path / "f",
            client(httpx.MockTransport(handler)),
            sleep=lambda _: None,
        )
    assert not (tmp_path / "f").exists()


def test_404_is_not_retried(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404)

    with pytest.raises(DownloadError, match="404"):
        download("https://a.org/f", tmp_path / "f", client(httpx.MockTransport(handler)))
    assert calls["n"] == 1


def test_size_limit_enforced_while_streaming(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 5000)

    with pytest.raises(DownloadError, match="limite"):
        download(
            "https://a.org/f",
            tmp_path / "f",
            client(httpx.MockTransport(handler)),
            max_bytes=1000,
        )
    assert not (tmp_path / "f").exists()
