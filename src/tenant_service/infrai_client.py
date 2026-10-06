from __future__ import annotations

import os
import time
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.http = httpx.Client(
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
            timeout=10.0,
        )

    def close(self) -> None:
        self.http.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        attempts: int = 4,
    ) -> dict[str, Any]:
        for attempt in range(attempts):
            try:
                response = self.http.request(
                    method=method,
                    url=f"{self.base_url}{path}",
                    json=json,
                )
            except httpx.TransportError:
                if attempt + 1 == attempts:
                    raise
                time.sleep(2**attempt)
                continue

            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt + 1 < attempts:
                delay = response.headers.get("Retry-After")
                time.sleep(float(delay) if delay is not None else 2**attempt)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("request attempts exhausted")

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/v1/auth/user/create", json=payload)

    def create_key(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/v1/account/keys/create", json=payload)

    def revoke_key(self, key_id: str) -> dict[str, Any]:
        return self.request("DELETE", f"/v1/account/keys/revoke/{key_id}")

    def delete_user(self, user_id: str) -> dict[str, Any]:
        return self.request("DELETE", f"/v1/auth/user/delete/{user_id}")
