from datetime import datetime, timezone
from typing import Any

from market_provider import market_provider


class MarketEngine:
    def __init__(self) -> None:
        self.symbol = "XAUUSD"

    def status(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "symbol": self.symbol,
            "provider": "twelve_data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def snapshot(self) -> dict[str, Any]:
        quote = await market_provider.quote()

        if quote.get("status") == "error":
            return {
                "symbol": self.symbol,
                "status": "error",
                "provider": "twelve_data",
                "error": quote.get("error"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "symbol": self.symbol,
            "status": "live",
            "provider": "twelve_data",
            "price": quote.get("close") or quote.get("price"),
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
            "change": quote.get("change"),
            "percent_change": quote.get("percent_change"),
            "timestamp": quote.get("timestamp")
            or datetime.now(timezone.utc).isoformat(),
        }

    async def candles(
        self,
        timeframe: str = "M5",
        limit: int = 100,
    ) -> dict[str, Any]:
        intervals = {
            "1M": "1min",
            "5M": "5min",
            "15M": "15min",
            "30M": "30min",
            "1H": "1h",
            "4H": "4h",
            "1D": "1day",
        }

        timeframe = timeframe.upper()
        interval = intervals.get(timeframe, "5min")

        data = await market_provider.candles(interval, limit)

        if data.get("status") == "error":
            return {
                "symbol": self.symbol,
                "timeframe": timeframe,
                "status": "error",
                "error": data.get("error"),
                "candles": [],
            }

        return {
            "symbol": self.symbol,
            "timeframe": timeframe,
            "status": "live",
            "provider": "twelve_data",
            "candles": data.get("values", []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


market_engine = MarketEngine()
