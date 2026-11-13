-- =====================================================================
-- 05_rfm_segmentation.sql  -  RFM segmentation and churn-risk flag
--
-- Business question: which customer segments generate the most revenue,
-- and which are at risk of churning?
--
-- Rules
--   * Grain = one row per CUSTOMER (customer_unique_id). In Olist,
--     customer_id is re-issued for every order, so it cannot be used.
--   * Only valid orders: canceled / unavailable orders and orders with
--     no items are excluded (see v_orders in 00_views.sql).
--   * Reference date = the day after the last VALID order in the data.
--   * R and M scores are data-driven quintiles (NTILE 5); the exact
--     cut-off values are published by the rfm_cutoffs query.
--   * F cannot be split into quintiles because ~97% of customers buy
--     once, so F uses business logic: 1 order / 2 orders / 3+ orders.
-- =====================================================================

DROP TABLE IF EXISTS rfm_customers;
CREATE TABLE rfm_customers AS
WITH valid_orders AS (
    SELECT * FROM v_orders
    WHERE  order_status NOT IN ('canceled', 'unavailable')
      AND  gross_value IS NOT NULL
),
ref AS (
    SELECT julianday(DATE(MAX(order_purchase_timestamp), '+1 day')) AS ref_day
    FROM   valid_orders
),
base AS (
    SELECT  customer_unique_id,
            MAX(customer_state)                     AS state,
            CAST((SELECT ref_day FROM ref)
                 - julianday(DATE(MAX(order_purchase_timestamp))) AS INT) AS recency_days,
            COUNT(*)                                AS frequency,
            ROUND(SUM(gross_value), 2)              AS monetary,
            MIN(purchase_date)                      AS first_order,
            MAX(purchase_date)                      AS last_order,
            ROUND(AVG(review_score), 2)             AS avg_review
    FROM    valid_orders
    GROUP BY customer_unique_id
),
scored AS (
    SELECT  *,
            6 - NTILE(5) OVER (ORDER BY recency_days)   AS r_score,  -- 5 = most recent
            CASE WHEN frequency >= 3 THEN 3
                 WHEN frequency = 2  THEN 2
                 ELSE 1 END                             AS f_score,
            NTILE(5) OVER (ORDER BY monetary)           AS m_score   -- 5 = highest spend
    FROM    base
)
SELECT  *,
        r_score || f_score || m_score AS rfm_code,
        CASE
            WHEN f_score >= 2 AND r_score >= 4                 THEN 'Champions'
            WHEN f_score >= 2                                  THEN 'Loyal'
            WHEN r_score >= 4 AND m_score >= 4                 THEN 'Potential Loyalists'
            WHEN r_score >= 4                                  THEN 'New Customers'
            WHEN m_score >= 4                                  THEN 'At Risk'
            WHEN r_score = 3                                   THEN 'About to Sleep'
            ELSE                                                    'Lost'
        END AS segment,
        -- Stretch goal: churn flag as specified (one purchase, silent > 90 days)
        CASE WHEN recency_days > 90 AND frequency = 1 THEN 1 ELSE 0 END AS churn_flag,
        -- Prioritised version: the flag alone catches most customers, so rank by value
        CASE WHEN recency_days > 90 AND frequency = 1 AND m_score >= 4 THEN '1 High risk - high value'
             WHEN recency_days > 90 AND frequency = 1                  THEN '2 High risk - low value'
             ELSE '3 Active (<= 90 days or repeat buyer)' END AS churn_risk_tier
FROM    scored;

CREATE INDEX ix_rfm_segment ON rfm_customers(segment);

-- name: rfm_reference
SELECT  DATE(MAX(last_order), '+1 day')   AS reference_date,
        COUNT(*)                          AS customers,
        ROUND(SUM(monetary), 0)           AS revenue
FROM    rfm_customers;

-- name: rfm_cutoffs
-- The data-driven boundaries behind each R and M score.
SELECT  'Recency (days since last order)' AS metric, r_score AS score,
        MIN(recency_days) AS min_value, MAX(recency_days) AS max_value, COUNT(*) AS customers
FROM    rfm_customers GROUP BY r_score
UNION ALL
SELECT  'Monetary (R$ total spend)', m_score,
        MIN(monetary), MAX(monetary), COUNT(*)
FROM    rfm_customers GROUP BY m_score
UNION ALL
SELECT  'Frequency (orders)', f_score,
        MIN(frequency), MAX(frequency), COUNT(*)
FROM    rfm_customers GROUP BY f_score
ORDER BY 1, 2;

-- name: rfm_segment_summary
SELECT  segment,
        COUNT(*)                                              AS customers,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)    AS pct_customers,
        ROUND(SUM(monetary), 0)                               AS revenue,
        ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_revenue,
        ROUND(AVG(monetary), 2)                               AS avg_spend,
        ROUND(AVG(recency_days), 0)                           AS avg_recency_days,
        ROUND(AVG(frequency), 2)                              AS avg_orders,
        ROUND(AVG(avg_review), 2)                             AS avg_review,
        ROUND(100.0 * AVG(churn_flag), 1)                     AS pct_churn_flag
FROM    rfm_customers
GROUP BY segment
ORDER BY revenue DESC;

-- name: rfm_churn_risk
SELECT  churn_risk_tier,
        COUNT(*)                                              AS customers,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)    AS pct_customers,
        ROUND(SUM(monetary), 0)                               AS revenue,
        ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_revenue,
        ROUND(AVG(monetary), 2)                               AS avg_spend,
        ROUND(AVG(recency_days), 0)                           AS avg_recency_days
FROM    rfm_customers
GROUP BY churn_risk_tier
ORDER BY churn_risk_tier;

-- name: rfm_segment_by_state
-- Where the At Risk revenue sits geographically (top 10 states by At Risk revenue).
SELECT  state,
        COUNT(*)                                       AS at_risk_customers,
        ROUND(SUM(monetary), 0)                        AS at_risk_revenue,
        ROUND(AVG(avg_review), 2)                      AS avg_review
FROM    rfm_customers
WHERE   segment = 'At Risk'
GROUP BY state
ORDER BY at_risk_revenue DESC
LIMIT 10;

-- name: rfm_customers
SELECT * FROM rfm_customers ORDER BY monetary DESC;
