from src.translator import translate_content, query_llm_robust, detect_language, translate_to_english
from unittest.mock import patch, MagicMock

@patch('src.translator.query_llm_robust')
def test_llm_normal_response(mock_query):
    # Test when LLM provides expected result
    # Mock language detection to return Spanish
    mock_query.side_effect = ["Spanish", "This is an English message"]

    is_english, translated_content = translate_content("Este es un mensaje en español")
    assert is_english == False
    assert translated_content == "This is an English message"

@patch('src.translator.query_llm_robust')
def test_llm_english_content(mock_query):
    # Test when content is already English
    mock_query.return_value = "English"

    is_english, translated_content = translate_content("This is an English message")
    assert is_english == True
    assert translated_content == "This is an English message"

@patch('src.translator.query_llm_robust')
def test_llm_gibberish_response(mock_query):
    # Test when LLM provides gibberish/unexpected response
    # Mock language detection to return "Unknown"
    mock_query.return_value = "gibberish nonsense"

    is_english, translated_content = translate_content("hola mundo")
    # Should fallback to treating as English
    assert is_english == True
    assert translated_content == "hola mundo"

@patch('src.translator.query_llm_robust')
def test_llm_unknown_language(mock_query):
    # Test when language detection returns "Unknown"
    mock_query.return_value = "Unknown"

    is_english, translated_content = translate_content("some text")
    # Should treat as English
    assert is_english == True
    assert translated_content == "some text"

@patch('src.translator.query_llm_robust')
def test_llm_exception_handling(mock_query):
    # Test when LLM query raises an exception
    mock_query.side_effect = Exception("LLM service unavailable")

    is_english, translated_content = translate_content("text in another language")
    # Should fallback to treating as English
    assert is_english == True
    assert translated_content == "text in another language"

def test_empty_language():
    # Test behavior with empty string
    assert translate_content("") == (True, "")

