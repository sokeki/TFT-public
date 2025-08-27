# riot_api.py
import aiohttp


class RiotAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None  # Session will be created lazily

    async def get_session(self):
        """Create aiohttp session if it doesn't exist yet."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def request(self, url: str, params=None):
        """Generic GET request to Riot API."""
        if params is None:
            params = {}
        params["api_key"] = self.api_key

        session = await self.get_session()
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_summoner(self, region: str, tag: str, name: str):
        """Get summoner info by name."""
        url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        return await self.request(url)

    async def get_league_entries(self, region: str, puuid: str):
        """Get ranked TFT entries for a summoner."""
        url = f"https://{region}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
        return await self.request(url)

    async def get_match_ids(self, routing: str, puuid: str, count: int = 20):
        """Get match IDs for a player."""
        url = f"https://{routing}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
        return await self.request(url, params={"count": count})

    async def get_match(self, routing: str, match_id: str):
        """Get full match info by match ID."""
        url = f"https://{routing}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        return await self.request(url)

    async def close(self):
        """Close aiohttp session if it exists."""
        if self.session:
            await self.session.close()
            self.session = None
