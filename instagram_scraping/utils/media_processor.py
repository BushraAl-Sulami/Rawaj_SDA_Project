import base64
import os
import tempfile

import cv2
import requests


def download_file(url: str) -> bytes:

    response = requests.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    return response.content


def image_url_to_base64(image_url: str) -> str:

    response = requests.get(
        image_url,
        timeout=60
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "image/jpeg"
    )

    encoded_image = base64.b64encode(
        response.content
    ).decode("utf-8")

    return f"data:{content_type};base64,{encoded_image}"


def frame_to_base64(frame) -> str:

    success, buffer = cv2.imencode(
        ".jpg",
        frame
    )

    if not success:
        raise ValueError("Could not encode video frame")

    encoded_frame = base64.b64encode(
        buffer.tobytes()
    ).decode("utf-8")

    return f"data:image/jpeg;base64,{encoded_frame}"


def extract_video_frames(
    video_url: str,
    number_of_frames: int = 4
) -> list[str]:

    video_bytes = download_file(
        video_url
    )

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".mp4",
        delete=False
    )

    temp_path = temp_file.name

    try:

        temp_file.write(video_bytes)
        temp_file.close()

        video = cv2.VideoCapture(
            temp_path
        )

        total_frames = int(
            video.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        if total_frames <= 0:
            video.release()
            return []

        if number_of_frames > total_frames:
            number_of_frames = total_frames

        positions = []

        for i in range(number_of_frames):

            if number_of_frames == 1:
                position = 0
            else:
                position = int(
                    i
                    * (total_frames - 1)
                    / (number_of_frames - 1)
                )

            positions.append(position)

        frames_base64 = []

        for position in positions:

            video.set(
                cv2.CAP_PROP_POS_FRAMES,
                position
            )

            success, frame = video.read()

            if success:
                frames_base64.append(
                    frame_to_base64(frame)
                )

        video.release()

        return frames_base64

    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)