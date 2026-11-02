-- Customer Churn Business Analysis
-- Database: data/processed/customer_churn.db
-- Table: customers
-- These queries use descriptive analysis only; no predictive model is involved.


-- 1. What are the headline customer retention KPIs?
-- Multiplying by 100.0 forces decimal division in SQLite. NULLIF prevents a
-- divide-by-zero error if the table is ever empty.
SELECT
    COUNT(*) AS total_customers,
    SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END) AS churned_customers,
    SUM(CASE WHEN churn_flag = 0 THEN 1 ELSE 0 END) AS retained_customers,
    ROUND(
        100.0 * SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS churn_rate_percent,
    ROUND(
        100.0 * SUM(CASE WHEN churn_flag = 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS retention_rate_percent
FROM customers;


-- 2. How much monthly recurring revenue is associated with churned customers?
SELECT
    ROUND(
        COALESCE(
            SUM(CASE WHEN churn_flag = 1 THEN monthly_charges ELSE 0 END),
            0
        ),
        2
    ) AS monthly_revenue_at_risk_usd
FROM customers;


-- 3. How does churn vary by contract type?
SELECT
    COALESCE(contract, 'Missing') AS contract,
    COUNT(*) AS total_customers,
    SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END) AS churned_customers,
    SUM(CASE WHEN churn_flag = 0 THEN 1 ELSE 0 END) AS retained_customers,
    ROUND(
        100.0 * SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS churn_rate_percent
FROM customers
GROUP BY COALESCE(contract, 'Missing')
ORDER BY churn_rate_percent DESC, total_customers DESC;


-- 4. How does churn vary by internet service?
SELECT
    COALESCE(internet_service, 'Missing') AS internet_service,
    COUNT(*) AS total_customers,
    SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END) AS churned_customers,
    SUM(CASE WHEN churn_flag = 0 THEN 1 ELSE 0 END) AS retained_customers,
    ROUND(
        100.0 * SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS churn_rate_percent
FROM customers
GROUP BY COALESCE(internet_service, 'Missing')
ORDER BY churn_rate_percent DESC, total_customers DESC;


-- 5. How does churn vary by payment method?
SELECT
    COALESCE(payment_method, 'Missing') AS payment_method,
    COUNT(*) AS total_customers,
    SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END) AS churned_customers,
    SUM(CASE WHEN churn_flag = 0 THEN 1 ELSE 0 END) AS retained_customers,
    ROUND(
        100.0 * SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS churn_rate_percent
FROM customers
GROUP BY COALESCE(payment_method, 'Missing')
ORDER BY churn_rate_percent DESC, total_customers DESC;


-- 6. How does churn change as customer tenure increases?
-- The sort key keeps the tenure bands in chronological order.
WITH tenure_bands AS (
    SELECT
        churn_flag,
        CASE
            WHEN tenure BETWEEN 0 AND 12 THEN '0-12 months'
            WHEN tenure BETWEEN 13 AND 24 THEN '13-24 months'
            WHEN tenure BETWEEN 25 AND 48 THEN '25-48 months'
            WHEN tenure BETWEEN 49 AND 72 THEN '49-72 months'
            ELSE 'Missing/out of range'
        END AS tenure_group,
        CASE
            WHEN tenure BETWEEN 0 AND 12 THEN 1
            WHEN tenure BETWEEN 13 AND 24 THEN 2
            WHEN tenure BETWEEN 25 AND 48 THEN 3
            WHEN tenure BETWEEN 49 AND 72 THEN 4
            ELSE 5
        END AS sort_order
    FROM customers
),
tenure_summary AS (
    SELECT
        tenure_group,
        sort_order,
        COUNT(*) AS total_customers,
        SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END) AS churned_customers,
        SUM(CASE WHEN churn_flag = 0 THEN 1 ELSE 0 END) AS retained_customers
    FROM tenure_bands
    GROUP BY tenure_group, sort_order
)
SELECT
    tenure_group,
    total_customers,
    churned_customers,
    retained_customers,
    ROUND(
        100.0 * churned_customers / NULLIF(total_customers, 0),
        2
    ) AS churn_rate_percent
FROM tenure_summary
ORDER BY sort_order;


-- 7. How does churn vary across monthly charge bands?
-- Boundary rules: $40-$70 includes both $40 and $70; $70-$100 includes values
-- above $70 through $100. This avoids overlapping groups.
WITH charge_bands AS (
    SELECT
        churn_flag,
        CASE
            WHEN monthly_charges < 40 THEN 'Under $40'
            WHEN monthly_charges BETWEEN 40 AND 70 THEN '$40-$70'
            WHEN monthly_charges > 70 AND monthly_charges <= 100 THEN '$70-$100'
            WHEN monthly_charges > 100 THEN 'Over $100'
            ELSE 'Missing/out of range'
        END AS monthly_charge_group,
        CASE
            WHEN monthly_charges < 40 THEN 1
            WHEN monthly_charges BETWEEN 40 AND 70 THEN 2
            WHEN monthly_charges > 70 AND monthly_charges <= 100 THEN 3
            WHEN monthly_charges > 100 THEN 4
            ELSE 5
        END AS sort_order
    FROM customers
),
charge_summary AS (
    SELECT
        monthly_charge_group,
        sort_order,
        COUNT(*) AS total_customers,
        SUM(CASE WHEN churn_flag = 1 THEN 1 ELSE 0 END) AS churned_customers,
        SUM(CASE WHEN churn_flag = 0 THEN 1 ELSE 0 END) AS retained_customers
    FROM charge_bands
    GROUP BY monthly_charge_group, sort_order
)
SELECT
    monthly_charge_group,
    total_customers,
    churned_customers,
    retained_customers,
    ROUND(
        100.0 * churned_customers / NULLIF(total_customers, 0),
        2
    ) AS churn_rate_percent
FROM charge_summary
ORDER BY sort_order;


-- 8. Which combinations of contract, internet service, payment method, and
-- tenure have the highest churn rates?
-- A minimum of 30 customers removes very small combinations that could produce
-- unstable or misleading rates. Customer count remains visible for context.
WITH customer_combinations AS (
    SELECT
        COALESCE(contract, 'Missing') AS contract,
        COALESCE(internet_service, 'Missing') AS internet_service,
        COALESCE(payment_method, 'Missing') AS payment_method,
        CASE
            WHEN tenure BETWEEN 0 AND 12 THEN '0-12 months'
            WHEN tenure BETWEEN 13 AND 24 THEN '13-24 months'
            WHEN tenure BETWEEN 25 AND 48 THEN '25-48 months'
            WHEN tenure BETWEEN 49 AND 72 THEN '49-72 months'
            ELSE 'Missing/out of range'
        END AS tenure_group,
        churn_flag,
        monthly_charges
    FROM customers
    WHERE churn_flag IN (0, 1)
),
combination_summary AS (
    SELECT
        contract,
        internet_service,
        payment_method,
        tenure_group,
        COUNT(*) AS total_customers,
        SUM(churn_flag) AS churned_customers,
        ROUND(SUM(CASE WHEN churn_flag = 1 THEN monthly_charges ELSE 0 END), 2)
            AS monthly_revenue_at_risk_usd
    FROM customer_combinations
    GROUP BY
        contract,
        internet_service,
        payment_method,
        tenure_group
    HAVING COUNT(*) >= 30
)
SELECT
    contract,
    internet_service,
    payment_method,
    tenure_group,
    total_customers,
    churned_customers,
    ROUND(
        100.0 * churned_customers / NULLIF(total_customers, 0),
        2
    ) AS churn_rate_percent,
    monthly_revenue_at_risk_usd
FROM combination_summary
ORDER BY churn_rate_percent DESC, total_customers DESC
LIMIT 20;


-- 9. Which meaningful customer segments rank highest for churn?
-- This compares the major single-dimension segments on one ranked list. The
-- 100-customer minimum keeps the ranking focused on material business groups.
WITH customer_groups AS (
    SELECT
        *,
        CASE
            WHEN tenure BETWEEN 0 AND 12 THEN '0-12 months'
            WHEN tenure BETWEEN 13 AND 24 THEN '13-24 months'
            WHEN tenure BETWEEN 25 AND 48 THEN '25-48 months'
            WHEN tenure BETWEEN 49 AND 72 THEN '49-72 months'
            ELSE 'Missing/out of range'
        END AS tenure_group,
        CASE
            WHEN monthly_charges < 40 THEN 'Under $40'
            WHEN monthly_charges BETWEEN 40 AND 70 THEN '$40-$70'
            WHEN monthly_charges > 70 AND monthly_charges <= 100 THEN '$70-$100'
            WHEN monthly_charges > 100 THEN 'Over $100'
            ELSE 'Missing/out of range'
        END AS monthly_charge_group
    FROM customers
    WHERE churn_flag IN (0, 1)
),
segment_rollup AS (
    SELECT
        'Contract' AS segment_dimension,
        COALESCE(contract, 'Missing') AS customer_segment,
        COUNT(*) AS customer_count,
        SUM(churn_flag) AS churned_customers
    FROM customer_groups
    GROUP BY COALESCE(contract, 'Missing')

    UNION ALL

    SELECT
        'Internet service',
        COALESCE(internet_service, 'Missing'),
        COUNT(*),
        SUM(churn_flag)
    FROM customer_groups
    GROUP BY COALESCE(internet_service, 'Missing')

    UNION ALL

    SELECT
        'Payment method',
        COALESCE(payment_method, 'Missing'),
        COUNT(*),
        SUM(churn_flag)
    FROM customer_groups
    GROUP BY COALESCE(payment_method, 'Missing')

    UNION ALL

    SELECT
        'Tenure group',
        tenure_group,
        COUNT(*),
        SUM(churn_flag)
    FROM customer_groups
    GROUP BY tenure_group

    UNION ALL

    SELECT
        'Monthly charge group',
        monthly_charge_group,
        COUNT(*),
        SUM(churn_flag)
    FROM customer_groups
    GROUP BY monthly_charge_group
),
segment_metrics AS (
    SELECT
        segment_dimension,
        customer_segment,
        customer_count,
        churned_customers,
        ROUND(
            100.0 * churned_customers / NULLIF(customer_count, 0),
            2
        ) AS churn_rate_percent
    FROM segment_rollup
    WHERE customer_count >= 100
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY churn_rate_percent DESC, customer_count DESC
    ) AS risk_rank,
    segment_dimension,
    customer_segment,
    customer_count,
    churned_customers,
    churn_rate_percent
FROM segment_metrics
ORDER BY risk_rank;
