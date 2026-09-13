import os
import json
import base64
import tempfile
from datetime import datetime

import cv2
import numpy as np
import requests

from dotenv import load_dotenv
from openai import OpenAI


# =========================================================
# 1. Configuration
# =========================================================

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Input produced by content_test.py
INPUT_FILE = os.getenv(
    "INSTAGRAM_INPUT_FILE",
    "instagram_data_burgerSite.json"
)

# Final research analysis
OUTPUT_FILE = os.getenv(
    "INSTAGRAM_OUTPUT_FILE",
    "instagram_analysis_burgerSite.json"
)

# You can also set this inside .env:
# OPENAI_MODEL=gpt-5.6-luna

MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna"
)

# Maximum number of carousel/images analyzed per post
MAX_IMAGES_PER_POST = 10

# Maximum number of frames sampled from each Reel/video
MAX_VIDEO_FRAMES = 6

REQUEST_TIMEOUT = 60


# =========================================================
# 2. HTTP headers
# =========================================================

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://www.instagram.com/"
}


# =========================================================
# 3. Load Instagram data collected by Scrapfly
# =========================================================

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


profile = data.get(
    "profile",
    {}
)

posts = data.get(
    "posts",
    []
)

username = profile.get(
    "username",
    "unknown"
)


print(
    f"\nAnalyzing Instagram account: "
    f"@{username}"
)

print(
    f"Posts collected: {len(posts)}"
)


# =========================================================
# 4. Parse Instagram post dates
# =========================================================

def parse_date(date_text):
    """
    Convert Instagram publication date into datetime.

    Supports common human-readable and ISO date formats.
    """

    if not date_text:
        return None

    date_text = str(
        date_text
    ).strip()

    # ---------------------------------------------
    # Try ISO format first
    # ---------------------------------------------

    try:

        iso_text = date_text.replace(
            "Z",
            "+00:00"
        )

        return datetime.fromisoformat(
            iso_text
        ).replace(
            tzinfo=None
        )

    except ValueError:
        pass

    # ---------------------------------------------
    # Other possible formats
    # ---------------------------------------------

    formats = [
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d %B %Y",
        "%d %b %Y"
    ]

    for date_format in formats:

        try:

            return datetime.strptime(
                date_text,
                date_format
            )

        except ValueError:
            continue

    return None


# =========================================================
# 5. Prepare posts with parsed dates
# =========================================================

parsed_posts = []

for post in posts:

    parsed_date = parse_date(
        post.get(
            "publication_date"
        )
    )

    if parsed_date:

        parsed_posts.append(
            {
                **post,
                "parsed_date": parsed_date
            }
        )


parsed_posts.sort(
    key=lambda x: x["parsed_date"],
    reverse=True
)


# =========================================================
# 6. Posting Activity
# =========================================================

posts_per_week = 0

if len(parsed_posts) >= 2:

    newest_date = (
        parsed_posts[0]
        ["parsed_date"]
    )

    oldest_date = (
        parsed_posts[-1]
        ["parsed_date"]
    )

    total_days = (
        newest_date
        - oldest_date
    ).days

    if total_days > 0:

        posts_per_week = (
            len(parsed_posts)
            / (total_days / 7)
        )


# =========================================================
# 7. Posting Consistency
# =========================================================

gaps = []

for i in range(
    len(parsed_posts) - 1
):

    current_date = (
        parsed_posts[i]
        ["parsed_date"]
    )

    next_date = (
        parsed_posts[i + 1]
        ["parsed_date"]
    )

    gap = (
        current_date
        - next_date
    ).days

    gaps.append(
        gap
    )


average_gap_days = (
    sum(gaps) / len(gaps)
    if gaps
    else 0
)

largest_gap_days = (
    max(gaps)
    if gaps
    else 0
)


# =========================================================
# 8. Normalize image URLs
# =========================================================

def normalize_image_urls(value):
    """
    Convert image_urls into a clean list.

    Accepts:
    null
    string
    list
    """

    if not value:
        return []

    if isinstance(
        value,
        str
    ):

        value = [
            value
        ]

    if not isinstance(
        value,
        list
    ):
        return []

    cleaned = []

    for url in value:

        if (
            isinstance(url, str)
            and url.strip()
        ):

            url = url.strip()

            if url not in cleaned:
                cleaned.append(
                    url
                )

    return cleaned


# =========================================================
# 9. Download Instagram image
# =========================================================

def image_url_to_data_url(
    image_url
):
    """
    Download remote Instagram image and convert it
    into JPEG base64 suitable for multimodal analysis.

    Re-encoding as JPEG avoids unsupported image
    MIME-type issues.
    """

    response = requests.get(
        image_url,
        headers=HTTP_HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    image_bytes = np.frombuffer(
        response.content,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        image_bytes,
        cv2.IMREAD_COLOR
    )

    if image is None:

        raise ValueError(
            "Downloaded content could not "
            "be decoded as an image."
        )

    success, buffer = cv2.imencode(
        ".jpg",
        image,
        [
            int(
                cv2.IMWRITE_JPEG_QUALITY
            ),
            85
        ]
    )

    if not success:

        raise ValueError(
            "Could not convert image to JPEG."
        )

    encoded = base64.b64encode(
        buffer.tobytes()
    ).decode(
        "utf-8"
    )

    return (
        "data:image/jpeg;base64,"
        + encoded
    )


# =========================================================
# 10. Download Instagram Reel/video
# =========================================================

def download_video(
    video_url
):
    """
    Download Instagram Reel/video to a temporary MP4 file.
    """

    response = requests.get(
        video_url,
        headers=HTTP_HEADERS,
        stream=True,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    temp_file = (
        tempfile.NamedTemporaryFile(
            suffix=".mp4",
            delete=False
        )
    )

    try:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:

                temp_file.write(
                    chunk
                )

    finally:

        temp_file.close()

    return temp_file.name


# =========================================================
# 11. Extract representative video frames
# =========================================================

def extract_video_frames(
    video_url,
    max_frames=6
):
    """
    Download video and sample representative frames
    evenly throughout the Reel.

    Returns:
    [
        {
            "timestamp_seconds": 1.5,
            "image": "data:image/jpeg;base64,..."
        }
    ]
    """

    video_path = None

    extracted_frames = []

    capture = None

    try:

        video_path = download_video(
            video_url
        )

        capture = cv2.VideoCapture(
            video_path
        )

        if not capture.isOpened():

            raise ValueError(
                "OpenCV could not open "
                "the downloaded video."
            )

        frame_count = int(
            capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        fps = capture.get(
            cv2.CAP_PROP_FPS
        )

        if not fps or fps <= 0:

            fps = 30

        if frame_count <= 0:

            raise ValueError(
                "Could not determine "
                "video frame count."
            )

        duration_seconds = (
            frame_count / fps
        )

        # ---------------------------------------------
        # Avoid exact first/last frame because those
        # may be black frames or transitions.
        # ---------------------------------------------

        percentages = np.linspace(
            0.05,
            0.95,
            max_frames
        )

        for percentage in percentages:

            timestamp = (
                duration_seconds
                * float(percentage)
            )

            capture.set(
                cv2.CAP_PROP_POS_MSEC,
                timestamp * 1000
            )

            success, frame = (
                capture.read()
            )

            if not success:
                continue

            success, buffer = (
                cv2.imencode(
                    ".jpg",
                    frame,
                    [
                        int(
                            cv2.IMWRITE_JPEG_QUALITY
                        ),
                        80
                    ]
                )
            )

            if not success:
                continue

            encoded = (
                base64.b64encode(
                    buffer.tobytes()
                )
                .decode(
                    "utf-8"
                )
            )

            extracted_frames.append(
                {
                    "timestamp_seconds": round(
                        timestamp,
                        2
                    ),

                    "image": (
                        "data:image/jpeg;base64,"
                        + encoded
                    )
                }
            )

    except Exception as error:

        print(
            f"Video processing failed: "
            f"{error}"
        )

    finally:

        if capture is not None:

            capture.release()

        if (
            video_path
            and os.path.exists(
                video_path
            )
        ):

            try:

                os.remove(
                    video_path
                )

            except OSError:
                pass

    return extracted_frames


# =========================================================
# 12. Clean / parse LLM JSON
# =========================================================

def parse_json_response(
    text
):
    """
    Extract JSON object from model response.
    """

    text = text.strip()

    # ---------------------------------------------
    # Remove Markdown fences
    # ---------------------------------------------

    if text.startswith(
        "```json"
    ):

        text = text[
            len("```json"):
        ]

    elif text.startswith(
        "```"
    ):

        text = text[
            len("```"):
        ]

    if text.endswith(
        "```"
    ):

        text = text[:-3]

    text = text.strip()

    # ---------------------------------------------
    # Try directly
    # ---------------------------------------------

    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError:
        pass

    # ---------------------------------------------
    # Try extracting first JSON object
    # ---------------------------------------------

    first_brace = text.find(
        "{"
    )

    last_brace = text.rfind(
        "}"
    )

    if (
        first_brace != -1
        and last_brace != -1
    ):

        json_text = text[
            first_brace:
            last_brace + 1
        ]

        return json.loads(
            json_text
        )

    raise ValueError(
        "Model did not return valid JSON."
    )


# =========================================================
# 13. Multimodal System Prompt
# =========================================================

SYSTEM_PROMPT = """
You are a marketing research analyst specializing in
restaurant social media analysis.

Your job is to understand Instagram posts semantically
using BOTH textual and visual evidence.

The post may contain:

- a caption
- one image
- multiple carousel images
- frames extracted from an Instagram Reel or video
- Arabic text
- English text
- mixed Arabic and English content

IMPORTANT:

Do NOT rely only on the caption.

Do NOT use simple keyword matching.

Understand the complete marketing meaning and intention
of the post.

Visual evidence may contain important information that
does not appear in the caption.

Examples include:

- prices
- discounts
- promotional offers
- product launches
- menu announcements
- event announcements
- seasonal campaigns
- reservation messages
- delivery information
- ordering information
- calls-to-action
- restaurant experiences
- visual branding

If the caption says very little but an image contains
important marketing information, use the visual evidence.

For Reel/video posts, the provided images may represent
frames sampled from different moments of the video.

Treat them as parts of the same video.

Do not invent details that cannot be supported by the
caption or visual evidence.

Understand Arabic, English and mixed-language content
naturally.

Return ONLY valid JSON.
"""


# =========================================================
# 14. Analyze one Instagram post
# =========================================================

def analyze_single_post(
    post,
    post_id
):
    """
    Analyze caption + carousel images + Reel frames.
    """

    print(
        f"\n{'-' * 60}"
    )

    print(
        f"Analyzing post "
        f"{post_id}/{len(posts)}"
    )

    caption = (
        post.get(
            "caption"
        )
        or ""
    )

    publication_date = (
        post.get(
            "publication_date"
        )
    )

    media_type = (
        post.get(
            "media_type"
        )
    )

    post_url = (
        post.get(
            "url"
        )
    )

    image_urls = normalize_image_urls(
        post.get(
            "image_urls"
        )
    )

    video_url = (
        post.get(
            "video_url"
        )
    )

    thumbnail_url = (
        post.get(
            "thumbnail_url"
        )
    )

    # Some extraction models may return video_url
    # as a list instead of a string.

    if isinstance(
        video_url,
        list
    ):

        video_url = (
            video_url[0]
            if video_url
            else None
        )

    # ---------------------------------------------
    # Build multimodal message
    # ---------------------------------------------

    user_content = [
        {
            "type": "input_text",

            "text": f"""
Analyze Instagram post #{post_id} from restaurant
account @{username}.

POST INFORMATION

Caption:
{caption}

Publication date:
{publication_date}

Media type:
{media_type}

Post URL:
{post_url}

Analyze the complete post using BOTH the caption and
all supplied visual evidence.

Evaluate:

1. PROMOTIONAL ACTIVITY

Determine whether the post has a promotional or
commercial marketing purpose.

Promotional activity could include:

- promoting food/products
- promoting a restaurant experience
- launches
- offers
- discounts
- campaigns
- seasonal activities
- events
- menu items
- delivery
- commercial announcements

Determine this semantically.

Do not rely on specific keywords.


2. CTA USAGE

Determine whether the post encourages the audience
to take an action.

The CTA may appear:

- in the caption
- inside the image
- inside the video frames
- explicitly
- implicitly

Examples include encouraging people to:

- visit
- order
- reserve
- contact
- try
- discover
- attend
- purchase


3. CONTENT THEME

Determine the main content theme yourself.

Do not restrict yourself to a predefined category list.


4. CONTENT PURPOSE

Determine the marketing purpose of the post.

Examples may include:

- awareness
- engagement
- conversion
- information
- relationship building

Choose what best explains the actual post.


5. VISUAL CONTENT

Describe briefly what is visually being communicated.


6. VISUAL PROMOTIONAL TEXT

Identify important promotional text visible inside
images or video frames.

For example:

- offer text
- campaign name
- product launch
- promotional announcement

Do not invent text.


7. OFFERS / DISCOUNTS

Identify any visible:

- price
- percentage discount
- special offer
- limited-time promotion
- bundle
- deal

If none exist, return an empty list.


8. VISUAL CTA

Determine whether a CTA appears visually.

For example:

- Order Now
- Visit Us
- Reserve
- Scan QR
- Available Now

Return null if there is no visual CTA.


9. REASON

Provide a concise evidence-based explanation combining
caption evidence and visual evidence.

Return ONLY this JSON structure:

{{
    "post_id": {post_id},
    "is_promotional": true,
    "has_cta": true,
    "cta_type": "description or null",
    "content_theme": "short semantic category",
    "content_purpose": "short description",
    "visual_content": "short description",
    "visual_promotional_text": [],
    "offers_or_discounts": [],
    "visual_cta": null,
    "reason": "brief evidence-based explanation"
}}
"""
        }
    ]

    visual_inputs_added = 0

    # =====================================================
    # 14A. Add normal / carousel images
    # =====================================================

    if image_urls:

        print(
            f"Images found: "
            f"{len(image_urls)}"
        )

    for image_index, image_url in enumerate(
        image_urls[
            :MAX_IMAGES_PER_POST
        ],
        start=1
    ):

        try:

            print(
                f"Downloading image "
                f"{image_index}..."
            )

            image_data = (
                image_url_to_data_url(
                    image_url
                )
            )

            user_content.append(
                {
                    "type": "input_text",
                    "text": (
                        f"Instagram post "
                        f"image {image_index}:"
                    )
                }
            )

            user_content.append(
                {
                    "type": "input_image",
                    "image_url": image_data,
                    "detail": "high"
                }
            )

            visual_inputs_added += 1

        except Exception as error:

            print(
                f"Could not process image "
                f"{image_index}: {error}"
            )

    # =====================================================
    # 14B. Analyze Reel / video frames
    # =====================================================

    video_frames = []

    if video_url:

        print(
            "Video/Reel URL found."
        )

        print(
            "Downloading video and "
            "extracting frames..."
        )

        video_frames = (
            extract_video_frames(
                video_url,
                MAX_VIDEO_FRAMES
            )
        )

        print(
            f"Video frames extracted: "
            f"{len(video_frames)}"
        )

        for frame_index, frame in enumerate(
            video_frames,
            start=1
        ):

            timestamp = (
                frame[
                    "timestamp_seconds"
                ]
            )

            user_content.append(
                {
                    "type": "input_text",
                    "text": (
                        f"Instagram Reel/video "
                        f"frame {frame_index} "
                        f"at approximately "
                        f"{timestamp} seconds:"
                    )
                }
            )

            user_content.append(
                {
                    "type": "input_image",
                    "image_url": (
                        frame[
                            "image"
                        ]
                    ),
                    "detail": "high"
                }
            )

            visual_inputs_added += 1

    # =====================================================
    # 14C. Thumbnail fallback
    # =====================================================

    if (
        not video_frames
        and thumbnail_url
    ):

        try:

            print(
                "Using video thumbnail "
                "as fallback..."
            )

            thumbnail_data = (
                image_url_to_data_url(
                    thumbnail_url
                )
            )

            user_content.append(
                {
                    "type": "input_text",
                    "text": (
                        "Instagram Reel/video "
                        "thumbnail:"
                    )
                }
            )

            user_content.append(
                {
                    "type": "input_image",
                    "image_url": (
                        thumbnail_data
                    ),
                    "detail": "high"
                }
            )

            visual_inputs_added += 1

        except Exception as error:

            print(
                "Could not process "
                f"thumbnail: {error}"
            )

    print(
        f"Visual inputs sent to model: "
        f"{visual_inputs_added}"
    )

    # =====================================================
    # 14D. Send post to multimodal LLM
    # =====================================================

    response = client.responses.create(

        model=MODEL,

        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": SYSTEM_PROMPT
                    }
                ]
            },

            {
                "role": "user",
                "content": user_content
            }
        ]
    )

    result = parse_json_response(
        response.output_text
    )

    # ---------------------------------------------
    # Add technical metadata
    # ---------------------------------------------

    result[
        "visual_inputs_analyzed"
    ] = visual_inputs_added

    result[
        "images_found"
    ] = len(
        image_urls
    )

    result[
        "video_frames_analyzed"
    ] = len(
        video_frames
    )

    result[
        "source_url"
    ] = post_url

    return result


# =========================================================
# 15. Analyze every Instagram post
# =========================================================

print(
    "\nStarting multimodal content analysis..."
)

post_analyses = []

for index, post in enumerate(
    posts,
    start=1
):

    try:

        analysis = (
            analyze_single_post(
                post,
                index
            )
        )

        post_analyses.append(
            analysis
        )

        print(
            f"Post {index} analysis "
            "completed."
        )

    except Exception as error:

        print(
            f"\nPost {index} "
            f"analysis failed:"
        )

        print(
            error
        )

        # Keep the post in the result even if
        # one LLM/media request fails.

        post_analyses.append(
            {
                "post_id": index,

                "source_url": post.get(
                    "url"
                ),

                "analysis_error": str(
                    error
                )
            }
        )


# =========================================================
# 16. Successful analyses only
# =========================================================

successful_analyses = [
    analysis
    for analysis in post_analyses
    if not analysis.get(
        "analysis_error"
    )
]


# =========================================================
# 17. Generate account-level semantic summary
# =========================================================

def generate_account_summary(
    analyses
):
    """
    Combine individual post analysis into account-level
    marketing research evidence.
    """

    if not analyses:

        return {
            "posts_successfully_analyzed": 0,

            "promotional_posts_count": 0,

            "promotional_activity_summary": (
                "No posts were successfully "
                "analyzed."
            ),

            "cta_posts_count": 0,

            "cta_usage_summary": (
                "No posts were successfully "
                "analyzed."
            ),

            "identified_content_themes": [],

            "content_variety_summary": (
                "No sufficient evidence."
            ),

            "overall_content_summary": (
                "No sufficient evidence."
            )
        }

    # ---------------------------------------------
    # Numerical counts calculated by Python
    # ---------------------------------------------

    promotional_count = sum(
        1
        for item in analyses
        if item.get(
            "is_promotional"
        ) is True
    )

    cta_count = sum(
        1
        for item in analyses
        if item.get(
            "has_cta"
        ) is True
    )

    themes = sorted(
        {
            item.get(
                "content_theme"
            )

            for item in analyses

            if item.get(
                "content_theme"
            )
        }
    )

    summary_prompt = f"""
You are analyzing the overall Instagram marketing
content of restaurant account @{username}.

Below are post-level analyses produced from captions,
images, carousel images and Reel/video frames.

POST ANALYSES:

{json.dumps(
    analyses,
    ensure_ascii=False,
    indent=2
)}

The following counts are already calculated and must
NOT be changed:

Posts successfully analyzed:
{len(analyses)}

Promotional posts:
{promotional_count}

Posts with CTA:
{cta_count}

Detected themes:
{json.dumps(
    themes,
    ensure_ascii=False
)}

Generate an account-level summary.

Evaluate:

1. Promotional Activity

Describe how frequently and strongly the account uses
its Instagram content for promotional/commercial
purposes.


2. CTA Usage

Describe how consistently the restaurant encourages
users to take action.


3. Content Variety

Evaluate the variety of themes, purposes and content
formats observed across the posts.


4. Overall Content

Give a concise overall description of the restaurant's
Instagram marketing approach.

Do NOT qualify the restaurant.

Do NOT give an opportunity score.

Do NOT decide whether Rawaj should contact the
restaurant.

This is research evidence only.

Return ONLY valid JSON:

{{
    "posts_successfully_analyzed": {len(analyses)},
    "promotional_posts_count": {promotional_count},
    "promotional_activity_summary": "",
    "cta_posts_count": {cta_count},
    "cta_usage_summary": "",
    "identified_content_themes": [],
    "content_variety_summary": "",
    "overall_content_summary": ""
}}
"""

    response = client.responses.create(

        model=MODEL,

        input=[
            {
                "role": "system",

                "content": [
                    {
                        "type": "input_text",

                        "text": """
You are a restaurant social-media marketing
research analyst.

Synthesize evidence across multiple Instagram posts.

Do not qualify or score the restaurant.

Return only valid JSON.
"""
                    }
                ]
            },

            {
                "role": "user",

                "content": [
                    {
                        "type": "input_text",
                        "text": summary_prompt
                    }
                ]
            }
        ]
    )

    result = parse_json_response(
        response.output_text
    )

    # ---------------------------------------------
    # Guarantee exact numerical counts
    # ---------------------------------------------

    result[
        "posts_successfully_analyzed"
    ] = len(
        analyses
    )

    result[
        "promotional_posts_count"
    ] = promotional_count

    result[
        "cta_posts_count"
    ] = cta_count

    return result


# =========================================================
# 18. Run account summary
# =========================================================

print(
    "\nGenerating account-level "
    "content summary..."
)

try:

    account_summary = (
        generate_account_summary(
            successful_analyses
        )
    )

    print(
        "Account-level content "
        "summary completed."
    )

except Exception as error:

    print(
        "\nAccount summary failed:"
    )

    print(
        error
    )

    account_summary = {
        "error": str(
            error
        )
    }


# =========================================================
# 19. Combined LLM analysis structure
# =========================================================

llm_analysis = {

    "post_analysis": (
        post_analyses
    ),

    "account_summary": (
        account_summary
    )
}


# =========================================================
# 20. Final Research Agent result
# =========================================================

final_analysis = {

    "profile": {

        "username": profile.get(
            "username"
        ),

        "display_name": profile.get(
            "display_name"
        ),

        "bio": profile.get(
            "bio"
        ),

        "followers_count": profile.get(
            "followers_count"
        ),

        "following_count": profile.get(
            "following_count"
        ),

        "total_profile_posts": profile.get(
            "posts_count"
        ),

        "posts_collected": len(
            posts
        ),

        "posts_successfully_analyzed": len(
            successful_analyses
        )
    },


    # -------------------------------------------------
    # Quantitative research evidence
    # -------------------------------------------------

    "posting_activity": {

        "posts_with_valid_dates": len(
            parsed_posts
        ),

        "posts_per_week": round(
            posts_per_week,
            2
        )
    },


    "posting_consistency": {

        "average_gap_days": round(
            average_gap_days,
            2
        ),

        "largest_gap_days": (
            largest_gap_days
        ),

        "posting_gaps_days": (
            gaps
        )
    },


    # -------------------------------------------------
    # Multimodal semantic research evidence
    # -------------------------------------------------

    "content_analysis": (
        llm_analysis
    )
}


# =========================================================
# 21. Save final analysis
# =========================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        final_analysis,
        file,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# 22. Display Research Agent results
# =========================================================

print(
    "\n"
)

print(
    "=" * 60
)

print(
    "INSTAGRAM RESEARCH RESULTS"
)

print(
    "=" * 60
)


# =========================================================
# Account
# =========================================================

print(
    "\nACCOUNT"
)

print(
    f"@{profile.get('username')}"
)

print(
    f"Posts collected: "
    f"{len(posts)}"
)

print(
    "Posts successfully analyzed: "
    f"{len(successful_analyses)}"
)


# =========================================================
# Posting Activity
# =========================================================

print(
    "\nPOSTING ACTIVITY"
)

print(
    f"Posts per week: "
    f"{round(posts_per_week, 2)}"
)


# =========================================================
# Posting Consistency
# =========================================================

print(
    "\nPOSTING CONSISTENCY"
)

print(
    f"Average gap: "
    f"{round(average_gap_days, 2)} days"
)

print(
    f"Largest gap: "
    f"{largest_gap_days} days"
)


# =========================================================
# Account Semantic Summary
# =========================================================

print(
    "\nPROMOTIONAL ACTIVITY"
)

print(
    "Promotional posts:",
    account_summary.get(
        "promotional_posts_count"
    )
)

print(
    account_summary.get(
        "promotional_activity_summary",
        ""
    )
)


print(
    "\nCTA USAGE"
)

print(
    "Posts with CTA:",
    account_summary.get(
        "cta_posts_count"
    )
)

print(
    account_summary.get(
        "cta_usage_summary",
        ""
    )
)


print(
    "\nCONTENT THEMES"
)

themes = account_summary.get(
    "identified_content_themes",
    []
)

for theme in themes:

    print(
        f"- {theme}"
    )


print(
    "\nCONTENT VARIETY"
)

print(
    account_summary.get(
        "content_variety_summary",
        ""
    )
)


print(
    "\nOVERALL CONTENT"
)

print(
    account_summary.get(
        "overall_content_summary",
        ""
    )
)


# =========================================================
# 23. Per-post results
# =========================================================

print(
    "\nPER-POST ANALYSIS"
)

for analysis in post_analyses:

    post_id = analysis.get(
        "post_id"
    )

    print(
        f"\nPost {post_id}"
    )

    if analysis.get(
        "analysis_error"
    ):

        print(
            "Analysis failed:"
        )

        print(
            analysis.get(
                "analysis_error"
            )
        )

        continue

    print(
        "Promotional:",
        analysis.get(
            "is_promotional"
        )
    )

    print(
        "CTA:",
        analysis.get(
            "has_cta"
        )
    )

    print(
        "Theme:",
        analysis.get(
            "content_theme"
        )
    )

    print(
        "Purpose:",
        analysis.get(
            "content_purpose"
        )
    )

    print(
        "Images found:",
        analysis.get(
            "images_found"
        )
    )

    print(
        "Video frames analyzed:",
        analysis.get(
            "video_frames_analyzed"
        )
    )

    print(
        "Reason:",
        analysis.get(
            "reason"
        )
    )


# =========================================================
# 24. Finished
# =========================================================

print(
    "\n"
    + "=" * 60
)

print(
    f"Full analysis saved to: "
    f"{OUTPUT_FILE}"
)

print(
    "=" * 60
)