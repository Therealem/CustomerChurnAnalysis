"""Calculate business KPIs and grouped churn summaries with pandas."""

from pathlib import Path

import pandas as pd


# Use project-relative paths so the script can be run from any folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "telco_churn_clean.csv"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "processed"

REQUIRED_COLUMNS = {
    "customer_id",
    "churn_flag",
    "monthly_charges",
    "tenure",
    "contract",
    "internet_service",
    "payment_method",
}


def safe_percentage(numerator: int, denominator: int) -> float:
    """Return a percentage, or a missing value when the denominator is zero."""
    if denominator == 0:
        return float("nan")
    return numerator / denominator * 100


def format_number(value: float, format_text: str) -> str:
    """Format a number while safely displaying missing results as N/A."""
    if pd.isna(value):
        return "N/A"
    return format(value, format_text)


def build_grouped_analysis(
    data: pd.DataFrame, group_column: str
) -> pd.DataFrame:
    """Calculate customer counts and churn rate for one business segment."""
    grouped = (
        data.groupby(group_column, observed=True, dropna=False, sort=False)
        .agg(
            total_customers=("customer_id", "size"),
            churned_customers=("churn_flag", lambda values: values.eq(1).sum()),
            retained_customers=("churn_flag", lambda values: values.eq(0).sum()),
        )
        .reset_index()
    )

    grouped["churn_rate_percent"] = (
        grouped["churned_customers"] / grouped["total_customers"] * 100
    ).round(2)

    # Keep custom tenure and charge bands in their intended business order.
    if isinstance(data[group_column].dtype, pd.CategoricalDtype):
        grouped = grouped.sort_values(group_column).reset_index(drop=True)

    return grouped


def print_grouped_analysis(title: str, grouped: pd.DataFrame) -> None:
    """Print a grouped result with an easy-to-read percentage column."""
    printable = grouped.copy()
    printable["churn_rate_percent"] = printable["churn_rate_percent"].map(
        lambda value: format_number(value, ".2f") + "%"
        if not pd.isna(value)
        else "N/A"
    )
    print(f"\n{title}")
    print("-" * len(title))
    print(printable.to_string(index=False))


def main() -> None:
    """Load cleaned data, calculate KPIs, and save the analysis tables."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned data not found: {INPUT_PATH}\n"
            "Run src/clean_data.py before running this script."
        )

    customers = pd.read_csv(INPUT_PATH)

    # Stop with a clear message if the cleaned file does not have the needed fields.
    missing_columns = REQUIRED_COLUMNS.difference(customers.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"The cleaned dataset is missing columns: {missing_list}")

    # Convert the numeric fields safely. Unexpected text becomes a missing value.
    for column in ["churn_flag", "monthly_charges", "tenure"]:
        customers[column] = pd.to_numeric(customers[column], errors="coerce")

    # Each row should represent one customer. Keep the first record only if an ID
    # unexpectedly appears more than once, so customers are not double-counted.
    duplicate_customer_ids = int(customers["customer_id"].duplicated().sum())
    if duplicate_customer_ids:
        print(
            f"Warning: {duplicate_customer_ids} duplicate customer IDs found. "
            "Only the first record for each ID will be analyzed."
        )
        customers = customers.drop_duplicates(subset="customer_id", keep="first")

    total_customers = len(customers)
    churned_customers = int(customers["churn_flag"].eq(1).sum())
    retained_customers = int(customers["churn_flag"].eq(0).sum())
    churn_rate = safe_percentage(churned_customers, total_customers)
    retention_rate = safe_percentage(retained_customers, total_customers)
    average_monthly_charges = customers["monthly_charges"].mean()
    average_tenure = customers["tenure"].mean()
    monthly_revenue_at_risk = customers.loc[
        customers["churn_flag"].eq(1), "monthly_charges"
    ].sum(min_count=1)

    # Save numeric values as well as presentation-ready values and units.
    kpi_summary = pd.DataFrame(
        [
            {
                "kpi": "Total customers",
                "value": total_customers,
                "unit": "customers",
                "formatted_value": f"{total_customers:,}",
            },
            {
                "kpi": "Churned customers",
                "value": churned_customers,
                "unit": "customers",
                "formatted_value": f"{churned_customers:,}",
            },
            {
                "kpi": "Retained customers",
                "value": retained_customers,
                "unit": "customers",
                "formatted_value": f"{retained_customers:,}",
            },
            {
                "kpi": "Churn rate",
                "value": round(churn_rate, 2),
                "unit": "percent",
                "formatted_value": format_number(churn_rate, ".2f") + "%",
            },
            {
                "kpi": "Retention rate",
                "value": round(retention_rate, 2),
                "unit": "percent",
                "formatted_value": format_number(retention_rate, ".2f") + "%",
            },
            {
                "kpi": "Average monthly charges",
                "value": round(average_monthly_charges, 2),
                "unit": "USD",
                "formatted_value": "$"
                + format_number(average_monthly_charges, ",.2f"),
            },
            {
                "kpi": "Average tenure",
                "value": round(average_tenure, 2),
                "unit": "months",
                "formatted_value": format_number(average_tenure, ".2f")
                + " months",
            },
            {
                "kpi": "Monthly revenue at risk from churned customers",
                "value": round(monthly_revenue_at_risk, 2),
                "unit": "USD",
                "formatted_value": "$"
                + format_number(monthly_revenue_at_risk, ",.2f"),
            },
        ]
    )

    print("Business KPI Summary")
    print("--------------------")
    for row in kpi_summary.itertuples(index=False):
        print(f"{row.kpi}: {row.formatted_value}")

    # Missing text categories remain visible instead of being silently discarded.
    for column in ["contract", "internet_service", "payment_method"]:
        customers[column] = customers[column].fillna("Missing")

    # Create the requested tenure bands with explicit, non-overlapping limits.
    tenure_group = pd.Series("Missing/out of range", index=customers.index)
    tenure_group.loc[customers["tenure"].between(0, 12, inclusive="both")] = (
        "0-12 months"
    )
    tenure_group.loc[customers["tenure"].gt(12) & customers["tenure"].le(24)] = (
        "13-24 months"
    )
    tenure_group.loc[customers["tenure"].gt(24) & customers["tenure"].le(48)] = (
        "25-48 months"
    )
    tenure_group.loc[customers["tenure"].gt(48) & customers["tenure"].le(72)] = (
        "49-72 months"
    )
    customers["tenure_group"] = pd.Categorical(
        tenure_group,
        categories=[
            "0-12 months",
            "13-24 months",
            "25-48 months",
            "49-72 months",
            "Missing/out of range",
        ],
        ordered=True,
    )

    # Define charge bands explicitly so $40, $70, and $100 are handled clearly.
    monthly_charge_group = pd.Series("Missing/out of range", index=customers.index)
    monthly_charge_group.loc[customers["monthly_charges"].lt(40)] = "<$40"
    monthly_charge_group.loc[
        customers["monthly_charges"].ge(40)
        & customers["monthly_charges"].le(70)
    ] = "$40-$70"
    monthly_charge_group.loc[
        customers["monthly_charges"].gt(70)
        & customers["monthly_charges"].le(100)
    ] = "$70-$100"
    monthly_charge_group.loc[customers["monthly_charges"].gt(100)] = ">$100"
    customers["monthly_charge_group"] = pd.Categorical(
        monthly_charge_group,
        categories=[
            "<$40",
            "$40-$70",
            "$70-$100",
            ">$100",
            "Missing/out of range",
        ],
        ordered=True,
    )

    grouped_outputs = [
        (
            "Churn by Contract",
            "contract",
            "churn_by_contract.csv",
        ),
        (
            "Churn by Internet Service",
            "internet_service",
            "churn_by_internet_service.csv",
        ),
        (
            "Churn by Payment Method",
            "payment_method",
            "churn_by_payment_method.csv",
        ),
        (
            "Churn by Tenure Group",
            "tenure_group",
            "churn_by_tenure_group.csv",
        ),
        (
            "Churn by Monthly Charge Group",
            "monthly_charge_group",
            "churn_by_monthly_charge_group.csv",
        ),
    ]

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    kpi_summary.to_csv(OUTPUT_DIRECTORY / "kpi_summary.csv", index=False)

    for title, group_column, file_name in grouped_outputs:
        grouped = build_grouped_analysis(customers, group_column)
        grouped.to_csv(OUTPUT_DIRECTORY / file_name, index=False)
        print_grouped_analysis(title, grouped)

    print(f"\nAnalysis files saved to: {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    main()
