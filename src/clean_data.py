"""Clean the IBM Telco Customer Churn dataset for later business analysis."""

from pathlib import Path
import re

import pandas as pd


# Build file paths from the project folder so the script works from any location.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "telco_churn_clean.csv"


def to_snake_case(column_name: str) -> str:
    """Convert a column name such as MonthlyCharges to monthly_charges."""
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", column_name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    return name.strip("_").lower()


def find_missing_or_blank_values(data: pd.DataFrame) -> pd.Series:
    """Count missing and blank cells in each column."""
    missing_or_blank = data.isna().copy()

    # Pandas does not always treat whitespace-only text as a missing value.
    for column in data.select_dtypes(include=["object", "string"]).columns:
        blank_values = data[column].astype("string").str.strip().eq("")
        missing_or_blank[column] = missing_or_blank[column] | blank_values.fillna(False)

    return missing_or_blank.sum()


def main() -> None:
    """Load, clean, validate, and save the customer dataset."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    # Load the original CSV without modifying the source file.
    customers = pd.read_csv(INPUT_PATH)
    rows_before = len(customers)

    print(f"Original shape: {customers.shape}")
    print("Original column names:")
    for column in customers.columns:
        print(f"  - {column}")

    # Report duplicate rows, but keep them so no customer records are removed.
    duplicates_found = int(customers.duplicated().sum())
    print(f"\nDuplicate rows found: {duplicates_found}")

    # Count both pandas missing values and strings that are empty or only spaces.
    missing_by_column = find_missing_or_blank_values(customers)
    missing_values_found = int(missing_by_column.sum())
    print(f"Missing or blank values found: {missing_values_found}")
    if missing_values_found:
        print("Missing or blank values by column:")
        for column, count in missing_by_column[missing_by_column > 0].items():
            print(f"  - {column}: {int(count)}")

    # Trim text values and represent blank strings consistently as missing values.
    text_columns = customers.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        customers[column] = customers[column].astype("string").str.strip()
        customers[column] = customers[column].replace("", pd.NA)

    # Standardize all column names before creating new fields.
    customers.columns = [to_snake_case(column) for column in customers.columns]

    # Invalid or blank TotalCharges values become missing instead of causing errors.
    customers["total_charges"] = pd.to_numeric(
        customers["total_charges"], errors="coerce"
    ).astype("Float64")
    invalid_total_charges = int(customers["total_charges"].isna().sum())
    print(
        "TotalCharges values that could not be converted: "
        f"{invalid_total_charges}"
    )

    # Create a numeric churn indicator while preserving the original churn column.
    customers["churn_flag"] = customers["churn"].map(
        {"Yes": 1, "No": 0}
    ).astype("Int64")

    # Create the processed folder if needed, then save the cleaned dataset.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    customers.to_csv(OUTPUT_PATH, index=False)
    rows_after = len(customers)

    print("\nCleaning summary")
    print("----------------")
    print(f"Rows before: {rows_before}")
    print(f"Rows after: {rows_after}")
    print(f"Duplicates found: {duplicates_found}")
    print(f"Missing values found: {missing_values_found}")
    print(f"Rows with invalid TotalCharges: {invalid_total_charges}")
    print(f"Cleaned dataset saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
