"""
Phase 2a: Theme classification via Claude API.

Takes a raw extract JSON and classifies the game's themes against the SEO taxonomy.
"""

import json
import logging
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5-20250514"

# Fallback model IDs to try if the primary is not available
_MODEL_FALLBACKS = [
    "claude-sonnet-4-5-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
]

SYSTEM_PROMPT = """You are an SEO taxonomy classifier for casino slot games.
Given the extracted text from a game's PowerPoint presentation, identify which theme tags apply.

Available theme tags (assign ALL that apply — games typically have 2–6 themes):
{themes_list}

Rules:
- Tags must come from the approved list only. Do not invent new tags.
- Input text is in Spanish. Use the spanish_aliases lookup to map Spanish terms before classifying.
- If a celebrity/real person is mentioned: add "Celebrities" tag + the person's full name as a separate tag + any relevant sport/genre tag.
- If a film/TV genre is referenced (heist, western, horror etc.): add "Movies & TV" tag AND the genre tag.
- Respond ONLY with valid JSON: {{"themes": ["Tag1", "Tag2"], "confidence": 0.85, "reasoning": "one sentence"}}
- Confidence should reflect how clearly the text supports the classification (0.5 = guessing, 0.9+ = explicit mention)."""


def _build_themes_list(taxonomy: dict) -> str:
    """Flatten the themes taxonomy into a readable list for the prompt."""
    lines = []
    for category, tags in taxonomy["themes"].items():
        lines.append(f"  {category}: {', '.join(tags)}")
    return "\n".join(lines)


def _build_spanish_aliases_section(taxonomy: dict) -> str:
    """Format the Spanish theme aliases for the prompt."""
    aliases = taxonomy.get("spanish_aliases", {}).get("themes", {})
    if not aliases:
        return "No Spanish aliases available."
    lines = []
    for spanish, english_tags in aliases.items():
        lines.append(f"  {spanish} → {', '.join(english_tags)}")
    return "\n".join(lines)


def _extract_game_text(extract: dict) -> str:
    """Pull all text from a raw extract JSON into a single string for classification."""
    parts = []

    # Prioritise category and sales slides
    category_texts = []
    sales_texts = []
    other_texts = []

    for slide in extract.get("slides", []):
        slide_text = "\n".join(slide.get("texts", []))
        if not slide_text.strip():
            continue
        if slide["is_category_slide"]:
            category_texts.append(f"[Category Slide {slide['slide_num']}]\n{slide_text}")
        elif slide["is_sales_slide"]:
            sales_texts.append(f"[Sales Slide {slide['slide_num']}]\n{slide_text}")
        else:
            other_texts.append(f"[Slide {slide['slide_num']}]\n{slide_text}")

    # Category slides first (most structured), then sales, then rest
    parts.extend(category_texts)
    parts.extend(sales_texts)
    parts.extend(other_texts)

    return "\n\n".join(parts)


async def classify_theme(
    extract: dict,
    taxonomy: dict,
    client: anthropic.AsyncAnthropic,
) -> dict:
    """
    Classify a single game's themes using Claude API.

    Returns dict with keys: themes, confidence, reasoning, error
    """
    game_text = _extract_game_text(extract)
    base_key = extract.get("base_key", "unknown")

    if not game_text.strip():
        logger.warning(f"[{base_key}] No text to classify")
        return {
            "themes": [],
            "confidence": 0.0,
            "reasoning": "No extractable text found in PPTX",
            "error": None,
        }

    themes_list = _build_themes_list(taxonomy)
    aliases_section = _build_spanish_aliases_section(taxonomy)

    system = SYSTEM_PROMPT.format(themes_list=themes_list)
    user_msg = (
        f"Game: {extract.get('folder_game_name', base_key)}\n"
        f"Category: {extract.get('folder_category', 'unknown')}\n\n"
        f"Spanish alias reference:\n{aliases_section}\n\n"
        f"Extracted text:\n{game_text}"
    )

    try:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        text = response.content[0].text.strip()

        # Parse JSON from response — handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(text)
        return {
            "themes": result.get("themes", []),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", ""),
            "error": None,
        }

    except json.JSONDecodeError as e:
        logger.error(f"[{base_key}] Failed to parse theme response: {e}\nRaw: {text}")
        return {
            "themes": [],
            "confidence": 0.0,
            "reasoning": "",
            "error": f"JSON parse error: {e}",
        }
    except Exception as e:
        logger.error(f"[{base_key}] Theme classification failed: {e}")
        return {
            "themes": [],
            "confidence": 0.0,
            "reasoning": "",
            "error": str(e),
        }
