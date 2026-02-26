"""
__init__.py — Flask Application Factory for MPPW LLM Tokenizer

Sets up the Flask app with API endpoints for processing manufacturing
CSV log files. The frontend can upload CSVs and receive structured JSON
summaries of sensor data statistics and user notes.

Endpoints:
    GET  /health        — Container health check
    POST /api/upload    — Upload CSV files and receive summary
    GET  /api/summary   — Retrieve the most recent processed summary


"""

import os
import tempfile
from flask import Flask, request, jsonify
from .csv_log_processor import CSVLogProcessor


def create_app():
    """
    Application factory: builds and configures the Flask instance.

    Uses the factory pattern so the app can be created with different
    configs for testing vs. production without import side effects.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # Store the most recent processing result in memory.
    # In production, this would be persisted to a database (e.g., MongoDB).
    app.config["latest_summary"] = None

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    @app.route("/health")
    def health():
        """Simple health check to verify the container is running."""
        return jsonify({"status": "ok"})

    # ------------------------------------------------------------------
    # CSV Upload and Processing
    # ------------------------------------------------------------------

    @app.route("/api/upload", methods=["POST"])
    def upload_csv_files():
        """
        Accept one or more CSV files, process them, and return the summary.

        Expects a multipart/form-data POST request with files attached
        under the key "files". Each file is temporarily saved to disk,
        processed by the CSVLogProcessor, then cleaned up.

        Request:
            POST /api/upload
            Content-Type: multipart/form-data
            Body: files=<csv_file_1>&files=<csv_file_2>

        Response (200):
            {
                "header_statistics": [...],
                "user_notes": [...],
                "files_processed": [...],
                "total_files": int,
                "total_data_points": int
            }

        Error (400):
            { "error": "No files uploaded" }
        """
        # Validate that files were included in the request
        if "files" not in request.files:
            return jsonify({"error": "No files uploaded. Use key 'files' in form data."}), 400

        uploaded_files = request.files.getlist("files")

        # Filter out empty file inputs (browser quirk)
        uploaded_files = [f for f in uploaded_files if f.filename]

        if not uploaded_files:
            return jsonify({"error": "No valid CSV files found in request."}), 400

        # Save uploaded files to a temp directory for processing
        temp_dir = tempfile.mkdtemp()
        saved_paths = []

        try:
            for file in uploaded_files:
                # Secure the filename and save to temp directory
                file_path = os.path.join(temp_dir, file.filename)
                file.save(file_path)
                saved_paths.append(file_path)

            # Run the processor on all uploaded files
            processor = CSVLogProcessor()
            processor.load_files(saved_paths)
            summary = processor.get_summary()

            # Cache the result for the /api/summary endpoint
            app.config["latest_summary"] = summary

            return jsonify(summary), 200

        finally:
            # Clean up temp files regardless of success or failure
            for path in saved_paths:
                if os.path.exists(path):
                    os.remove(path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

    # ------------------------------------------------------------------
    # Retrieve Latest Summary
    # ------------------------------------------------------------------

    @app.route("/api/summary", methods=["GET"])
    def get_summary():
        """
        Return the most recently processed CSV summary.

        This allows the frontend to fetch results without re-uploading
        files. Useful for page refreshes or navigating back to results.

        Response (200):
            The full summary JSON (same format as /api/upload response)

        Response (404):
            { "error": "No summary available" }
        """
        summary = app.config.get("latest_summary")

        if summary is None:
            return jsonify({"error": "No summary available. Upload CSV files first."}), 404

        return jsonify(summary), 200

    return app