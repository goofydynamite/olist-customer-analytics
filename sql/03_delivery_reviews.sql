-- Delivery times vs review scores.

-- name: review_by_delivery_delay
SELECT  CASE WHEN days_late <= -10 THEN '1 10+ days early'
             WHEN days_late <= -5  THEN '2 5-9 days early'
             WHEN days_late <= 0   THEN '3 0-4 days early / on time'
             WHEN days_late <= 3   THEN '4 1-3 days late'
             WHEN days_late <= 7   THEN '5 4-7 days late'
             WHEN days_late <= 14  THEN '6 8-14 days late'
             ELSE '7 15+ days late' END             AS delay_band,
        COUNT(*)                                    AS orders,
        ROUND(AVG(review_score), 2)                 AS avg_review,
        ROUND(100.0 * AVG(review_score <= 2), 1)    AS pct_negative,
        ROUND(100.0 * AVG(review_score = 5), 1)     AS pct_five_star
FROM    v_orders
WHERE   is_delivered = 1 AND review_score IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- name: review_score_distribution
SELECT  review_score,
        COUNT(*) AS orders,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct,
        ROUND(100.0 * AVG(has_comment), 1)                AS pct_with_comment,
        ROUND(100.0 * AVG(is_late), 1)                    AS pct_late
FROM    v_orders
WHERE   review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;

-- name: late_vs_ontime_summary
SELECT  CASE is_late WHEN 1 THEN 'Late' ELSE 'On time' END AS delivery,
        COUNT(*)                                 AS orders,
        ROUND(AVG(review_score), 2)              AS avg_review,
        ROUND(100.0 * AVG(review_score <= 2), 1) AS pct_negative,
        ROUND(AVG(delivery_days), 1)             AS avg_delivery_days
FROM    v_orders
WHERE   is_delivered = 1 AND review_score IS NOT NULL
GROUP BY is_late;

-- name: multi_seller_orders
SELECT  CASE WHEN n_sellers = 1 THEN '1 seller' ELSE '2+ sellers' END AS sellers_in_order,
        COUNT(*)                          AS orders,
        ROUND(AVG(review_score), 2)       AS avg_review,
        ROUND(100.0 * AVG(is_late), 1)    AS late_pct
FROM    v_orders
WHERE   is_delivered = 1 AND review_score IS NOT NULL
GROUP BY 1;

-- name: delivery_route_state_pairs
-- seller state to customer state, routes with 200+ items
SELECT  seller_state, customer_state,
        COUNT(*)                         AS items,
        ROUND(AVG(delivery_days), 1)     AS avg_delivery_days,
        ROUND(100.0 * AVG(is_late), 1)   AS late_pct,
        ROUND(AVG(review_score), 2)      AS avg_review
FROM    v_items
WHERE   order_status = 'delivered' AND delivery_days IS NOT NULL
GROUP BY seller_state, customer_state
HAVING  COUNT(*) >= 200
ORDER BY late_pct DESC
LIMIT 20;
