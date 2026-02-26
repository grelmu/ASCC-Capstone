# MPPW LLM Tokenizer

A Flask-based microservice for processing manufacturing operation CSV log files. It extracts sensor data, computes cumulative statistics (min, max, mean) across multiple files, detects user notes, and returns structured JSON for frontend display.

> **Note:** This is a prototype. In production, the statistical processing will be augmented by an LLM (Llama 3) for contextual summarization of manufacturing logs.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

## Quick Start

From the **project root** (`ASCC-Capstone/`):

### 1. Build the container

```sh
docker build -t ascc/mppw-llm-tokenizer:dev -f containers/mppw-llm-tokenizer/Dockerfile mppw_llm_tokenizer
```

### 2. Run the container

```sh
docker run -p 5000:5000 ascc/mppw-llm-tokenizer:dev
```

### 3. Verify it's running

Open a browser or new terminal:

```sh
curl http://localhost:5000/health
```

Expected response:
```json
{"status": "ok"}
```

## API Endpoints

### `GET /health`

Health check to verify the container is running.

**Response:**
```json
{"status": "ok"}
```

---

### `POST /api/upload`

Upload one or more CSV log files for processing. Returns cumulative statistics across all uploaded files.

**Request:**
- Content-Type: `multipart/form-data`
- Key: `files` (one or more CSV files)

**Example (single file):**
```sh
curl -F "files=@/path/to/your/logfile.csv" http://localhost:5000/api/upload
```

**Example (multiple files):**
```sh
curl -F "files=@/path/to/log1.csv" -F "files=@/path/to/log2.csv" http://localhost:5000/api/upload
```

**Response (200):**
```json
{
  "header_statistics": [
    {
      "header": "Nozzle Temperature",
      "min": 213.0,
      "max": 230.2,
      "mean": 220.33,
      "count": 10169
    }
  ],
  "user_notes": [],
  "files_processed": [
    {
      "file_name": "logfile.csv",
      "row_count": 3757,
      "start_time": "9/24/2025 11:50:20 AM",
      "end_time": "9/24/2025 3:01:02 PM",
      "notes_column": "7.5in x 8in Hex 2xBrim Rear Left PolyPro"
    }
  ],
  "total_files": 1,
  "total_data_points": 48841
}
```

---

### `GET /api/summary`

Retrieve the most recently processed summary without re-uploading files.

**Response (200):** Same format as `/api/upload`.

**Response (404):** No files have been processed yet.
```json
{"error": "No summary available. Upload CSV files first."}
```

## Expected CSV Format

The processor is designed for ASCC 3D printing operation logs with this structure:

| Column | Type | Description |
|---|---|---|
| DateTime | Metadata | Timestamp of the reading |
| Line of G-Code | Metadata | Current G-Code line number |
| Cycle Time | Metadata | Elapsed cycle time |
| Screw Torque | Numeric | Extruder screw torque |
| Upper Temperature | Numeric | Upper zone temperature |
| Middle Temperature | Numeric | Middle zone temperature |
| Lower Temperature | Numeric | Lower zone temperature |
| Nozzle Temperature | Numeric | Nozzle temperature |
| Melt Zone Temperature | Numeric | Melt zone temperature |
| Feed Housing Temperature | Numeric | Feed housing temperature |
| Chamber Temperature | Numeric | Chamber temperature |
| Bed Temperature | Numeric | Bed temperature |
| Screw RPS | Numeric | Screw revolutions per second |
| Feed Rate Override | Numeric | Feed rate override percentage |
| Spindle Override | Numeric | Spindle override percentage |
| Total Power Used During Print | Numeric | Cumulative power consumption |
| *[Print Job Name]* | Notes | Last column — named after the print job, reserved for user notes |

The processor will handle CSVs with different or additional columns. Any non-numeric values found in numeric columns are captured as inline annotations.

## Project Structure

```
mppw_llm_tokenizer/
├── app/
│   ├── __init__.py            # Flask app factory with API endpoints
│   ├── main.py                # Entry point — starts the Flask server
│   └── csv_log_processor.py   # Core processing logic for CSV files
└── requirements.txt           # Python dependencies

containers/
└── mppw-llm-tokenizer/
    └── Dockerfile             # Container build instructions
```

## Editing and Testing

### Making code changes

1. Edit files in `mppw_llm_tokenizer/app/`
2. Rebuild the container:
   ```sh
   docker build -t ascc/mppw-llm-tokenizer:dev -f containers/mppw-llm-tokenizer/Dockerfile mppw_llm_tokenizer
   ```
3. Run and test:
   ```sh
   docker run -p 5000:5000 ascc/mppw-llm-tokenizer:dev
   ```

### Running the processor standalone (without Docker)

You can also run the CSV processor directly with Python 3.8+:

```sh
cd mppw_llm_tokenizer/app
python csv_log_processor.py /path/to/log1.csv /path/to/log2.csv
```

This prints the JSON summary to the terminal.

### Stopping the container

Press `Ctrl+C` in the terminal where the container is running.

> The "WARNING: This is a development server" message from Flask is normal and expected for local development.

## Future Work

- **LLM Integration:** Replace or augment statistical processing with Llama 3 for contextual log summarization
- **User Notes:** Finalize the format and location of user-authored notes in CSV files
- **MongoDB Storage:** Persist processed summaries to the MPPW database
- **Frontend Integration:** Connect the React frontend to these API endpoints
