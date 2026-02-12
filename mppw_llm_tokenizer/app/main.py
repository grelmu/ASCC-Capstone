"""
main.py — Entry point for the MPPW LLM Tokenizer Flask application.

Starts the Flask development server on port 5000. In production, this
would be replaced by a WSGI server like Gunicorn.


"""

from . import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)