import os
from typing import Any

import httpx


class TwelveDataProvider:
    BASE_URL = "https://api.twelvedata.com"

    def __init__(self) -> None:
        self.api_key = os.getenv("TWELVE_DATA_API_KEY")
        self.symbol = os.getenv("XAUUSD_DATA_SYMBOL", "XAU/USD")

    async def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.api_key:
            return {
                "status": "error",
                "error": "TWELVE_DATA_API_KEY is not configured",
            }

        params["apikey"] = self.api_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def quote(self) -> dict[str, Any]:
        return await self._get(
            "quote",
            {
                "symbol": self.symbol,
            },
        )

    async def candles(
        self,
        interval: str = "5min",
        outputsize: int = 100,
    ) -> dict[str, Any]:
        return await self._get(
            "time_series",
            {
                "symbol": self.symbol,
                "interval": interval,
                "outputsize": outputsize,
                "format": "JSON",
            },
        )


market_provider = TwelveDataProvider()
