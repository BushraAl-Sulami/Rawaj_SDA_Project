import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from utils.media_processor import (
    image_url_to_base64,
    extract_video_frames
)


load_dotenv(override=True)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY was not found in .env"
    )

client = OpenAI(
    api_key=OPENAI_API_KEY
)


def analyze_post(post: dict):

    caption = (
        post.get("caption")
        or ""
    )

    post_type = (
        post.get("type")
        or "unknown"
    )

    content = [
        {
            "type": "input_text",
            "text": f"""
You are a marketing analyst specializing in restaurant social media.

Analyze this Instagram post based only on the evidence provided.

POST INFORMATION

Caption:
{caption}

Post type:
{post_type}

Likes:
{post.get("likes")}

Comments:
{post.get("comments")}

Published at:
{post.get("timestamp")}

Post URL:
{post.get("post_url")}

Analyze:

1. What the post is communicating.
2. Strengths of the content.
3. Possible marketing weaknesses or gaps.
4. Whether there is a clear call to action.
5. Whether the branding or marketing message is clear.
6. Whether the post encourages audience engagement.
7. Opportunities for improvement.

Important rules:

- Do not invent information.
- Use only the caption, visual evidence, and metadata provided.
- Do not make conclusions about the entire Instagram account from one post.
- If something cannot be determined from the available evidence, say so.

Return valid JSON only.

Use exactly this structure:

{{
    "summary": "",
    "strengths": [],
    "marketing_gaps": [],
    "cta": {{
        "present": false,
        "evidence": ""
    }},
    "branding_observation": "",
    "engagement_observation": "",
    "improvement_opportunities": [],
    "evidence_used": []
}}
"""
        }
    ]


    # -----------------------------
    # IMAGE POST
    # -----------------------------

    if post_type.lower() == "image":

        image_url = post.get(
            "image_url"
        )

        if image_url:

            image_base64 = (
                image_url_to_base64(
                    image_url
                )
            )

            content.append(
                {
                    "type": "input_image",
                    "image_url": image_base64
                }
            )


    # -----------------------------
    # REEL / VIDEO POST
    # -----------------------------

    elif post_type.lower() in [
        "reel",
        "video"
    ]:

        video_url = post.get(
            "video_url"
        )

        if video_url:

            frames = extract_video_frames(
                video_url,
                number_of_frames=4
            )

            for frame in frames:

                content.append(
                    {
                        "type": "input_image",
                        "image_url": frame
                    }
                )

        else:

            # fallback to cover image

            image_url = post.get(
                "image_url"
            )

            if image_url:

                image_base64 = (
                    image_url_to_base64(
                        image_url
                    )
                )

                content.append(
                    {
                        "type": "input_image",
                        "image_url": image_base64
                    }
                )


    # -----------------------------
    # CAROUSEL
    # -----------------------------

    elif post_type.lower() == "carousel":

        carousel_media = (
            post.get("carousel_media")
            or []
        )

        for media in carousel_media:

            media_url = None

            if isinstance(
                media,
                str
            ):
                media_url = media

            elif isinstance(
                media,
                dict
            ):

                media_url = (
                    media.get("image_url")
                    or media.get("url")
                )

            if media_url:

                image_base64 = (
                    image_url_to_base64(
                        media_url
                    )
                )

                content.append(
                    {
                        "type": "input_image",
                        "image_url": image_base64
                    }
                )


    # -----------------------------
    # FALLBACK
    # -----------------------------

    else:

        image_url = post.get(
            "image_url"
        )

        if image_url:

            image_base64 = (
                image_url_to_base64(
                    image_url
                )
            )

            content.append(
                {
                    "type": "input_image",
                    "image_url": image_base64
                }
            )


    response = client.responses.create(
        model="gpt-5.6-luna",
        input=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    raw_result = (
        response.output_text
    )

    try:

        return json.loads(
            raw_result
        )

    except json.JSONDecodeError:

        return {
            "raw_analysis": raw_result
        }


def analyze_posts(
    posts: list[dict]
):

    analyses = []

    for index, post in enumerate(
        posts,
        start=1
    ):

        print(
            f"Analyzing post "
            f"{index}/{len(posts)}..."
        )

        try:

            result = analyze_post(
                post
            )

            analyses.append(
                {
                    "post_url":
                        post.get(
                            "post_url"
                        ),

                    "type":
                        post.get(
                            "type"
                        ),

                    "analysis":
                        result
                }
            )

        except Exception as error:

            print(
                f"Failed to analyze "
                f"post {index}: {error}"
            )

            analyses.append(
                {
                    "post_url":
                        post.get(
                            "post_url"
                        ),

                    "type":
                        post.get(
                            "type"
                        ),

                    "error":
                        str(error)
                }
            )

    return analyses