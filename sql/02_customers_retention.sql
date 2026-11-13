-- =====================================================================
-- 02_customers_retention.sql  -  repeat purchase, cohorts, states (RFM: see 05)
-- Uses customer_unique_id (the person), not customer_id (per order).
-- =====================================================================

-- name: repeat_purchase_distribution
WITH per_customer AS (
    SELECT customer_unique_id, COUNT(*) AS n_orders, SUM(gross_value) AS spend
    FROM   v_orders
    WHERE  order_status NOT IN ('canceled', 'unavailable')
    GROUP BY customer_unique_id
)
SELECT  CASE WHEN n_orders >= 4 THEN '4+' ELSE CAST(n_orders AS TEXT) END AS orders_per_customer,
        COUNT(*)                                            AS customers,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS pct_customers,
        ROUND(SUM(spend), 0)                                AS revenue,
        ROUND(100.0 * SUM(spend) / SUM(SUM(spend)) OVER (), 2) AS pct_revenue
FROM    per_customer
GROUP BY 1
ORDER BY MIN(n_orders);

-- name: days_to_second_order
WITH ranked AS (
    SELECT customer_unique_id,
           julianday(order_purchase_timestamp) AS t,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY order_purchase_timestamp) AS rn
    FROM   v_orders
    WHERE  order_status NOT IN ('canceled', 'unavailable')
), gaps AS (
    SELECT a.customer_unique_id, b.t - a.t AS days
    FROM   ranked a JOIN ranked b
      ON   a.customer_unique_id = b.customer_unique_id AND a.rn = 1 AND b.rn = 2
)
SELECT  CASE WHEN days < 1 THEN '0 same day'
             WHEN days <= 30 THEN '1 <=30 days'
             WHEN days <= 90 THEN '2 31-90 days'
             WHEN days <= 180 THEN '3 91-180 days'
             WHEN days <= 365 THEN '4 181-365 days'
             ELSE '5 >365 days' END AS gap_band,
        COUNT(*) AS customers
FROM    gaps
GROUP BY 1
ORDER BY 1;

-- name: cohort_retention
-- Cohort = month of first purchase. Retention = % of cohort buying again in month N.
WITH firsts AS (
    SELECT customer_unique_id, MIN(purchase_month) AS cohort
    FROM   v_orders
    WHERE  order_status NOT IN ('canceled', 'unavailable')
    GROUP BY customer_unique_id
), activity AS (
    SELECT DISTINCT o.customer_unique_id, f.cohort,
           (CAST(substr(o.purchase_month,1,4) AS INT) - CAST(substr(f.cohort,1,4) AS INT)) * 12
         + (CAST(substr(o.purchase_month,6,2) AS INT) - CAST(substr(f.cohort,6,2) AS INT)) AS month_n
    FROM   v_orders o JOIN firsts f USING (customer_unique_id)
    WHERE  o.order_status NOT IN ('canceled', 'unavailable')
), sizes AS (
    SELECT cohort, COUNT(*) AS cohort_size FROM firsts GROUP BY cohort
)
SELECT  a.cohort, s.cohort_size, a.month_n,
        COUNT(*) AS active_customers,
        ROUND(100.0 * COUNT(*) / s.cohort_size, 2) AS retention_pct
FROM    activity a JOIN sizes s USING (cohort)
WHERE   a.cohort BETWEEN '2017-01' AND '2018-08' AND a.month_n <= 12
GROUP BY a.cohort, a.month_n
ORDER BY a.cohort, a.month_n;

-- name: customers_by_state
SELECT  customer_state,
        COUNT(DISTINCT customer_unique_id)           AS customers,
        COUNT(*)                                     AS orders,
        ROUND(SUM(gross_value), 0)                   AS revenue,
        ROUND(AVG(gross_value), 2)                   AS aov,
        ROUND(AVG(freight_value), 2)                 AS avg_freight,
        ROUND(100.0 * AVG(freight_value / NULLIF(items_value,0)), 1) AS freight_pct_of_items,
        ROUND(AVG(CASE WHEN is_delivered=1 THEN delivery_days END), 1) AS avg_delivery_days,
        ROUND(100.0 * AVG(is_late), 1)               AS late_pct,
        ROUND(AVG(review_score), 2)                  AS avg_review
FROM    v_orders
WHERE   order_status NOT IN ('canceled', 'unavailable')
GROUP BY customer_state
ORDER BY revenue DESC;
