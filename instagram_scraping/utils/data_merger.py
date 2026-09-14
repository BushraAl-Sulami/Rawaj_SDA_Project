def merge_posts_with_media(posts, media_results):

    media_by_url = {
        item.get("post_url"): item
        for item in media_results
        if item.get("post_url")
    }

    merged_posts = []

    for post in posts:

        post_url = post.get("url")
        media = media_by_url.get(post_url, {})

        merged_post = {
            "post_url": post_url,
            "caption": post.get("caption"),
            "type": media.get("type") or post.get("type"),
            "likes": post.get("likesCount"),
            "comments": post.get("commentsCount"),
            "timestamp": post.get("timestamp"),

            "image_url": media.get("image_url"),
            "video_url": media.get("video_url"),

            "carousel_count": media.get("carousel_count"),
            "carousel_media": media.get("carousel_media", [])
        }

        merged_posts.append(merged_post)

    return merged_posts