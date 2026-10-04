"""
Shared async HTTP helper used by every service module.

Centralizing this gives us one place to configure: timeouts, the User-Agent
(several of these APIs ask you to identify your client), and retry-on-transient-
failure behavior, instead of repeating try/except boilerplate in ten services.
"""
from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import settings


class UpstreamAPIError(RuntimeError):
    """Raised when an external bioinformatics API returns an error we can't recover from."""

    def __init__(self, service: str, message: str, status_code: int | None = None):
        self.service = service
        self.status_code = status_code
        super().__init__(f"[{service}] {message}" + (f" (HTTP {status_code})" if status_code else ""))


class NotFoundError(UpstreamAPIError):
    """The requested entity (accession, PDB ID, gene, ...) does not exist upstream."""


_RETRYABLE = (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError)


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(_RETRYABLE),
)
async def request_json(
    service: str,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET/POST a URL and return parsed JSON, raising UpstreamAPIError/NotFoundError on failure."""
    merged_headers = {"User-Agent": settings.user_agent, "Accept": "application/json"}
    if headers:
        merged_headers.update(headers)

    async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
        try:
            response = await client.request(
                method, url, params=params, json=json_body, headers=merged_headers
            )
        except httpx.TimeoutException as exc:
            raise UpstreamAPIError(service, f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise UpstreamAPIError(service, f"Network error: {exc}") from exc

    if response.status_code == 404:
        raise NotFoundError(service, "Resource not found", status_code=404)
    if response.status_code == 429:
        raise UpstreamAPIError(service, "Rate limited by upstream API", status_code=429)
    if response.status_code >= 400:
        raise UpstreamAPIError(service, response.text[:300], status_code=response.status_code)

    if not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise UpstreamAPIError(service, f"Non-JSON response: {exc}") from exc


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(_RETRYABLE),
)
async def request_text(
    service: str, method: str, url: str, *, params: dict[str, Any] | None = None
) -> str:
    """GET/POST a URL and return the raw text body (used for FASTA, PDB/CIF files, XML)."""
    merged_headers = {"User-Agent": settings.user_agent}
    async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
        try:
            response = await client.request(method, url, params=params, headers=merged_headers)
        except httpx.TimeoutException as exc:
            raise UpstreamAPIError(service, f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise UpstreamAPIError(service, f"Network error: {exc}") from exc

    if response.status_code == 404:
        raise NotFoundError(service, "Resource not found", status_code=404)
    if response.status_code >= 400:
        raise UpstreamAPIError(service, response.text[:300], status_code=response.status_code)

    return response.text
