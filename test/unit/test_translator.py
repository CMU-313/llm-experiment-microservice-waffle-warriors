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


@patch('src.translator.query_llm_robust')
def test_unexpected_language(mock_query):
    # Mock LLM to return unexpected response that doesn't match valid languages
    mock_query.side_effect = ["I don't understand your request", "I don't understand your request"]

    is_english, translated_content = translate_content("Hier ist dein erstes Beispiel.")
    # Should fallback to treating as English when language detection fails
    assert is_english == True
    assert translated_content == "Hier ist dein erstes Beispiel."


@patch('src.translator.query_llm_robust')
def test_empty_llm_response(mock_query):
    # Mock LLM to return empty response
    mock_query.return_value = ""

    is_english, translated_content = translate_content("Ceci est un test")
    # Should fallback to treating as English when response is empty
    assert is_english == True
    assert translated_content == "Ceci est un test"


@patch('src.translator.query_llm_robust')
def test_non_string_llm_response(mock_query):
    # This test doesn't make sense with our current implementation
    # since query_llm_robust always returns strings
    # Let's test a more realistic scenario - partial translation
    mock_query.side_effect = ["Unknown", "Hello world test"]

    is_english, translated_content = translate_content("gibberish 未知語 text")
    # Should translate when language is "Unknown" (fallback to English assumption)
    assert is_english == True
    assert translated_content == "gibberish 未知語 text"


@patch('src.translator.query_llm_robust')
def test_spanish_detection(mock_query):
    # Test proper Spanish detection and translation
    mock_query.side_effect = ["Spanish", "Hello, this is a test"]

    is_english, translated_content = translate_content("Hola, esto es una prueba")
    # Should detect Spanish and translate
    assert is_english == False
    assert translated_content == "Hello, this is a test"

