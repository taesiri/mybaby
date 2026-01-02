"""Flask application entrypoint."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from io import BytesIO

from dotenv import load_dotenv
from flask import Flask, Response, render_template, request, send_file

from .gemini_client import ImageInput, generate_baby_image

MAX_IMAGES = 5
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def create_app() -> Flask:
    load_dotenv(override=True)
    os.environ.pop("GOOGLE_API_KEY", None)

    logging.basicConfig(level=logging.INFO)

    template_dir = Path(__file__).resolve().parents[2] / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.config.update(
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
        GEMINI_CHAT_MODEL="gemini-3-pro-preview",
        GEMINI_IMAGE_MODEL="gemini-3-pro-image-preview",
    )

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.post("/generate")
    def generate() -> Response:
        api_key = app.config["GEMINI_API_KEY"]
        if not api_key:
            return Response("Missing GEMINI_API_KEY in .env", status=400)

        files = request.files.getlist("images")
        app.logger.info("Generation request received with %s image(s).", len(files))
        if not 1 <= len(files) <= MAX_IMAGES:
            return Response("Provide between 1 and 5 images.", status=400)

        images: list[ImageInput] = []
        for upload in files:
            if upload.mimetype not in ALLOWED_MIME_TYPES:
                return Response(
                    f"Unsupported file type: {upload.mimetype}.", status=400
                )
            images.append(ImageInput(data=upload.read(), mime_type=upload.mimetype))
        app.logger.info(
            "Accepted images: %s",
            ", ".join(image.mime_type for image in images),
        )

        params = {
            "hair_color": request.form.get("hair_color", ""),
            "hair_amount": request.form.get("hair_amount", ""),
            "skin_tone": request.form.get("skin_tone", ""),
            "eye_color": request.form.get("eye_color", ""),
            "extra_notes": request.form.get("extra_notes", ""),
        }
        app.logger.info("Parameters received: %s", {k: v for k, v in params.items() if v})

        try:
            image_bytes, mime_type = generate_baby_image(
                api_key=api_key,
                chat_model_name=app.config["GEMINI_CHAT_MODEL"],
                image_model_name=app.config["GEMINI_IMAGE_MODEL"],
                images=images,
                params=params,
            )
            app.logger.info("Gemini returned image with mime type %s.", mime_type)
        except Exception as exc:  # noqa: BLE001 - surface Gemini errors to client
            app.logger.exception("Gemini generation failed.")
            return Response(str(exc), status=500)

        return send_file(BytesIO(image_bytes), mimetype=mime_type)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
