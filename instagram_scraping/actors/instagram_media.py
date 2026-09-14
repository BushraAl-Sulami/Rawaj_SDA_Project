import os

from apify_client import ApifyClient
from dotenv import load_dotenv


load_dotenv(override=True)

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

if not APIFY_API_TOKEN:
    raise ValueError("APIFY_API_TOKEN was not found in .env")

client = ApifyClient(APIFY_API_TOKEN)


def extract_instagram_media(post_urls: list[str]):

    run_input = {
        "post_urls": post_urls
    }

    run = client.actor(
        "mina_safwat/instagram-post-scraper-no-cookies"
    ).call(run_input=run_input)

    results = list(
        client.dataset(
            run["defaultDatasetId"]
        ).iterate_items()
    )

    return results