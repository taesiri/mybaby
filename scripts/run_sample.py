"""Run a standalone Gemini image generation on the sample image."""

from __future__ import annotations

import os
import mimetypes
import sys
from pathlib import Path

from dotenv import load_dotenv

from mybaby.gemini_client import ImageInput, generate_baby_image


def main() -> None:
    load_dotenv(override=True)

    # Ensure we only use the .env value, not any shell-provided key.
    os.environ.pop("GOOGLE_API_KEY", None)
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        # Ensure the SDK uses the same key even if GOOGLE_API_KEY is set in the shell.
        os.environ["GOOGLE_API_KEY"] = gemini_key

    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets/imgs/sample.jpeg")
    sample_path = image_path
    if not sample_path.exists():
        raise FileNotFoundError(f"Missing sample image at {sample_path}")

    image_bytes = sample_path.read_bytes()
    mime_type, _ = mimetypes.guess_type(sample_path.name)
    if not mime_type:
        mime_type = "image/jpeg"

    api_key = gemini_key
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in .env")

    output_bytes, mime_type = generate_baby_image(
        api_key=api_key,
        chat_model_name="gemini-3-pro-preview",
        image_model_name="gemini-3-pro-image-preview",
        images=[ImageInput(data=image_bytes, mime_type=mime_type)],
        params={
            "hair_color": "dark brown",
            "skin_tone": "warm medium",
            "eye_color": "hazel",
            "extra_notes": "gentle smile, soft natural lighting",
        },
    )

    suffix = ".png" if mime_type == "image/png" else ".jpg"
    output_path = Path("outputs") / f"sample_output{suffix}"
    output_path.write_bytes(output_bytes)
    print(f"Saved output to {output_path}")


if __name__ == "__main__":
    main()
