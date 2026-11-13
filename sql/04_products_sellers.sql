-- Categories and sellers.

-- name: category_performance
WITH c AS (
    SELECT  category,
            COUNT(*)                         AS items_sold,
            COUNT(DISTINCT order_id)         AS orders,
            SUM(price)                       AS revenue,
            AVG(price)                       AS avg_price,
            AVG(freight_value / NULLIF(price, 0)) AS freight_ratio,
            AVG(review_score)                AS avg_review,
            AVG(is_late)                     AS late_rate
    FROM    v_items
    WHERE   order_status NOT IN ('canceled', 'unavailable')
    GROUP BY category
)
SELECT  category,
        items_sold, orders,
        ROUND(revenue, 0)                    AS revenue,
        ROUND(avg_price, 2)                  AS avg_price,
        ROUND(100 * freight_ratio, 1)        AS freight_pct_of_price,
        ROUND(avg_review, 2)                 AS avg_review,
        ROUND(100 * late_rate, 1)            AS late_pct,
        RANK() OVER (ORDER BY revenue DESC)  AS revenue_rank,
        ROUND(100.0 * revenue / SUM(revenue) OVER (), 2) AS pct_revenue,
        -- Pareto: cumulative share of revenue
        ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC ROWS UNBOUNDED PRECEDING)
              / SUM(revenue) OVER (), 2)    AS cum_pct_revenue
FROM    c
ORDER BY revenue DESC;

-- name: category_growth_2017_vs_2018
-- Jan-Aug only so both years are comparable
SELECT  category,
        ROUND(SUM(CASE WHEN purchase_month BETWEEN '2017-01' AND '2017-08' THEN price END), 0) AS rev_2017_jan_aug,
        ROUND(SUM(CASE WHEN purchase_month BETWEEN '2018-01' AND '2018-08' THEN price END), 0) AS rev_2018_jan_aug,
        ROUND(100.0 * (SUM(CASE WHEN purchase_month BETWEEN '2018-01' AND '2018-08' THEN price END)
             - SUM(CASE WHEN purchase_month BETWEEN '2017-01' AND '2017-08' THEN price END))
             / SUM(CASE WHEN purchase_month BETWEEN '2017-01' AND '2017-08' THEN price END), 1) AS growth_pct
FROM    v_items
WHERE   order_status NOT IN ('canceled', 'unavailable')
GROUP BY category
HAVING  SUM(CASE WHEN purchase_month BETWEEN '2017-01' AND '2017-08' THEN price END) >= 50000
ORDER BY growth_pct DESC;

-- name: seller_scorecard
WITH s AS (
    SELECT  seller_id, seller_state,
            COUNT(DISTINCT order_id)      AS orders,
            SUM(price)                    AS revenue,
            AVG(review_score)             AS avg_review,
            AVG(is_late)                  AS late_rate,
            COUNT(DISTINCT category)      AS n_categories
    FROM    v_items
    WHERE   order_status NOT IN ('canceled', 'unavailable')
    GROUP BY seller_id, seller_state
)
SELECT  seller_id, seller_state, orders,
        ROUND(revenue, 0)        AS revenue,
        ROUND(avg_review, 2)     AS avg_review,
        ROUND(100 * late_rate, 1) AS late_pct,
        n_categories,
        CASE WHEN orders >= 50 AND avg_review < 3.5          THEN 'At risk - low rating'
             WHEN orders >= 50 AND late_rate > 0.15          THEN 'At risk - late shipping'
             WHEN orders >= 100 AND avg_review >= 4.3        THEN 'Star seller'
             WHEN orders < 10                                THEN 'Long tail'
             ELSE 'Core' END     AS seller_segment,
        NTILE(10) OVER (ORDER BY revenue DESC) AS revenue_decile
FROM    s
ORDER BY revenue DESC;

-- name: seller_concentration
WITH s AS (
    SELECT seller_id, SUM(price) AS revenue FROM v_items
    WHERE order_status NOT IN ('canceled', 'unavailable') GROUP BY seller_id
), r AS (
    SELECT revenue, PERCENT_RANK() OVER (ORDER BY revenue DESC) AS pr FROM s
)
SELECT  'Top 1%'  AS seller_group, ROUND(100.0 * SUM(CASE WHEN pr <= 0.01 THEN revenue END) / SUM(revenue), 1) AS pct_revenue FROM r
UNION ALL
SELECT  'Top 10%', ROUND(100.0 * SUM(CASE WHEN pr <= 0.10 THEN revenue END) / SUM(revenue), 1) FROM r
UNION ALL
SELECT  'Top 20%', ROUND(100.0 * SUM(CASE WHEN pr <= 0.20 THEN revenue END) / SUM(revenue), 1) FROM r
UNION ALL
SELECT  'Bottom 50%', ROUND(100.0 * SUM(CASE WHEN pr > 0.50 THEN revenue END) / SUM(revenue), 1) FROM r;
