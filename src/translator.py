import json
import logging
from typing import Tuple

import requests
from requests.exceptions import RequestException, Timeout

from ollama import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_TIMEOUT = 30  # seconds
MAX_RETRIES = 2
OLLAMA_HOST = "http://host.docker.internal:11434"


# Prompts based on design document
LANGUAGE_DETECTION_PROMPT = """You are a language detection system.
Identify the language of the input text.
Respond with ONLY the English name of the language.
Do NOT include quotes, punctuation, or any other text.
If the language is undetectable, reply: Unknown
INPUT:"""

TRANSLATION_PROMPT = """You are a strict translation engine.
Translate the input text into English.
Rules:
- Reply with ONLY the translated English text.
- Do NOT add quotes, commentary, or any additional information.
- If the text is already English, return it unchanged.
- Preserve original meaning, tone, and emojis.
INPUT:"""


def query_llm(prompt: str, content: str) -> str:
    """Query the LLM with a prompt and content, with retries.

    Raises Exception if all retries fail.
    """
    for attempt in range(MAX_RETRIES):
        try:
            full_prompt = f"{prompt}\n{content}"

            client = Client(host=OLLAMA_HOST)

            response = client.generate(
                model=OLLAMA_MODEL,
                prompt=full_prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 500,
                },
            )

            # Extract and clean the response
            if "response" in response:
                result = response["response"].strip()
                if result:
                    logger.info(
                        f"LLM response (attempt {attempt + 1}): {result[:100]}..."
                    )
                    return result
                else:
                    logger.warning(
                        f"Empty LLM response on attempt {attempt + 1}")
            else:
                logger.warning(
                    f"Malformed LLM response on attempt {attempt + 1}: {response}")

        except Timeout:
            logger.error(f"LLM timeout on attempt {attempt + 1}")
            if attempt == MAX_RETRIES - 1:
                raise Exception(f"LLM timeout after {MAX_RETRIES} attempts")

        except Exception as e: 
            logger.error(f"LLM query error on attempt {attempt + 1}: {e}")
            if attempt == MAX_RETRIES - 1:
                raise Exception(
                    f"LLM query failed after {MAX_RETRIES} attempts: {str(e)}")

    raise Exception(f"All {MAX_RETRIES} attempts failed")


def query_llm_robust(prompt: str, content: str) -> str:
    """Call query_llm and return sensible fallbacks on error."""
    try:
        return query_llm(prompt, content)
    except Exception as e:
        logger.error(f"LLM query failed completely: {str(e)}")
        # Return appropriate fallback based on prompt type
        if "language detection" in prompt.lower():
            return "Unknown"
        elif "translation" in prompt.lower():
            return content  # Return original content as fallback
        else:
            return ""


def detect_language(content: str) -> str:
    """Detect the language of the given content using the LLM.

    Returns the language name (e.g. "English") or "Unknown".
    """
    if not content or not content.strip():
        return "Unknown"

    try:
        language = query_llm_robust(LANGUAGE_DETECTION_PROMPT, content.strip())

        if not isinstance(language, str) or not language.strip():
            logger.warning(f"Empty or invalid language response: {language!r}")
            return "Unknown"

        language_cleaned = language.strip().strip('"\'').lower()

        # Reject empty, gibberish, or multi-word responses
        if (not language_cleaned
                or any(k in language_cleaned for k in ["unknown", "gibberish", "nonsense"])
                or len(language_cleaned.split()) > 2
                # reject non-alphabetic responses
                or not any(c.isalpha() for c in language_cleaned)
                ):
            logger.warning(
                f"Unexpected language response treated as Unknown: {language_cleaned!r}")
            return "Unknown"

        return " ".join(word.capitalize() for word in language_cleaned.split())

    except Exception as e:
        logger.error(f"Language detection failed: {str(e)}")
        return "Unknown"


def translate_to_english(content: str) -> str:
    """Translate content to English using the LLM."""
    if not content or not content.strip():
        return content

    try:
        translation = query_llm_robust(TRANSLATION_PROMPT, content.strip())
        translation = translation.strip().strip('"\'')

        if translation:
            return translation
        else:
            logger.warning("Empty translation received, returning original")
            return content

    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        return content


def translate_content(content: str) -> Tuple[bool, str]:
    """Detect language and translate content to English when necessary.

    Returns:
        A tuple of (is_english: bool, translated_content: str)
    """
    if not content:
        return True, content

    try:
        language = detect_language(content)

        if language.lower() == "english":
            return True, content

        if language.lower() == "unknown":
            logger.info(
                f"Unknown language detected, treating as English: {content[:50]}...")
            return True, content

        translated_content = translate_to_english(content)

        if not translated_content or translated_content.strip().lower() == content.strip().lower():
            return False, content

        logger.info(f"Translated from {language} to English")
        return False, translated_content

    except Exception as e:
        logger.error(f"Translation process failed: {e}")
        return True, content


def health_check() -> bool:
    """
    Check if the Ollama service is available and the model is loaded.

    Returns:
        True if the service is healthy, False otherwise
    """
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code != 200:
            return False

        models = response.json().get("models", [])
        model_names = [model.get("name", "") for model in models]

        return any(OLLAMA_MODEL in name for name in model_names)

    except (RequestException, Timeout, json.JSONDecodeError):
        return False
