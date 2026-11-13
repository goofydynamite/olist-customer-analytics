# Olist E-commerce: Customer, Delivery & Retention Analytics

End-to-end analysis of ~100k orders from Olist, a Brazilian online marketplace (Sep 2016 to Aug 2018), using **SQL, Python and Excel**.

## Business questions
1. How is the business growing, and when do customers buy?
2. Do customers come back? Which customers are worth the most?
3. What causes bad reviews: the product or the delivery?
4. Which states, categories and sellers need attention?

## Data
The 9 original CSVs are in [`data/raw/`](data/raw), unchanged.
Source: [Brazilian E-Commerce Public Dataset by Olist (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), CC BY-NC-SA 4.0.

| File | Rows |
|---|---:|
| `olist_orders_dataset.csv` | 99,441 |
| `olist_customers_dataset.csv` | 99,441 |
| `olist_order_items_dataset.csv` | 112,650 |
| `olist_order_payments_dataset.csv` | 103,886 |
| `olist_order_reviews_dataset.csv` | 99,224 |
| `olist_products_dataset.csv` | 32,951 |
| `olist_sellers_dataset.csv` | 3,095 |
| `product_category_name_translation.csv` | 71 |
| `olist_geolocation_dataset.csv` | 1,000,163 |

## Data model

```
customers (customer_id, customer_unique_id) 1──* orders 1──* order_items *──1 products ── category_translation
                                                  │  1──* payments        *──1 sellers
                                                  └─ 1──1 reviews (deduplicated)
geolocation (zip prefix -> lat/lng) joins customers and sellers
```
`customer_id` is created per order. The real person is `customer_unique_id`, so every retention metric uses that key. Mixing them up is a common mistake with this dataset, and it would make the repeat rate look like 0%.

## Data cleaning

All cleaning happens in [`src/etl.py`](src/etl.py). The original files in [`data/raw/`](data/raw) are never modified. The cleaned tables are written both to the SQLite database and as CSV files in [`data/cleaned/`](data/cleaned), so you can open them directly in Excel or pandas. Every check is also logged in [`outputs/data_quality_report.csv`](outputs/data_quality_report.csv) and the `Data_Quality` tab of the workbook.

### Raw data at a glance

| File | Rows | Key | Issues found |
|---|---:|---|---|
| `olist_customers_dataset.csv` | 99,441 | `customer_id` | Only 96,096 real people; untidy city names |
| `olist_orders_dataset.csv` | 99,441 | `order_id` | 4,908 missing timestamps; 8 "delivered" orders with no delivery date |
| `olist_order_items_dataset.csv` | 112,650 | `order_id` + `order_item_id` | 775 orders have no items |
| `olist_order_payments_dataset.csv` | 103,886 | `order_id` + `payment_sequential` | 3 rows `not_defined`; split payments |
| `olist_order_reviews_dataset.csv` | 99,224 | `review_id` | 814 duplicate ids; 547 orders with >1 review |
| `olist_products_dataset.csv` | 32,951 | `product_id` | 610 without category; misspelled column names |
| `olist_sellers_dataset.csv` | 3,095 | `seller_id` | Untidy city names |
| `product_category_name_translation.csv` | 71 | `product_category_name` | 2 categories missing; BOM at start of file |
| `olist_geolocation_dataset.csv` | 1,000,163 | none | 261,831 exact duplicates; 42 points outside Brazil |

### Cleaning summary, file by file

| File | Problem found | What was done |
|---|---|---|
| **customers** | 99,441 `customer_id`s but only 96,096 real people: a new id is created for every order. | All customer and retention numbers use `customer_unique_id`. Without this, nobody would ever look like a repeat buyer. City names trimmed and title-cased. |
| **orders** | Missing dates: 160 approval, 1,783 handed to carrier, 2,965 delivered. 8 orders say "delivered" but have no delivery date. | Text dates converted to real dates. An order counts as delivered only if its status is `delivered` **and** it has a date. Added `delivery_days`, `estimated_days`, `days_late` (vs the promised date), `is_late` and `purchase_month`. |
| **order_items** | 775 orders (mostly canceled or unavailable) have no items. | Kept, but they add no revenue. Revenue = item price + freight, excluding canceled and unavailable orders. |
| **payments** | 3 rows with type `not_defined`. Some orders are split across several payments. | The 3 rows are removed. Payments are summed per order, and the method carrying the largest amount is recorded as the main one. |
| **reviews** | 814 duplicate `review_id`s; 547 orders with more than one review. 58k reviews have no text comment (normal). | Kept the latest review per order, leaving 98,673. Added a `has_comment` flag. |
| **products** | 610 products with no category. 2 categories missing from the translation file. Misspelled column names (`lenght`). | Missing categories set to `unknown`. Translated `pc_gamer` and `portateis_cozinha...` by hand. Fixed the column names. |
| **category translation** | The file starts with an invisible character (BOM). | Read with `utf-8-sig` so the first column name comes through correctly. |
| **sellers** | Untidy city names | Trimmed and title-cased |
| **geolocation** | 1,000,163 rows: 261,831 exact duplicates, 42 points outside Brazil, many points per zip code | Points outside Brazil removed, then averaged to one point per zip code, leaving 19,010 rows. Used for the customer map. |
| **all files** | Zip codes like `01037` lose their leading zero when read as numbers. | Read as text. |
| **time range** | Sep-Dec 2016 and Sep-Oct 2018 have very few orders. | Trend charts use Jan 2017 to Aug 2018 only. |

### Step by step

**1. Read everything with the right types**
- Zip code prefixes (`01037`) are read as **text**, so leading zeros are not lost.
- All date columns (purchase, approval, carrier, delivery, estimated delivery, shipping limit, review dates) are parsed into real datetimes; unparseable values become null instead of failing.
- The translation file starts with an invisible byte-order mark, so it is read with `utf-8-sig` to keep the first column name correct.

**2. Customers: separate the order id from the person**
- `customer_id` is generated **per order** (99,441 ids), while `customer_unique_id` is the real person (96,096).
- Every customer, repeat-purchase, cohort and RFM metric uses `customer_unique_id`. Using `customer_id` would make every customer look like a one-time buyer.
- City names trimmed and title-cased (`sao paulo` to `Sao Paulo`).

**3. Orders: define "delivered" and add delivery metrics**
- Missing timestamps are left as null, not filled in: 160 approval dates, 1,783 carrier dates and 2,965 customer delivery dates. Most belong to canceled, unavailable or in-transit orders.
- An order counts as **delivered** only if its status is `delivered` **and** it has a delivery date. That excludes 8 inconsistent orders.
- New columns:
  - `delivery_days`: purchase to delivery
  - `estimated_days`: purchase to promised date
  - `days_late`: delivery date minus promised date, in whole days (positive = late)
  - `is_late`: set only for delivered orders
  - `purchase_month`: for trends and cohorts

**4. Order items: define revenue**
- Revenue = item `price` + `freight_value`, summed per order.
- Canceled and unavailable orders are excluded from revenue and KPIs. The 775 orders with no items (almost all canceled or unavailable) therefore add nothing.
- Category-level revenue uses item price only, without freight.

**5. Payments**
- 3 rows with `payment_type = not_defined` removed.
- Orders paid with several methods (for example card + voucher) are summed per order. The method carrying the largest amount is recorded as the order's main payment type, along with the maximum number of installments.

**6. Reviews: one review per order**
- 814 `review_id`s appear more than once, and 547 orders have more than one review.
- Kept the **most recent answer per order**, leaving 98,673 reviews, so no order is double-counted in review averages.
- 58,247 reviews have no text comment. That is normal (the score is mandatory, text is optional), so a `has_comment` flag is added instead of dropping them.

**7. Products and categories**
- Misspelled source columns fixed: `product_name_lenght` and `product_description_lenght` become `..._length`.
- 2 Portuguese categories missing from the translation file were translated by hand:
  - `pc_gamer` becomes `pc_gamer`
  - `portateis_cozinha_e_preparadores_de_alimentos` becomes `portable_kitchen_food_processors`
- 610 products with no category are labelled `unknown`, not dropped, so their sales still count.
- The English name is joined onto every product as a single `category` column, so SQL never has to deal with Portuguese names.
- 2 products with no weight or dimensions are kept, since those columns aren't used in the analysis.

**8. Sellers**
- City names trimmed and title-cased.

**9. Geolocation: 1M rows down to one point per zip code**
- The raw file has many GPS points per zip prefix, including 261,831 exact duplicates.
- Points outside Brazil's bounding box are removed: latitude -34 to 5.5, longitude -74 to -34. That drops 42 points.
- Remaining points are averaged into **one lat/lng per zip prefix**, leaving 19,010 rows. These are used for the customer map. The state is taken from the first point for each zip.

**10. Load into SQLite**
- 8 clean tables written to `data/olist.db` **and** to `data/cleaned/*.csv` (customers, orders, order_items, payments, reviews, products, sellers, geolocation), with 12 indexes in the database on the join keys (order, customer, product, seller, zip) so the SQL layer runs in seconds.
- Dates are stored as `YYYY-MM-DD HH:MM:SS` text, the format SQLite's date functions (`DATE`, `strftime`, `julianday`) expect.
- The data-quality report is measured on the **raw** files, before any cleaning, so it shows the problems as they arrived.

**11. Checks that found nothing to fix**
- No duplicate keys in customers, orders, order items, payments, products or sellers.
- No fully duplicated rows in any table except geolocation.
- 9 payments of R$ 0.00 are vouchers, not errors, so they are kept.

**12. Analysis-level rules (in SQL and Python)**
- **Which orders count:** revenue, KPIs, customer and category metrics exclude `canceled` and `unavailable` orders.
- **Delivery metrics** (delivery days, late rate, review vs delay) use delivered orders only.
- **Review metrics** use only orders that have a review.
- **No divide-by-zero:** freight-to-price ratios use `NULLIF(price, 0)` in SQL and `replace(0, NaN)` in Python.
- **RFM** includes only customers whose orders have items (94,983 people). Recency is measured from one day after the last order in the data (the last order is on 2018-10-17).
- **Review-driver model:** rows missing any model input are dropped before training.
- **Time window:** Sep-Dec 2016 and Sep-Oct 2018 have very few orders, so trend and cohort charts use **Jan 2017 to Aug 2018**.
- **Like-for-like growth:** year-on-year comparisons use Jan-Aug of both years.
- **Same-day "second orders":** 896 customers placed a second order on the same day as their first. These are probably split checkouts rather than true loyalty, so the 3% repeat rate is, if anything, slightly optimistic.

## SQL analysis

All SQL runs on the SQLite database built by the ETL. [`src/run_sql.py`](src/run_sql.py) executes the files in [`sql/`](sql) in order and saves each named query's result to [`outputs/sql_results/`](outputs/sql_results).

```bash
python src/run_sql.py
```

| File | Queries |
|---|---|
| [`00_views.sql`](sql/00_views.sql) | Reusable views: `v_orders` (one row per order with value, payment, review and delivery fields) and `v_items` (one row per item with category and seller) |
| [`01_business_kpis.sql`](sql/01_business_kpis.sql) | KPI summary, monthly trend (MoM growth, 3-month average, running total), order status mix, weekday x hour heatmap, payment mix, installments vs order value |
| [`02_customers_retention.sql`](sql/02_customers_retention.sql) | Repeat-purchase distribution, days to second order, monthly cohort retention, RFM base scores, performance by state |
| [`03_delivery_reviews.sql`](sql/03_delivery_reviews.sql) | Review score by delivery delay, review distribution, late vs on time, multi-seller orders, worst seller-to-customer routes |
| [`04_products_sellers.sql`](sql/04_products_sellers.sql) | Category Pareto, category growth 2018 vs 2017, seller scorecard and segments, seller revenue concentration |

**Techniques used:** multi-table joins, views, CTEs, `CASE` bucketing, window functions (`LAG`, moving averages, running totals, `RANK`, `NTILE`, `PERCENT_RANK`, `ROW_NUMBER`), `HAVING`, `UNION ALL`, and date maths with `julianday` / `strftime`.

**First results from SQL**

| Delivery vs promised date | Orders | Avg review | 1-2 star reviews |
|---|---:|---:|---:|
| 10+ days early | 61,523 | 4.32 | 8.9% |
| 0-4 days early / on time | 7,888 | 4.12 | 11.4% |
| 1-3 days late | 1,852 | 3.29 | 32.1% |
| 4-7 days late | 1,748 | 2.10 | 67.7% |
| 8-14 days late | 1,446 | 1.67 | 80.2% |

- 97% of customers placed only one order.
- The top 10% of sellers generate 68% of item revenue.

## Python analysis

[`notebooks/olist_analysis.ipynb`](notebooks/olist_analysis.ipynb) reads the SQL results and the database, adds statistics, segmentation and a simple model, and saves the charts to [`reports/figures/`](reports/figures). The notebook is generated from [`src/analysis.py`](src/analysis.py) by [`src/make_notebook.py`](src/make_notebook.py), so the script and the notebook never drift apart.

```bash
python src/make_notebook.py
```

| Analysis | Method | Result |
|---|---|---|
| Growth | Monthly revenue with a 3-month average | Revenue Jan-Aug 2018 was **+140%** vs Jan-Aug 2017; Nov-2017 (Black Friday) is the peak month |
| Late vs on-time reviews | Mann-Whitney U test | **4.29 vs 2.27** stars, p < 0.001 |
| What predicts a 1-2 star review | Logistic regression on 8 order features (standardised) | Test ROC-AUC **0.74**; days late and total delivery time are the strongest drivers |
| Customer value | RFM segmentation (Recency and Monetary quintiles, repeat purchase as loyalty signal) | 8 segments, each with a recommended action |
| Regions | State-level regression of review on delivery days | Slower states rate lower |

### RFM segments

| Segment | Customers | Share of revenue | Avg spend (R$) | Recommended action |
|---|---:|---:|---:|---|
| New high-value | 14,611 | 28.2% | 303 | Second-order coupon within 30 days |
| At risk big spenders | 14,041 | 27.6% | 309 | High-touch win-back; ask why they left |
| Promising big spenders | 7,045 | 12.5% | 280 | Reminder + loyalty points before they lapse |
| Hibernating | 22,931 | 10.6% | 73 | Seasonal campaigns only |
| New low-value | 22,138 | 10.3% | 73 | Cross-sell bundles, free-shipping nudges |
| Needs attention | 11,330 | 5.2% | 72 | Low-cost email reactivation |
| Loyal (lapsing) | 1,643 | 3.1% | 299 | Personalised win-back offers |
| Champions | 1,244 | 2.5% | 321 | VIP perks and referral programme |

Segment table: [`data/processed/rfm_segment_summary.csv`](data/processed/rfm_segment_summary.csv). Model coefficients: [`data/processed/negative_review_drivers.csv`](data/processed/negative_review_drivers.csv).

### Charts

| | |
|---|---|
| ![Monthly revenue](reports/figures/01_monthly_revenue.png) | ![Review vs delay](reports/figures/05_review_vs_delay.png) |
| ![Cohort retention](reports/figures/03_cohort_retention.png) | ![RFM segments](reports/figures/04_rfm_segments.png) |
| ![Negative review drivers](reports/figures/06_negative_review_drivers.png) | ![States](reports/figures/07_states.png) |
| ![Top categories](reports/figures/09_top_categories.png) | ![Customer map](reports/figures/08_customer_map.png) |
| ![Orders by weekday and hour](reports/figures/02_weekday_hour_heatmap.png) | |

## Excel dashboard

[`excel/Olist_Customer_Dashboard.xlsx`](excel/Olist_Customer_Dashboard.xlsx) is built by [`src/build_excel.py`](src/build_excel.py) from the SQL and Python outputs. The data tabs hold the query results as values; every KPI, ratio, growth rate, lookup and summary on top of them is a **live Excel formula** (431 formulas, 0 errors).

![Excel dashboard](reports/figures/10_excel_dashboard.png)

| Tab | What it shows | Excel features |
|---|---|---|
| **Dashboard** | 8 KPI tiles, 7 charts, key insights | Native charts; tiles are formulas over the data tabs |
| | **State lookup**: pick a state in the yellow cell | Data-validation dropdown + `INDEX`/`MATCH`; compares the state with the national late rate |
| **Monthly** | Orders, revenue, AOV, MoM growth, 3-month average, running total | `IFERROR`, `AVERAGE`, `SUM` with expanding ranges; data bars |
| **States** | 27 states: revenue, freight, delivery days, late rate, review | Revenue share and `RANK`; colour scales |
| **Categories** | 74 categories with Pareto A/B/C classes | Cumulative share with `SUM`; nested `IF`; low ratings highlighted |
| **Delivery_Reviews** | Review by delay band, score distribution, late vs on time, worst routes | `INDEX`/`MATCH` for the review gap |
| **Retention** | Repeat purchases and the monthly cohort retention matrix | Weighted average with `SUMPRODUCT` / `SUMIFS`; heatmap |
| **RFM_Segments** | 8 segments with recommended actions | Share formulas; data bars |
| **Sellers** | 3,053-seller scorecard (filterable) | `COUNTIFS`, `SUMIFS`, `AVERAGEIFS` summary by segment |
| **Payments** | Payment mix and installments vs order value | Excel Tables |
| **Data_Quality** | Raw-file checks and cleaning notes | |

To rebuild it:

```bash
python src/build_excel.py
```

On Windows with Excel installed, `powershell -File src/excel_recalc.ps1 -Png reports/figures/10_excel_dashboard.png` recalculates every formula and renders the dashboard image. Elsewhere, the workbook calculates when it is opened.

## Status
Work in progress: data cleaning, SQL analysis, Python analysis and an Excel dashboard are being added.
