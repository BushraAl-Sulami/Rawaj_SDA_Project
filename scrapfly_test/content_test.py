import os
import json
import time

from dotenv import load_dotenv
from scrapfly import ScrapflyClient, ScrapeConfig

load_dotenv()

client = ScrapflyClient(
    key=os.getenv("SCRAPFLY_API_KEY")
)

PROFILE_URL = "https://www.instagram.com/lute.ksa/"
#PROFILE_URL = "https://www.instagram.com/burger_site/"


# --------------------------------------------------
# 1. Scrape Instagram profile + recent post URLs
# --------------------------------------------------

def scrape_profile(profile_url):

    result = client.scrape(
        ScrapeConfig(
            url=profile_url,
            asp=True,
            render_js=True,

            extraction_prompt="""
            Extract information from this public Instagram profile.

            Return JSON containing:

            - username
            - display_name
            - bio
            - followers_count
            - following_count
            - posts_count

            Also extract visible recent Instagram posts and reels.

            Return them as:

            "recent_posts": [
                {
                    "url": "",
                    "type": ""
                }
            ]

            Only return URLs that actually exist.
            Do not invent information.
            """
        )
    )

    return result.scrape_result["extracted_data"]["data"]


# --------------------------------------------------
# 2. Scrape one Instagram post
# --------------------------------------------------

from bs4 import BeautifulSoup


def get_media_fallback(html):
    """
    Fallback: get main image/video from OpenGraph metadata
    if Scrapfly extraction did not return them.
    """

    soup = BeautifulSoup(html, "html.parser")

    image_url = None
    video_url = None

    image_tag = soup.find(
        "meta",
        property="og:image"
    )

    if image_tag:
        image_url = image_tag.get("content")

    video_tag = (
        soup.find("meta", property="og:video")
        or soup.find("meta", property="og:video:secure_url")
    )

    if video_tag:
        video_url = video_tag.get("content")

    return image_url, video_url


def scrape_post(post_url):

    result = client.scrape(
        ScrapeConfig(
            url=post_url,
            asp=True,
            render_js=True,

            extraction_prompt="""
            Extract information from THIS public Instagram post only.

            Return JSON containing:

            - username
            - caption
            - publication_date
            - likes_count
            - comments_count
            - media_type
            - hashtags
            - mentions

            Also extract the post media:

            - image_urls
            - video_url
            - thumbnail_url

            Rules:

            image_urls:
            - Return a JSON array.
            - For a normal image post, return the image URL.
            - For a carousel, return ALL image URLs belonging to
              this Instagram post when available.
            - Do not include profile pictures, suggested posts,
              logos or unrelated page images.

            video_url:
            - If this post is a Reel or video, return the actual
              video URL when it is available in the page.
            - Otherwise return null.

            thumbnail_url:
            - For a Reel/video, return its cover/thumbnail if available.
            - Otherwise return null.

            Do not invent URLs.

            If information is unavailable, return null.
            """
        )
    )

    data = (
        result.scrape_result
        ["extracted_data"]
        ["data"]
    )

    # --------------------------------------------------
    # Normalize media fields
    # --------------------------------------------------

    if not data.get("image_urls"):
        data["image_urls"] = []

    if isinstance(data["image_urls"], str):
        data["image_urls"] = [
            data["image_urls"]
        ]

    # --------------------------------------------------
    # Fallback using HTML metadata
    # --------------------------------------------------

    html = result.scrape_result.get(
        "content",
        ""
    )

    fallback_image, fallback_video = (
        get_media_fallback(html)
    )

    if (
        not data["image_urls"]
        and fallback_image
    ):
        data["image_urls"] = [
            fallback_image
        ]

    if (
        not data.get("video_url")
        and fallback_video
    ):
        data["video_url"] = (
            fallback_video
        )

    return data


# --------------------------------------------------
# 3. Main program
# --------------------------------------------------

print("Scraping profile...")

profile = scrape_profile(PROFILE_URL)

print(f"Profile: {profile['username']}")
print(f"Followers: {profile['followers_count']}")

post_urls = profile.get("recent_posts", [])

print(f"Found {len(post_urls)} posts")

all_posts = []


# --------------------------------------------------
# 4. Scrape every post
# --------------------------------------------------

for index, post in enumerate(post_urls, start=1):

    url = post["url"]

    print(f"\nScraping post {index}/{len(post_urls)}")
    print(url)

    try:

        post_data = scrape_post(url)

        post_data["url"] = url

        all_posts.append(post_data)

        print("Done")

        # Small delay between requests
        time.sleep(2)

    except Exception as e:

        print(f"Failed: {e}")


# --------------------------------------------------
# 5. Final structured result
# --------------------------------------------------

output = {

    "profile": {
        "username": profile.get("username"),
        "display_name": profile.get("display_name"),
        "bio": profile.get("bio"),
        "followers_count": profile.get("followers_count"),
        "following_count": profile.get("following_count"),
        "posts_count": profile.get("posts_count")
    },

    "posts": all_posts
}


# --------------------------------------------------
# 6. Save to JSON
# --------------------------------------------------

with open(
    "instagram_data_burgerSite.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        output,
        file,
        ensure_ascii=False,
        indent=2
    )


print("\n==============================")
print("Scraping completed!")
print(f"Posts scraped: {len(all_posts)}")
print("Saved to instagram_data_burgerSite.json")
print("==============================")