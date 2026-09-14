import os

from apify_client import ApifyClient
from dotenv import load_dotenv


load_dotenv(override=True)

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

if not APIFY_API_TOKEN:
    raise ValueError("APIFY_API_TOKEN was not found in .env")

client = ApifyClient(APIFY_API_TOKEN)


def get_instagram_profile(username: str):

    run_input = {
        "usernames": [username]
    }

    run = client.actor(
        "apify/instagram-profile-scraper"
    ).call(run_input=run_input)

    profiles = list(
        client.dataset(
            run["defaultDatasetId"]
        ).iterate_items()
    )

    if not profiles:
        return {}

    return profiles[0]