import json
import os
import re

from actors.instagram_profile import get_instagram_profile
from utils.restaurant_loader import load_restaurants

from actors.instagram_posts import (
    get_instagram_posts
)

from actors.instagram_media import (
    extract_instagram_media
)

from utils.data_merger import (
    merge_posts_with_media
)

from analysis.marketing_analyzer import (
    analyze_posts
)


# ==========================================
# SETTINGS
# ==========================================

OUTPUT_FOLDER = "outputs"

csv_path = "data/restaurants.csv"

number_of_restaurants = 20
number_of_posts = 1

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def extract_instagram_username(instagram_value: str):

    value = instagram_value.strip().rstrip("/")

    if "instagram.com/" in value:

        username = (
            value
            .split("instagram.com/")[-1]
            .split("/")[0]
        )

        return username

    return value.replace("@", "")


def safe_folder_name(name: str):

    name = name.strip()

    name = re.sub(
        r'[^\w\-]+',
        '_',
        name
    )

    return name.strip("_")


# ==========================================
# LOAD RESTAURANTS FROM CSV
# ==========================================

restaurants = load_restaurants(
    csv_path
)


# Keep only restaurants with Instagram
restaurants_with_instagram = [
    restaurant
    for restaurant in restaurants
    if isinstance(
        restaurant.get("Instagram (Company)"),
        str
    )
    and restaurant[
        "Instagram (Company)"
    ].strip()
]


# Select only 2 restaurants
selected_restaurants = (
    restaurants_with_instagram[
        :number_of_restaurants
    ]
)


print(
    f"\nSelected "
    f"{len(selected_restaurants)} restaurants:"
)


for restaurant in selected_restaurants:

    print(
        "-",
        restaurant["Name"],
        "->",
        restaurant["Instagram (Company)"]
    )


# ==========================================
# RUN PIPELINE FOR EACH RESTAURANT
# ==========================================

for index, restaurant in enumerate(
    selected_restaurants,
    start=1
):

    restaurant_name = restaurant["Name"]

    instagram_value = restaurant[
        "Instagram (Company)"
    ]

    username = extract_instagram_username(
        instagram_value
    )


    print(
        "\n\n=========================================="
    )

    print(
        f"RESTAURANT {index}/"
        f"{len(selected_restaurants)}"
    )

    print(
        "Restaurant:",
        restaurant_name
    )

    print(
        "Instagram:",
        username
    )

    print(
        "=========================================="
    )


    # ======================================
    # CREATE RESTAURANT OUTPUT FOLDER
    # ======================================

    restaurant_folder = os.path.join(
        OUTPUT_FOLDER,
        safe_folder_name(
            restaurant_name
        )
    )

    os.makedirs(
        restaurant_folder,
        exist_ok=True
    )


    # ======================================
    # STEP 1: PROFILE DATA
    # ======================================

    print(
        "\nSTEP 1: Getting Instagram profile..."
    )

    profile = get_instagram_profile(
        username
    )


    profile_data = {
        "restaurant_name":
            restaurant_name,

        "username":
            profile.get("username"),

        "full_name":
            profile.get("fullName"),

        "biography":
            profile.get("biography"),

        "followers":
            profile.get("followersCount"),

        "following":
            profile.get("followsCount"),

        "posts_count":
            profile.get("postsCount"),

        "verified":
            profile.get("verified")
    }


    with open(
        os.path.join(
            restaurant_folder,
            "profile.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            profile_data,
            file,
            ensure_ascii=False,
            indent=2
        )


    print(
        "Followers:",
        profile_data["followers"]
    )


    # ======================================
    # STEP 2: ACTOR 1 - GET 15 POSTS
    # ======================================

    print(
        f"\nSTEP 2: Getting latest "
        f"{number_of_posts} posts..."
    )


    posts = get_instagram_posts(
    username=username,
    limit=number_of_posts
   )

# Sort posts by timestamp: newest -> oldest
    posts = sorted(
    posts,
    key=lambda post: post.get("timestamp") or "",
    reverse=True
   )

# Make sure we keep only the latest 15 posts
    posts = posts[:number_of_posts]


    with open(
        os.path.join(
            restaurant_folder,
            "posts.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            posts,
            file,
            ensure_ascii=False,
            indent=2
        )


    print(
        f"Found {len(posts)} posts."
    )


    # ======================================
    # STEP 3: ACTOR 2 - EXTRACT MEDIA
    # ======================================

    print(
        "\nSTEP 3: Extracting media..."
    )


    post_urls = [
        post["url"]
        for post in posts
        if post.get("url")
    ]


    media_results = (
        extract_instagram_media(
            post_urls
        )
    )


    with open(
        os.path.join(
            restaurant_folder,
            "media.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            media_results,
            file,
            ensure_ascii=False,
            indent=2
        )


    print(
        f"Extracted media for "
        f"{len(media_results)} posts."
    )


    # ======================================
    # STEP 4: MERGE DATA
    # ======================================

    print(
        "\nSTEP 4: Merging post data..."
    )


    merged_posts = (
        merge_posts_with_media(
            posts,
            media_results
        )
    )


    with open(
        os.path.join(
            restaurant_folder,
            "merged_posts.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            merged_posts,
            file,
            ensure_ascii=False,
            indent=2
        )


    print(
        "Merged data saved."
    )


    # ======================================
    # STEP 5: AI ANALYSIS
    # ======================================

    print(
        "\nSTEP 5: Analyzing posts..."
    )


    analysis_results = (
        analyze_posts(
            merged_posts
        )
    )


    with open(
        os.path.join(
            restaurant_folder,
            "analysis.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            analysis_results,
            file,
            ensure_ascii=False,
            indent=2
        )


    print(
        f"\nCompleted: "
        f"{restaurant_name}"
    )


# ==========================================
# COMPLETE
# ==========================================

print(
    "\n\n=========================================="
)

print(
    "PIPELINE COMPLETED FOR ALL RESTAURANTS"
)

print(
    "=========================================="
)