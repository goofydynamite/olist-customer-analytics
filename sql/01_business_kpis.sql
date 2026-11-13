-- =====================================================================
-- 01_business_kpis.sql  -  headline numbers and monthly trend
-- Revenue = item price + freight on non-cancelled/unavailable orders.
-- The data has a thin tail: Sep-Oct 2016 and Sep-Oct 2018 are partial,
-- so trend queries keep 2017-01 .. 2018-08.
-- =====================================================================

-- name: kpi_summary
SELECT  COUNT(*)                                        AS total_orders,
        COUNT(DISTINCT customer_unique_id)              AS unique_customers,
        ROUND(SUM(gross_value), 0)                      AS gross_revenue,
        ROUND(AVG(gross_value), 2)                      AS avg_order_value,
        ROUND(AVG(n_items), 2)                          AS avg_items_per_order,
        ROUND(100.0 * SUM(is_delivered) / COUNT(*), 2)  AS pct_delivered,
        ROUND(100.0 * AVG(is_late), 2)                  AS pct_late_of_delivered,
        ROUND(AVG(CASE WHEN is_delivered = 1 THEN delivery_days END), 1) AS avg_delivery_days,
        ROUND(AVG(review_score), 2)                     AS avg_review_score,
        MIN(purchase_date)                              AS first_order,
        MAX(purchase_date)                              AS last_order
FROM    v_orders
WHERE   order_status NOT IN ('canceled', 'unavailable');

-- name: monthly_trend
WITH m AS (
    SELECT  purchase_month,
            COUNT(*)                            AS orders,
            COUNT(DISTINCT customer_unique_id)  AS customers,
            SUM(gross_value)                    AS revenue,
            AVG(gross_value)                    AS aov,
            AVG(review_score)                   AS avg_review,
            AVG(is_late)                        AS late_rate
    FROM    v_orders
    WHERE   order_status NOT IN ('canceled', 'unavailable')
      AND   purchase_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY purchase_month
)
SELECT  purchase_month,
        orders,
        customers,
        ROUND(revenue, 0)                                   AS revenue,
        ROUND(aov, 2)                                       AS aov,
        ROUND(avg_review, 2)                                AS avg_review,
        ROUND(100 * late_rate, 1)                           AS late_rate_pct,
        -- month-over-month growth with LAG
        ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY purchase_month))
              / LAG(revenue) OVER (ORDER BY purchase_month), 1) AS revenue_mom_pct,
        -- 3-month moving average
        ROUND(AVG(revenue) OVER (ORDER BY purchase_month
              ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0)  AS revenue_3m_avg,
        -- running total
        ROUND(SUM(revenue) OVER (ORDER BY purchase_month), 0) AS revenue_cumulative
FROM    m
ORDER BY purchase_month;

-- name: order_status_mix
SELECT  order_status,
        COUNT(*) AS orders,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM    orders
GROUP BY order_status
ORDER BY orders DESC;

-- name: weekday_hour_heatmap
SELECT  CAST(strftime('%w', order_purchase_timestamp) AS INT) AS weekday_num,  -- 0 = Sunday
        CASE strftime('%w', order_purchase_timestamp)
             WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue' WHEN '3' THEN 'Wed'
             WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat' END   AS weekday,
        CAST(strftime('%H', order_purchase_timestamp) AS INT)  AS hour,
        COUNT(*) AS orders
FROM    orders
GROUP BY 1, 2, 3
ORDER BY 1, 3;

-- name: payment_mix
SELECT  payment_type,
        COUNT(DISTINCT order_id)                 AS orders,
        ROUND(SUM(payment_value), 0)             AS value,
        ROUND(100.0 * SUM(payment_value) / SUM(SUM(payment_value)) OVER (), 1) AS pct_value,
        ROUND(AVG(payment_installments), 2)      AS avg_installments,
        ROUND(AVG(payment_value), 2)             AS avg_payment
FROM    payments
GROUP BY payment_type
ORDER BY value DESC;

-- name: installments_vs_ticket
SELECT  CASE WHEN max_installments <= 1 THEN '1'
             WHEN max_installments <= 3 THEN '2-3'
             WHEN max_installments <= 6 THEN '4-6'
             WHEN max_installments <= 10 THEN '7-10'
             ELSE '11+' END                  AS installments_band,
        COUNT(*)                             AS orders,
        ROUND(AVG(paid_value), 2)            AS avg_order_value
FROM    v_orders
WHERE   main_payment_type = 'credit_card'
GROUP BY 1
ORDER BY MIN(max_installments);
