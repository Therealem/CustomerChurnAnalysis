"""Load the cleaned customer churn data into a SQLite database."""

from pathlib import Path
import sqlite3

import pandas as pd


# Build paths from the project folder so the script works from any location.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "telco_churn_clean.csv"
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "customer_churn.db"
TABLE_NAME = "customers"


def main() -> None:
    """Read the cleaned CSV and replace the customers table in SQLite."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned data not found: {INPUT_PATH}\n"
            "Run src/clean_data.py before building the database."
        )

    customers = pd.read_csv(INPUT_PATH)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # The connection context commits the completed write and closes safely.
    with sqlite3.connect(DATABASE_PATH) as connection:
        # Replace makes the script rerunnable without appending duplicate rows.
        customers.to_sql(
            TABLE_NAME,
            connection,
            if_exists="replace",
            index=False,
        )

        # Read the database count back to confirm how many rows were written.
        rows_written = connection.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME}"
        ).fetchone()[0]

    print(f"Rows written to '{TABLE_NAME}': {rows_written:,}")
    print(f"SQLite database saved to: {DATABASE_PATH}")


if __name__ == "__main__":
    main()
