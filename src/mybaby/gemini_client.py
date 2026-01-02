"""Gemini client wrapper for image generation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from google import genai
from google.genai import types


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    mime_type: str


def _build_prompt(params: dict[str, str]) -> str:
    prompt_lines = [
        "Create a realistic, photorealistic baby portrait based on the attached 3D ultrasound image(s).",
        "Use the parameters below to guide appearance. Do not add text or watermarks.",
    ]
    for key, value in params.items():
        if value:
            prompt_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    return "\n".join(prompt_lines)


def _extract_text(response: types.GenerateContentResponse) -> str | None:
    for candidate in response.candidates or []:
        content = candidate.content
        if not content or not content.parts:
            continue
        for part in content.parts:
            if part.text:
                return part.text
    return None


def _refine_prompt(
    *,
    client: genai.Client,
    chat_model_name: str,
    params: dict[str, str],
) -> str:
    seed_prompt = _build_prompt(params)
    response = client.models.generate_content(
        model=chat_model_name,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=(
                            "You are a creative director for photorealistic baby portraits. "
                            "Rewrite the prompt for a text-to-image model. Keep it concise, vivid, "
                            "and safe. Do not add any extra requirements beyond the provided "
                            "parameters.\n\n"
                            f"{seed_prompt}"
                        )
                    )
                ],
            )
        ],
    )
    return _extract_text(response) or seed_prompt


def generate_baby_image(
    *,
    api_key: str,
    chat_model_name: str,
    image_model_name: str,
    images: Iterable[ImageInput],
    params: dict[str, str],
) -> tuple[bytes, str]:
    """Generate a baby image using Gemini, returning (image_bytes, mime_type)."""
    os.environ["GOOGLE_API_KEY"] = api_key
    client = genai.Client(api_key=api_key)
    prompt = _refine_prompt(
        client=client,
        chat_model_name=chat_model_name,
        params=params,
    )

    parts: list[types.Part] = [types.Part.from_text(text=prompt)]
    image_list = list(images)
    if not image_list:
        raise ValueError("At least one input image is required.")
    for image in image_list:
        parts.append(types.Part.from_bytes(data=image.data, mime_type=image.mime_type))

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(image_size="1K"),
    )

    stream = client.models.generate_content_stream(
        model=image_model_name,
        contents=[types.Content(role="user", parts=parts)],
        config=config,
    )

    for chunk in stream:
        if not chunk.candidates:
            continue
        content = chunk.candidates[0].content
        if not content or not content.parts:
            continue
        part = content.parts[0]
        if part.inline_data and part.inline_data.data:
            mime_type = part.inline_data.mime_type or "image/png"
            return part.inline_data.data, mime_type

    raise RuntimeError("Gemini response did not include an image.")
