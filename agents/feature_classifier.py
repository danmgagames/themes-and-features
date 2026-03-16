"""
Phase 2b: Feature/mechanic classification via Claude API.

Takes a raw extract JSON and classifies the game's features against the SEO taxonomy.
"""

import json
import logging
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5-20250514"

SYSTEM_PROMPT = """You are a casino game mechanics classifier.
Given the extracted text from a game's PowerPoint presentation, identify which feature/mechanic tags apply.

Available feature tags (assign ALL that apply):
{features_list}

Spanish-to-English alias map:
{spanish_aliases_features}

Rules:
- Tags must come from the approved list only. If you encounter a mechanic not on the list, add it to the "unknown_features" array for human review — do not drop it.
- Input text is in Spanish.
- "Compra Free Spins" or "Opción de compra" always maps to "Buy Feature" / "Buy Free Spins".
- Megaways always maps to "Megaways".
- Respond ONLY with valid JSON: {{"features": ["Tag1", "Tag2"], "unknown_features": ["any not on list"], "confidence": 0.85, "reasoning": "one sentence"}}"""


def _build_features_list(taxonomy: dict) -> str:
    """Flatten the features taxonomy into a readable list for the prompt."""
    lines = []
    for category, tags in taxonomy["features"].items():
        if category.startswith("_"):
            continue
        lines.append(f"  {category}: {', '.join(tags)}")
    return "\n".join(lines)


def _build_spanish_aliases_section(taxonomy: dict) -> str:
    """Format the Spanish feature aliases for the prompt."""
    aliases = taxonomy.get("spanish_aliases", {}).get("features", {})
    if not aliases:
        return "No Spanish aliases available."
    lines = []
    for spanish, english in aliases.items():
        lines.append(f"  {spanish} → {english}")
    return "\n".join(lines)


def _extract_game_text(extract: dict) -> str:
    """Pull all text from a raw extract JSON into a single string for classification."""
    parts = []

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

    parts.extend(category_texts)
    parts.extend(sales_texts)
    parts.extend(other_texts)

    return "\n\n".join(parts)


async def classify_features(
    extract: dict,
    taxonomy: dict,
    client: anthropic.AsyncAnthropic,
) -> dict:
    """
    Classify a single game's features using Claude API.

    Returns dict with keys: features, unknown_features, confidence, reasoning, error
    """
    game_text = _extract_game_text(extract)
    base_key = extract.get("base_key", "unknown")

    if not game_text.strip():
        logger.warning(f"[{base_key}] No text to classify")
        return {
            "features": [],
            "unknown_features": [],
            "confidence": 0.0,
            "reasoning": "No extractable text found in PPTX",
            "error": None,
        }

    features_list = _build_features_list(taxonomy)
    aliases_section = _build_spanish_aliases_section(taxonomy)

    system = SYSTEM_PROMPT.format(
        features_list=features_list,
        spanish_aliases_features=aliases_section,
    )
    user_msg = (
        f"Game: {extract.get('folder_game_name', base_key)}\n"
        f"Category: {extract.get('folder_category', 'unknown')}\n\n"
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
            "features": result.get("features", []),
            "unknown_features": result.get("unknown_features", []),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", ""),
            "error": None,
        }

    except json.JSONDecodeError as e:
        logger.error(f"[{base_key}] Failed to parse feature response: {e}\nRaw: {text}")
        return {
            "features": [],
            "unknown_features": [],
            "confidence": 0.0,
            "reasoning": "",
            "error": f"JSON parse error: {e}",
        }
    except Exception as e:
        logger.error(f"[{base_key}] Feature classification failed: {e}")
        return {
            "features": [],
            "unknown_features": [],
            "confidence": 0.0,
            "reasoning": "",
            "error": str(e),
        }
