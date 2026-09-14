import os

from apify_client import ApifyClient
from dotenv import load_dotenv


load_dotenv(override=True)

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

if not APIFY_API_TOKEN:
    raise ValueError("APIFY_API_TOKEN was not found in .env")

client = ApifyClient(APIFY_API_TOKEN)


def get_instagram_posts(username: str, limit: int = 5):

    run_input = {
        "username": [username],
        "resultsLimit": limit,
        "dataDetailLevel": "basicData"
    }

    run = client.actor(
        "apify/instagram-post-scraper"
    ).call(run_input=run_input)

    posts = list(
        client.dataset(
            run["defaultDatasetId"]
        ).iterate_items()
    )

    return posts