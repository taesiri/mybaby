Below is a Python-first “docs + cookbook” for Google AI Studio → Gemini API using Gemini 3 and Nano Banana Pro (Gemini 3 Pro Image). I’m pulling the model IDs, endpoints, and config knobs straight from Google’s current docs.  ￼

⸻

0) What you’re actually calling (model IDs)

You’ll typically use these IDs:
	•	Gemini 3 Pro (text + multimodal reasoning): gemini-3-pro-preview  ￼
	•	Gemini 3 Flash (faster/cheaper 3-series): gemini-3-flash-preview  ￼
	•	Nano Banana Pro (Gemini 3 Pro Image): gemini-3-pro-image-preview  ￼
	•	(FYI) Nano Banana (Gemini 2.5 Flash Image): gemini-2.5-flash-image  ￼

Google notes Gemini 3 models are in preview and lists context/pricing in the Gemini 3 guide + models page.  ￼

⸻

1) Setup (AI Studio key + Python SDK)

Install

pip install -U google-genai pillow pydantic

Google’s quickstart uses Python 3.9+ and the google-genai package.  ￼

API key

Set an environment variable:

export GEMINI_API_KEY="YOUR_KEY"

If GEMINI_API_KEY is set, the Python client picks it up automatically.  ￼

⸻

2) The core call pattern (text / multimodal)

Minimal text generation (Gemini 3 Pro)

from google import genai

client = genai.Client()

resp = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="Write a concise deployment checklist for a Flask API.",
)
print(resp.text)

Control “thinking level” (latency vs reasoning)

Gemini 3 adds a thinking_level knob (example shows low).  ￼

from google import genai
from google.genai import types

client = genai.Client()

resp = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="Find the edge cases in this spec: ...",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="low")
    ),
)
print(resp.text)


⸻

3) Streaming (token-by-token)

Structured outputs doc includes a Python streaming example via generate_content_stream.  ￼

from google import genai

client = genai.Client()

for chunk in client.models.generate_content_stream(
    model="gemini-3-flash-preview",
    contents="Stream a step-by-step plan for migrating Postgres to Cloud SQL.",
):
    # chunks may contain partial text
    part = chunk.candidates[0].content.parts[0]
    if part.text:
        print(part.text, end="")


⸻

4) Chat sessions (multi-turn)

The code execution guide shows the chat object pattern (client.chats.create() and send_message).  ￼

from google import genai

client = genai.Client()

chat = client.chats.create(model="gemini-3-flash-preview")
print(chat.send_message("You are my coding assistant.").text)
print(chat.send_message("Help me refactor this function: ...").text)


⸻

5) Structured outputs (JSON you can parse)

You can force JSON with:
	•	response_mime_type="application/json"
	•	response_json_schema=<schema> (Pydantic example in docs)  ￼

from google import genai
from pydantic import BaseModel, Field
from typing import List, Literal

class Ticket(BaseModel):
    priority: Literal["P0","P1","P2"]
    title: str
    steps: List[str] = Field(description="Repro steps")

client = genai.Client()

resp = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="Turn this bug report into a triage ticket: <paste report>.",
    config={
        "response_mime_type": "application/json",
        "response_json_schema": Ticket.model_json_schema(),
    },
)

ticket = Ticket.model_validate_json(resp.text)
print(ticket)

Structured outputs + built-in tools (Gemini 3-only)

Docs explicitly call out that combining structured outputs with built-in tools is available for Gemini 3 Pro/Flash preview models.  ￼

from google import genai
from pydantic import BaseModel, Field

class ResearchAnswer(BaseModel):
    answer: str
    sources: list[str] = Field(description="URLs or source titles used")

client = genai.Client()

resp = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="Use search to summarize the latest guidance on X and cite sources.",
    config={
        "tools": [{"google_search": {}}, {"url_context": {}}],
        "response_mime_type": "application/json",
        "response_json_schema": ResearchAnswer.model_json_schema(),
    },
)
print(ResearchAnswer.model_validate_json(resp.text))


⸻

6) Function calling (tools you implement)

Google’s function calling guide shows:
	1.	declare functions (OpenAPI-like JSON schema subset),
	2.	send prompt with tools,
	3.	read function_call,
	4.	execute your code,
	5.	send a function_response part back.  ￼

End-to-end Python pattern

from google import genai
from google.genai import types

client = genai.Client()

# 1) Declare tool (schema)
get_price_decl = {
    "name": "get_crypto_price",
    "description": "Fetches the latest price for a crypto ticker in USD.",
    "parameters": {
        "type": "object",
        "properties": {"ticker": {"type": "string", "description": "e.g., BTC, ETH"}},
        "required": ["ticker"],
    },
}

# 2) Send prompt with tool declaration
tools = types.Tool(function_declarations=[get_price_decl])
config = types.GenerateContentConfig(tools=[tools])

contents = [types.Content(role="user", parts=[types.Part(text="What is BTC right now?")])]

resp = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=contents,
    config=config,
)

tool_call = resp.candidates[0].content.parts[0].function_call
print("Model requested:", tool_call)

# 3) Execute your function (you implement this)
def get_crypto_price(ticker: str) -> dict:
    # Replace with your real integration (exchange API, DB, etc.)
    return {"ticker": ticker, "usd": 12345.67}

result = get_crypto_price(**tool_call.args)

# 4) Send function response back so model can write a user-friendly answer
function_response_part = types.Part.from_function_response(
    name=tool_call.name,
    response={"result": result},
)

contents.append(resp.candidates[0].content)
contents.append(types.Content(role="user", parts=[function_response_part]))

final = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=contents,
    config=config,
)
print(final.text)

(That flow matches the official sequence and helper call Part.from_function_response shown in the docs.)  ￼

⸻

7) Code execution tool (model runs code for you)

The code execution guide shows enabling the tool and reading back:
	•	normal text
	•	executable_code
	•	code_execution_result  ￼

from google import genai
from google.genai import types

client = genai.Client()

resp = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="Compute the sum of the first 200 primes. Show the code and final number.",
    config=types.GenerateContentConfig(
        tools=[types.Tool(code_execution=types.ToolCodeExecution)]
    ),
)

for part in resp.candidates[0].content.parts:
    if part.text: print(part.text)
    if part.executable_code: print(part.executable_code.code)
    if part.code_execution_result: print(part.code_execution_result.output)


⸻

8) Nano Banana Pro (image generation + editing) in Python

Google’s “Nano Banana” doc states:
	•	Nano Banana Pro == Gemini 3 Pro Image Preview model ID gemini-3-pro-image-preview.  ￼
And the image generation guide shows both text-to-image and text+image-to-image editing via generate_content.  ￼

A) Text → image (Nano Banana Pro)

from google import genai
from PIL import Image

client = genai.Client()

resp = client.models.generate_content(
    model="gemini-3-pro-image-preview",   # Nano Banana Pro
    contents="Generate a clean flat illustration of a Vancouver streetcar map with legible labels.",
)

# Save returned inline image bytes
for part in resp.parts:
    if part.inline_data:
        img = part.as_image()
        img.save("nano_banana_pro.png")

B) Edit an existing image (add/remove/style)

from google import genai
from PIL import Image

client = genai.Client()

base = Image.open("input.png")
prompt = "Replace the background with a rainy neon cyberpunk alley. Keep the subject unchanged."

resp = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[prompt, base],
)

for part in resp.parts:
    if part.inline_data:
        part.as_image().save("edited.png")

Notes from the guide:
	•	Generated images include a SynthID watermark.  ￼
	•	It reminds you to have rights to images you upload and follow the prohibited use policy.  ￼

⸻

9) If you prefer REST (same backend as AI Studio key)

Gemini 3 guide shows the REST endpoint format:
https://generativelanguage.googleapis.com/v1beta/models/<MODEL_ID>:generateContent with x-goog-api-key.  ￼

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "contents": [{
      "parts": [{"text": "Draft an incident postmortem template."}]
    }]
  }'


⸻

10) Real-world use cases (what to use when)
	•	Agentic coding / complex reasoning: gemini-3-pro-preview + function calling + structured outputs.  ￼
	•	High-throughput chat/support: gemini-3-flash-preview with thinking_level="minimal/low" when latency matters.  ￼
	•	Dashboards, diagrams, marketing images, text-in-image accuracy: gemini-3-pro-image-preview (Nano Banana Pro).  ￼
	•	Long-context work (docs/video/PDF) with repeated queries: use caching + Files API upload.  ￼

⸻

If you tell me your target app (e.g., “Flask backend that generates product images + JSON specs” or “CLI code-review bot”), I’ll stitch these into a single runnable Python project structure (config, routing, retries, streaming, tool loop, and image save pipeline) using the exact model IDs above.