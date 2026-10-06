import httpx

from config import settings

class CapashinoError(Exception):
    def __init__(self, status_code: int, details: str):
        self.status_code = status_code
        self.details = details
        super().__init__(f"[{status_code}] {details}")

class CapashinoClient:
    def __init__(
            self,
            base_url: str | None = None,
            api_key: str | None = None,
            timeout: float = 10.0,
    ):
        self.base_url = (base_url or settings.capashino_url).rstrip("/")
        self.api_key = api_key or settings.capashino_api_key
        if not self.api_key:
            raise ValueError("CAPASHINO_API_KEY is not configured")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout
        )

    async def __aenter__(self) -> "CapashinoClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def send_notification(
            self,
            message: str,
            reference_id: str,
            idempotency_key: str,
    ) -> dict:
        response = await self._client.post(
            "/api/notifications",
            json = {
                "message": message,
                "reference_id": reference_id,
                "idempotency_key": idempotency_key,
            },
        )

        if not response.is_success:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text[:500]
            raise CapashinoError(response.status_code, str(detail))

        return response.json()