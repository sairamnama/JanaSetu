"""
GramSeva - Dynamic Translation Service
Integrates Google Cloud Translation API v2 for dynamic, system-generated content
(such as civic announcements, emergency broadcasts, and variable notices) with
in-memory caching and graceful error fallback.
"""

import os
import json
import html
import urllib.request
import urllib.error
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# In-memory translation cache: (text, source_lang, target_lang) -> translated_text
_TRANSLATION_CACHE: Dict[Tuple[str, str, str], str] = {}
_MAX_CACHE_SIZE = 2000

# Endpoint for Google Cloud Translation v2 API
GOOGLE_TRANSLATE_API_URL = "https://translation.googleapis.com/language/translate/v2"


def get_api_key() -> str:
    """Retrieves Google Cloud Translation API key securely from environment."""
    return (
        os.environ.get('GOOGLE_TRANSLATE_API_KEY') or
        os.environ.get('GOOGLE_API_KEY') or
        ''
    ).strip()


def is_api_configured() -> bool:
    """Returns True if a non-empty API key is present in environment secrets."""
    return bool(get_api_key())


def translate_dynamic_text(
    text: str,
    target_lang: str = 'te',
    source_lang: str = 'en'
) -> str:
    """
    Translates dynamic application text using Google Cloud Translation API.
    
    Invariants & Safety:
    - If target_lang matches source_lang or text is empty, returns original text immediately.
    - Checks in-memory cache first to eliminate duplicate API requests and costs.
    - If GOOGLE_TRANSLATE_API_KEY is not configured, logs a single warning and returns original text safely.
    - Never raises exceptions; gracefully falls back to original text on any timeout or network error.
    - API key is kept strictly on the backend and never exposed to the client.
    """
    if not text or not text.strip():
        return text

    clean_text = text.strip()
    if target_lang == source_lang:
        return text

    # Check cache
    cache_key = (clean_text, source_lang, target_lang)
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    api_key = get_api_key()
    if not api_key:
        # Graceful fallback when API key is not configured
        return text

    url = f"{GOOGLE_TRANSLATE_API_URL}?key={api_key}"
    payload = json.dumps({
        "q": clean_text,
        "target": target_lang,
        "source": source_lang,
        "format": "text"
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=3.5) as response:
            if response.status == 200:
                body = json.loads(response.read().decode('utf-8'))
                translations = body.get('data', {}).get('translations', [])
                if translations:
                    raw_result = translations[0].get('translatedText', '')
                    # Unescape HTML entities that translation API may produce
                    translated = html.unescape(raw_result)

                    # Manage cache capacity
                    if len(_TRANSLATION_CACHE) >= _MAX_CACHE_SIZE:
                        # Clear half the cache when full (simple LRU approximation)
                        keys_to_remove = list(_TRANSLATION_CACHE.keys())[: _MAX_CACHE_SIZE // 2]
                        for k in keys_to_remove:
                            _TRANSLATION_CACHE.pop(k, None)

                    _TRANSLATION_CACHE[cache_key] = translated
                    return translated
    except urllib.error.HTTPError as e:
        logger.warning("Google Cloud Translation API HTTP error %s: %s", e.code, e.reason)
    except urllib.error.URLError as e:
        logger.warning("Google Cloud Translation API network error: %s", e.reason)
    except Exception as e:
        logger.warning("Google Cloud Translation API unexpected error: %s", str(e))

    # Graceful fallback: return original text
    return text


def translate_announcement(announcement: dict, target_lang: str = 'te') -> dict:
    """
    Returns a copy of the announcement dictionary with title and content
    translated to the requested target language if target_lang is 'te'.
    """
    if target_lang != 'te' or not announcement:
        return announcement

    result = dict(announcement)
    if 'title' in result and result['title']:
        result['title'] = translate_dynamic_text(result['title'], target_lang='te', source_lang='en')
    if 'content' in result and result['content']:
        result['content'] = translate_dynamic_text(result['content'], target_lang='te', source_lang='en')

    return result

