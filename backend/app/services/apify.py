from __future__ import annotations

from typing import Optional

import httpx

from app.config import settings


APIFY_BASE = "https://api.apify.com/v2"
# Actor IDs use ~ instead of / in URL paths
INSTAGRAM_ACTOR = "apify~instagram-scraper"


async def fetch_instagram_post(url: str) -> Optional[dict]:
    """
    Scrape one Instagram post/reel for accurate metadata.

    Why this exists: yt-dlp's anonymous scrape can't return play_count
    because Instagram only exposes it to authenticated GraphQL clients,
    which means engagement_rate ends up 0 for IG. Apify hits IG's real
    internal endpoints and returns the full payload (views, follower
    counts, hashtags as a real list, etc.).

    Cost: ~$0.0005 per result. At 1000 creators/day = $0.50/day,
    which is the cheapest reliable way to get IG metrics short of
    paying for the official Meta Graph API (which is enterprise-only
    for non-IG-business accounts).

    Returns the raw item dict or None on failure — caller should
    gracefully merge with yt-dlp's partial data.
    """
    if not settings.apify_api_token:
        return None

    run_url = f"{APIFY_BASE}/acts/{INSTAGRAM_ACTOR}/run-sync-get-dataset-items"
    params = {"token": settings.apify_api_token}
    body = {
        "directUrls": [url],
        "resultsType": "posts",
        "resultsLimit": 1,
        "addParentData": True,  # includes owner profile with follower count
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(run_url, params=params, json=body)
            resp.raise_for_status()
            items = resp.json()
        return items[0] if items else None
    except Exception:
        # Apify can fail (rate limits, IG blocking, actor down). We swallow
        # because yt-dlp already gave us a degraded-but-usable payload.
        return None