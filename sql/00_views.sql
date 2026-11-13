-- =====================================================================
-- 00_views.sql  -  reusable analytical views on top of the raw tables
-- Grain notes:
--   * customer_id is per ORDER; customer_unique_id is the real person.
--   * an order can have many items, many payments, one (deduplicated) review.
-- =====================================================================

DROP VIEW IF EXISTS v_order_value;
CREATE VIEW v_order_value AS
SELECT  oi.order_id,
        COUNT(*)                         AS n_items,
        COUNT(DISTINCT oi.seller_id)     AS n_sellers,
        ROUND(SUM(oi.price), 2)          AS items_value,
        ROUND(SUM(oi.freight_value), 2)  AS freight_value,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS gross_value
FROM    order_items oi
GROUP BY oi.order_id;

DROP VIEW IF EXISTS v_order_payment;
CREATE VIEW v_order_payment AS
SELECT  order_id,
        ROUND(SUM(payment_value), 2)  AS paid_value,
        MAX(payment_installments)     AS max_installments,
        -- main payment method = the one carrying the largest amount
        (SELECT p2.payment_type FROM payments p2
          WHERE p2.order_id = p.order_id
          ORDER BY p2.payment_value DESC LIMIT 1) AS main_payment_type
FROM    payments p
GROUP BY order_id;

-- One row per order: the fact table every analysis starts from.
DROP VIEW IF EXISTS v_orders;
CREATE VIEW v_orders AS
SELECT  o.order_id,
        c.customer_unique_id,
        c.customer_state,
        c.customer_city,
        o.order_status,
        o.order_purchase_timestamp,
        o.purchase_month,
        DATE(o.order_purchase_timestamp)     AS purchase_date,
        o.is_delivered,
        ROUND(o.delivery_days, 2)            AS delivery_days,
        ROUND(o.estimated_days, 2)           AS estimated_days,
        o.days_late,
        o.is_late,
        v.n_items, v.n_sellers, v.items_value, v.freight_value, v.gross_value,
        p.paid_value, p.max_installments, p.main_payment_type,
        r.review_score,
        r.has_comment
FROM    orders o
JOIN    customers c        ON c.customer_id = o.customer_id
LEFT JOIN v_order_value v  ON v.order_id = o.order_id
LEFT JOIN v_order_payment p ON p.order_id = o.order_id
LEFT JOIN reviews r        ON r.order_id = o.order_id;

-- Item-level view with category and seller location.
DROP VIEW IF EXISTS v_items;
CREATE VIEW v_items AS
SELECT  oi.order_id, oi.order_item_id, oi.product_id, oi.seller_id,
        oi.price, oi.freight_value,
        pr.category,
        s.seller_state, s.seller_city,
        o.purchase_month, o.order_status, o.is_late, o.delivery_days,
        c.customer_state, c.customer_unique_id,
        r.review_score
FROM    order_items oi
JOIN    orders o     ON o.order_id = oi.order_id
JOIN    customers c  ON c.customer_id = o.customer_id
LEFT JOIN products pr ON pr.product_id = oi.product_id
LEFT JOIN sellers s   ON s.seller_id = oi.seller_id
LEFT JOIN reviews r   ON r.order_id = oi.order_id;

-- name: orders_clean
-- Analysis-ready orders: the rows and columns every other query works from.
-- Used for the Orders_Clean tab in the workbook.
SELECT  v.order_id,
        v.customer_unique_id,
        v.customer_state,
        v.customer_city,
        v.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        v.delivery_days,
        v.days_late,
        v.is_late,
        v.n_items,
        v.n_sellers,
        v.items_value,
        v.freight_value,
        v.gross_value,
        v.main_payment_type,
        v.max_installments,
        v.review_score
FROM    v_orders v
JOIN    orders o ON o.order_id = v.order_id
WHERE   v.order_status NOT IN ('canceled', 'unavailable')
  AND   v.gross_value IS NOT NULL
ORDER BY o.order_purchase_timestamp;
