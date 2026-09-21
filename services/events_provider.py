from datetime import date
from typing import Any

import httpx

from config import settings


class EventsProviderError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")


class EventsProviderClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or settings.events_provider_url).rstrip("/")
        self.api_key = api_key or settings.events_provider_api_key

        if not self.api_key:
            raise ValueError("EVENTS_PROVIDER_API_KEY is not configured")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "x-api-key": self.api_key,
                "Accept": "application/json",
            },
            timeout=timeout,
            follow_redirects=True,
        )

    async def __aenter__(self) -> "EventsProviderClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.is_success:
            try:
                return response.json()
            except ValueError:
                raise EventsProviderError(
                    response.status_code, "Response is not valid JSON"
                ) from None

        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:500]

        raise EventsProviderError(response.status_code, str(detail))

    async def fetch_events(self, changed_at: date) -> list[dict]:
        events: list[dict] = []
        url: str | None = "/api/events/"
        params: dict | None = {"changed_at": changed_at.isoformat()}

        while url:
            response = await self._client.get(url, params=params)
            data = self._handle_response(response)

            events.extend(data.get("results", []))

            url = data.get("next")
            params = None

        return events

    async def fetch_seats(self, event_id: str) -> list[str]:
        response = await self._client.get(f"/api/events/{event_id}/seats/")
        data = self._handle_response(response)
        return data.get("seats", [])

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        seat: str,
        email: str,
    ) -> str:
        response = await self._client.post(
            f"/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "seat": seat,
                "email": email,
            },
        )
        data = self._handle_response(response)
        return data["ticket_id"]

    async def unregister(self, event_id: str, ticket_id: str) -> bool:
        response = await self._client.request(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": ticket_id},
        )
        data = self._handle_response(response)
        return bool(data.get("success", False))
