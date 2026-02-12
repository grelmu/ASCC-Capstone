"""
csv_log_processor.py — Prototype CSV Manufacturing Log Processor

Processes batches of manufacturing operation CSV log files (e.g., 3D printing
sensor data), extracts numeric measurements per header, computes cumulative
statistics (min, max, mean) across all files, detects user-authored notes,
and returns structured JSON suitable for frontend display.

Architecture Notes:
    - In production, this statistical pipeline will be augmented or replaced
      by an LLM (Llama 3) for contextual summarization of manufacturing logs.
    - This prototype validates the data pipeline and establishes the JSON
      contract between the backend and frontend.

Typical CSV Structure (from ASCC 3D printing operations):
    DateTime, Line of G-Code, Cycle Time, Screw Torque, Upper Temperature,
    Middle Temperature, Lower Temperature, Nozzle Temperature, ...
    [Last column is named after the print job — reserved for user notes]

Usage:
    processor = CSVLogProcessor()
    processor.load_files(["log1.csv", "log2.csv", "log3.csv"])
    summary = processor.get_summary()  # Returns JSON-serializable dict


"""

import csv
import os
import json
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Constants: columns that contain metadata rather than sensor readings.
# These are excluded from statistical aggregation but still tracked.
# ---------------------------------------------------------------------------
METADATA_COLUMNS = {"DateTime", "Line of G-Code", "Cycle Time"}


class CSVLogProcessor:
    """
    Processes multiple CSV log files from manufacturing operations and
    computes cumulative statistics across all loaded files.

    Attributes:
        numeric_data:   Accumulated numeric values per header across all files.
        user_notes:     Collected text annotations found in the log files.
        file_metadata:  Provenance info (name, rows, time range) per file.
    """

    def __init__(self):
        """Initialize empty data structures for accumulation."""

        # Maps each numeric header to its list of observed values.
        # Example: { "Screw Torque": [0.6, 1.1, 0.6, ...] }
        self.numeric_data: Dict[str, List[float]] = {}

        # Stores user notes with source context for traceability.
        # Each entry: { "file", "row", "column", "content" }
        self.user_notes: List[Dict[str, Any]] = []

        # Tracks per-file metadata for provenance and frontend display.
        # Each entry: { "file_name", "row_count", "start_time", "end_time" }
        self.file_metadata: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def load_files(self, file_paths: List[str]) -> None:
        """
        Load and process a list of CSV file paths.

        Each file is independently parsed; its numeric values are merged
        into the cumulative dataset and any detected notes are recorded.

        Args:
            file_paths: Paths to CSV log files to process.

        Raises:
            ValueError: If file_paths is empty.
        """
        if not file_paths:
            raise ValueError("At least one file path is required.")

        for path in file_paths:
            if not os.path.exists(path):
                print(f"[WARNING] File not found, skipping: {path}")
                continue
            self._process_file(path)

    def get_summary(self) -> Dict[str, Any]:
        """
        Compute and return the cumulative summary as a JSON-ready dict.

        Returns a structured payload containing:
            - Per-header statistics (min, max, mean, sample count)
            - Collected user notes
            - File-level metadata for provenance

        Returns:
            Dictionary matching the frontend display contract.
        """
        return {
            "header_statistics": self._compute_statistics(),
            "user_notes": self.user_notes,
            "files_processed": self.file_metadata,
            "total_files": len(self.file_metadata),
            "total_data_points": sum(
                len(values) for values in self.numeric_data.values()
            ),
        }

    def get_summary_json(self, indent: int = 2) -> str:
        """
        Return the summary as a formatted JSON string.

        Convenience wrapper around get_summary() for debugging and
        direct API responses.

        Args:
            indent: JSON indentation level for readability.

        Returns:
            JSON string of the summary payload.
        """
        return json.dumps(self.get_summary(), indent=indent)

    # -----------------------------------------------------------------------
    # Internal Processing
    # -----------------------------------------------------------------------

    def _process_file(self, file_path: str) -> None:
        """
        Parse a single CSV file, extract numeric data and user notes.

        Handles the specific format of ASCC manufacturing logs:
        - Columns are space-padded after commas (stripped during parsing).
        - The last column is named after the print job and may contain notes.
        - All other columns (except metadata) contain numeric sensor data.

        Args:
            file_path: Path to the CSV file.
        """
        file_name = os.path.basename(file_path)
        row_count = 0
        first_timestamp: Optional[str] = None
        last_timestamp: Optional[str] = None

        with open(file_path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                print(f"[WARNING] No headers found in {file_name}, skipping.")
                return

            # Strip whitespace from headers (CSV has spaces after commas)
            headers = [h.strip() for h in reader.fieldnames]

            # Identify the notes column: the last column is named after the
            # print job (e.g., "7.5in x 8in Hex 2xBrim Rear Left PolyPro")
            notes_column = headers[-1]

            for row in reader:
                row_count += 1

                # Build a cleaned version of the row with stripped keys
                cleaned = {k.strip(): v.strip() if v else "" for k, v in row.items()}

                # Track timestamps for file metadata
                timestamp = cleaned.get("DateTime", "")
                if timestamp:
                    if first_timestamp is None:
                        first_timestamp = timestamp
                    last_timestamp = timestamp

                # Process each column in the row
                for header in headers:
                    value = cleaned.get(header, "")

                    # Skip empty values
                    if not value:
                        continue

                    # Check the notes column for user-authored text
                    if header == notes_column:
                        self._handle_potential_note(
                            value, file_name, row_count, header
                        )
                        continue

                    # Skip metadata columns (DateTime, etc.)
                    if header in METADATA_COLUMNS:
                        continue

                    # Attempt to parse as a numeric sensor reading
                    self._accumulate_numeric(header, value, file_name, row_count)

        # Record file-level metadata for provenance tracking
        self.file_metadata.append({
            "file_name": file_name,
            "row_count": row_count,
            "start_time": first_timestamp,
            "end_time": last_timestamp,
            "notes_column": notes_column,
        })

        print(f"[INFO] Processed {file_name}: {row_count} rows")

    def _accumulate_numeric(
        self, header: str, value: str, file_name: str, row: int
    ) -> None:
        """
        Attempt to parse a string value as a float and accumulate it.

        If the value cannot be parsed as numeric, it is treated as a
        potential user note (text annotation in an unexpected column).

        Args:
            header:    The column header this value belongs to.
            value:     The raw string value from the CSV cell.
            file_name: Source file name for note traceability.
            row:       Row number in the source file.
        """
        try:
            numeric_value = float(value)

            # Initialize the list for this header if first encounter
            if header not in self.numeric_data:
                self.numeric_data[header] = []

            self.numeric_data[header].append(numeric_value)

        except ValueError:
            # Non-numeric value in a numeric column — likely a user note
            # or annotation embedded in the sensor data.
            self.user_notes.append({
                "file": file_name,
                "row": row,
                "column": header,
                "content": value,
                "type": "inline_annotation",
            })

    def _handle_potential_note(
        self, value: str, file_name: str, row: int, column: str
    ) -> None:
        """
        Check if a value in the notes column contains meaningful text.

        Filters out empty strings and pure whitespace. Any remaining
        content is stored as a user note with full provenance context.

        Args:
            value:     The cell content to evaluate.
            file_name: Source file for traceability.
            row:       Row number (1-indexed) in the source file.
            column:    Column header where the note was found.
        """
        cleaned = value.strip()
        if not cleaned:
            return

        # If it parses as a number, it's data, not a note
        try:
            float(cleaned)
            return
        except ValueError:
            pass

        # This is genuine text content — store it as a user note
        self.user_notes.append({
            "file": file_name,
            "row": row,
            "column": column,
            "content": cleaned,
            "type": "user_note",
        })

    def _compute_statistics(self) -> List[Dict[str, Any]]:
        """
        Compute min, max, and mean for each numeric header.

        Returns a list of stat objects sorted alphabetically by header
        name for consistent frontend rendering.

        Returns:
            List of dicts, each containing:
                - header: Column name
                - min:    Minimum observed value
                - max:    Maximum observed value
                - mean:   Arithmetic mean (rounded to 4 decimal places)
                - count:  Number of data points
        """
        statistics = []

        for header, values in sorted(self.numeric_data.items()):
            if not values:
                continue

            statistics.append({
                "header": header,
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "mean": round(sum(values) / len(values), 4),
                "count": len(values),
            })

        return statistics


# ---------------------------------------------------------------------------
# Standalone execution: processes sample files and prints the summary.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    # Accept file paths as command-line arguments, or use a default glob
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        # Default: look for CSVs in the current directory
        import glob
        files = glob.glob("*.csv")

    if not files:
        print("No CSV files found. Pass file paths as arguments:")
        print("  python csv_log_processor.py file1.csv file2.csv")
        sys.exit(1)

    processor = CSVLogProcessor()
    processor.load_files(files)
    print("\n" + processor.get_summary_json())
