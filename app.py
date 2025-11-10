import os
import logging
from flask import Flask, request, jsonify
from src.translator import translate_content, health_check

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/')
def translator():
    """
    Root endpoint that translates content from query parameter.
    Kept for backward compatibility.
    """
    content = request.args.get("content", default="", type=str)
    is_english, translated_content = translate_content(content)
    return jsonify({
        "is_english": is_english,
        "translated_content": translated_content,
    })


@app.route('/translate', methods=['GET'])
def translate_endpoint():
    """
    Translate content from one language to English.

    Query Parameters:
    - content: The text to translate

    Returns:
    JSON with is_english (boolean) and translated_content (string)
    """
    try:
        # Get content from query parameter
        content = request.args.get('content', '')

        if not content:
            return jsonify({
                'error': 'Missing content parameter'
            }), 400

        # Translate the content
        is_english, translated_content = translate_content(content)

        return jsonify({
            'is_english': is_english,
            'translated_content': translated_content
        })

    except Exception as e:
        logger.error(f"Translation endpoint error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_endpoint():
    """
    Check the health of the translation service.

    Returns:
    JSON with health status and Ollama availability
    """
    ollama_healthy = health_check()

    status = {
        'status': 'healthy' if ollama_healthy else 'unhealthy',
        'ollama_available': ollama_healthy
    }

    if ollama_healthy:
        return jsonify(status), 200
    else:
        return jsonify(status), 503


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
