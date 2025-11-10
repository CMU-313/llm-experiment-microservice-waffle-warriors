import ollama
import json
import logging
from typing import Tuple, Optional
import requests
from requests.exceptions import RequestException, Timeout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_TIMEOUT = 30  # seconds
MAX_RETRIES = 2
OLLAMA_HOST = "http://host.docker.internal:11434"  # For Docker container to host connection

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
    """
    Query the LLM with a prompt and content, with robust error handling.

    Args:
        prompt: The system prompt to use
        content: The content to process

    Returns:
        The LLM response as a string

    Raises:
        Exception: If all retries fail
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Construct the full prompt
            full_prompt = f"{prompt}\n{content}"

            # Configure Ollama client to connect to host
            from ollama import Client
            client = Client(host=OLLAMA_HOST)

            # Query Ollama
            response = client.generate(
                model=OLLAMA_MODEL,
                prompt=full_prompt,
                options={
                    'temperature': 0.1,  # Low temperature for consistent output
                    'top_p': 0.9,
                    'max_tokens': 500
                }
            )

            # Extract and clean the response
            if 'response' in response:
                result = response['response'].strip()
                if result:
                    logger.info(f"LLM response (attempt {attempt + 1}): {result[:100]}...")
                    return result
                else:
                    logger.warning(f"Empty LLM response on attempt {attempt + 1}")
            else:
                logger.warning(f"Malformed LLM response on attempt {attempt + 1}: {response}")

        except Timeout:
            logger.error(f"LLM timeout on attempt {attempt + 1}")
            if attempt == MAX_RETRIES - 1:
                raise Exception(f"LLM timeout after {MAX_RETRIES} attempts")

        except Exception as e:
            logger.error(f"LLM query error on attempt {attempt + 1}: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise Exception(f"LLM query failed after {MAX_RETRIES} attempts: {str(e)}")

    raise Exception(f"All {MAX_RETRIES} attempts failed")


def query_llm_robust(prompt: str, content: str) -> str:
    """
    Robust version of query_llm that returns fallback values on failure.

    Args:
        prompt: The system prompt to use
        content: The content to process

    Returns:
        The LLM response as a string, or a fallback value
    """
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
    """
    Detect the language of the given content.

    Args:
        content: The text to analyze

    Returns:
        The detected language as a string (e.g., "English", "Chinese", etc.)
    """
    if not content or not content.strip():
        return "Unknown"

    try:
        language = query_llm_robust(LANGUAGE_DETECTION_PROMPT, content.strip())

        # Clean up the response
        language = language.strip().strip('"\'')

        # Validate common language names
        valid_languages = {
            'english', 'chinese', 'spanish', 'french', 'german', 'italian',
            'portuguese', 'russian', 'japanese', 'korean', 'arabic', 'hindi',
            'thai', 'turkish', 'vietnamese', 'catalan', 'dutch', 'polish',
            'unknown'
        }

        if language.lower() in valid_languages:
            return language.capitalize()
        else:
            logger.warning(f"Unexpected language response: {language}")
            return "Unknown"

    except Exception as e:
        logger.error(f"Language detection failed: {str(e)}")
        return "Unknown"


def translate_to_english(content: str) -> str:
    """
    Translate content to English using the LLM.

    Args:
        content: The text to translate

    Returns:
        The English translation as a string
    """
    if not content or not content.strip():
        return content

    try:
        translation = query_llm_robust(TRANSLATION_PROMPT, content.strip())

        # Clean up the response
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
    """
    Main translation function that detects language and translates if needed.

    Args:
        content: The text to analyze and potentially translate

    Returns:
        A tuple of (is_english: bool, translated_content: str)
    """
    if not content:
        return True, content

    try:
        # Detect the language
        language = detect_language(content)

        # If it's English, return as-is
        if language.lower() == "english":
            return True, content

        # If unknown language, assume it's English (conservative approach)
        if language.lower() == "unknown":
            logger.info(f"Unknown language detected, treating as English: {content[:50]}...")
            return True, content

        # Translate to English
        translated_content = translate_to_english(content)

        # Check if translation actually changed anything
        if translated_content.lower() == content.lower():
            # Content was already English or translation didn't change it
            return True, content

        logger.info(f"Translated from {language} to English")
        return False, translated_content

    except Exception as e:
        logger.error(f"Translation process failed: {str(e)}")
        # Conservative fallback: assume it's English and return original
        return True, content


def health_check() -> bool:
    """
    Check if the Ollama service is available and the model is loaded.

    Returns:
        True if the service is healthy, False otherwise
    """
    try:
        # Check if Ollama is running
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code != 200:
            return False

        # Check if our model is available
        models = response.json().get('models', [])
        model_names = [model.get('name', '') for model in models]

        return any(OLLAMA_MODEL in name for name in model_names)

    except (RequestException, Timeout, json.JSONDecodeError):
        return False
