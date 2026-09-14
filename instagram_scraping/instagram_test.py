import os

from apify_client import ApifyClient
from dotenv import load_dotenv


load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
print("Token loaded:", bool(APIFY_API_TOKEN))
print("Starts with apify_api_:", APIFY_API_TOKEN.startswith("apify_api_") if APIFY_API_TOKEN else False)
if not APIFY_API_TOKEN:
    raise ValueError("APIFY_API_TOKEN was not found in .env")

client = ApifyClient(APIFY_API_TOKEN)



#instagram Post Scraper-APIFY

def get_instagram_posts(username: str, limit: int = 5):

    run_input = {
        "username": [username],
        "resultsLimit": limit
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


#example usage

username = "dunkindonutsksa"

posts = get_instagram_posts(
    username=username,
    limit=5
)

print(f"Found {len(posts)} posts")

for post in posts:
    print("\n--------------------")
    print("Caption:", post.get("caption"))
    print("Post URL:", post.get("url"))
    print("Type:", post.get("type"))
    print("Likes:", post.get("likesCount"))
    print("Comments:", post.get("commentsCount"))




# Sec Actor (No cookie) - APIFY

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


# Get the URLs from Actor 1
post_urls = [
    post["url"]
    for post in posts
    if post.get("url")
]

# Send all URLs to Actor 2
media_results = extract_instagram_media(post_urls)

print("\n\n========== MEDIA RESULTS ==========")

for media in media_results:
    print("\n--------------------")
    print("Post URL:", media.get("post_url"))
    print("Type:", media.get("type"))
    print("Image URL:", media.get("image_url"))
    print("Video URL:", media.get("video_url"))
    print("Carousel Count:", media.get("carousel_count"))
    print("Carousel Media:", media.get("carousel_media"))