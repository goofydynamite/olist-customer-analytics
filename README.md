# Olist Customer Analytics

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) ![SQL](https://img.shields.io/badge/SQL-003B57?logo=sqlite&logoColor=white) ![Excel](https://img.shields.io/badge/Excel-217346?logo=microsoftexcel&logoColor=white)

An analysis of ~100k orders from Olist, a Brazilian online marketplace, between September 2016 and August 2018. I used Python to clean the data, SQL for most of the analysis, and Excel for the final dashboard.

The short version: delivery is what makes or breaks a review. Late orders average 2.3 stars against 4.3 for on-time ones. And almost nobody comes back: 97% of customers only ever placed one order.

![Excel dashboard](reports/figures/10_excel_dashboard.png)

## Questions I wanted to answer

1. How is the business growing, and when do people buy?
2. Do customers come back, and which ones are worth the most?
3. What causes bad reviews: the product or the delivery?
4. Which states, categories and sellers need attention?
5. Which customer segments bring in the most revenue, and which are about to churn?

## Main numbers

- 98,207 orders (excluding canceled / unavailable) from 94,990 customers
- R$ 15.74M in revenue (items + freight), average order R$ 160
- 6.8% of orders arrived after the promised date
- Average review 4.12 / 5
- Only 3.0% of customers ordered more than once
- Revenue for Jan-Aug 2018 was up 140% on Jan-Aug 2017

## What I found

**Late deliveries kill ratings.** Even 1-3 days late drops the average review from 4.1 to 3.3, and once an order is 4+ days late, 68-80% of reviews are 1 or 2 stars. A Mann-Whitney test confirms the gap (p < 0.001), and in a logistic regression on order features, days late was the strongest predictor of a bad review (AUC 0.74). Late-delivery rates spiked in Nov 2017 (Black Friday) and again in Feb-Mar 2018, when they reached 19%.

**There's almost no repeat business.** 97% of customers bought once. In any given month after their first order, only around 0.3% of a cohort buys again.

**At Risk customers hold the most revenue.** In the RFM segmentation, the "At Risk" group (high spenders who haven't been back in a while) is 22% of customers but 40% of revenue. Add "Potential Loyalists" and 38% of customers account for 68% of revenue.

**Orders split across sellers rate worse.** Orders with items from 2+ sellers average 2.86 stars vs 4.17, probably because they arrive as separate parcels.

**The North and Northeast are underserved.** Customers in AL, MA, SE, CE and PA wait 21-25 days (SP: 9), pay freight worth 43-54% of the item price, and give the lowest ratings.

**Seller revenue is concentrated.** The top 10% of sellers make 68% of revenue, and 38 sellers with 50+ orders either rate below 3.5 or deliver late more than 15% of the time.

What I'd do about it:
- Make delivery estimates realistic on slow routes, warn customers early when an order is running late, and rank sellers by on-time rate.
- Run a second-order programme (a coupon after delivery, reminders in the customer's category). Each extra 1% of customers making a second order is roughly 950 orders, or R$ 150k.
- Prioritise win-back for high-value customers who've gone quiet (details below).
- Look at regional carriers or fulfilment partners for the North/Northeast.

## RFM segmentation and churn risk

I scored every customer on Recency, Frequency and Monetary value in SQL ([`sql/05_rfm_segmentation.sql`](sql/05_rfm_segmentation.sql)) and wrote up the results in a [one-page recommendation](reports/RFM_recommendation.md). The segment summary and chart are also in the `RFM_Segments` tab of the workbook.

![RFM segments](reports/figures/04_rfm_segments.png)

| Segment | Customers | % of customers | % of revenue | Avg spend |
|---|---:|---:|---:|---:|
| At Risk | 21,092 | 22.2% | 40.2% | R$ 300 |
| Potential Loyalists | 14,604 | 15.4% | 28.1% | R$ 303 |
| Lost | 22,912 | 24.1% | 10.6% | R$ 73 |
| New Customers | 22,156 | 23.3% | 10.3% | R$ 73 |
| About to Sleep | 11,332 | 11.9% | 5.2% | R$ 72 |
| Loyal | 1,653 | 1.7% | 3.1% | R$ 299 |
| Champions | 1,234 | 1.3% | 2.5% | R$ 321 |

A few notes on how I built it:
- Everything is at customer level using `customer_unique_id`. Olist gives the same person a new `customer_id` for every order, so grouping by that would treat every order as a separate customer.
- Recency and Monetary scores are quintiles of the actual data (`NTILE(5)`), so the cut-offs aren't made up: 99 / 183 / 274 / 389 days for recency and R$ 55 / 88 / 133 / 209 for spend. Frequency can't be split that way because 97% of people bought once, so it's just 1, 2 or 3+ orders.
- Canceled and unavailable orders are removed first, and recency is measured from 2018-09-04, the day after the last valid order.

For churn, I flagged customers with one order and no purchase in the last 90 days. That catches 79% of customers, which is too many to act on, because the data stops in 2018 and so few people ever reorder. Splitting the flag by spend gives a usable list: 29,006 high-value flagged customers who together account for R$ 8.73M, or 55.5% of all revenue.

## The data

The 9 original CSVs from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (CC BY-NC-SA 4.0) are in [`data/raw/`](data/raw), untouched. The cleaned versions of 8 of them are in [`data/cleaned/`](data/cleaned).

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

How the tables connect:

```
customers 1──* orders 1──* order_items *──1 products ── category_translation
                  │  1──* payments          *──1 sellers
                  └─ 1──1 reviews
geolocation (zip code -> lat/lng) joins to customers and sellers
```

## Data cleaning

All of this happens in [`src/etl.py`](src/etl.py). The raw files are never modified. The cleaned tables go into a SQLite database and into `data/cleaned/` as CSVs. The checks are saved in [`outputs/data_quality_report.csv`](outputs/data_quality_report.csv) and the `Data_Quality` tab of the workbook.

| File | Problem | What I did |
|---|---|---|
| customers | 99,441 `customer_id`s but only 96,096 actual people (new id per order) | Used `customer_unique_id` for all customer metrics; tidied city names |
| orders | 160 missing approval dates, 1,783 missing carrier dates, 2,965 missing delivery dates; 8 orders marked "delivered" with no delivery date | Converted dates; only counted an order as delivered if it has a delivery date; added delivery-time columns |
| order_items | 775 orders have no items (almost all canceled / unavailable) | Kept them, but they add no revenue |
| payments | 3 rows with type `not_defined`; some orders paid in several parts | Dropped the 3 rows; summed payments per order |
| reviews | 814 duplicate review IDs; 547 orders with more than one review | Kept the latest review per order (98,673 left) |
| products | 610 with no category; 2 categories missing from the translation file; columns misspelled (`lenght`) | Set missing categories to `unknown`; translated the 2 by hand; fixed column names |
| category translation | File starts with a hidden byte-order mark | Read with `utf-8-sig` |
| sellers | Untidy city names | Trimmed and title-cased |
| geolocation | 1,000,163 rows, 261,831 exact duplicates, 42 points outside Brazil | Removed points outside Brazil and averaged to one point per zip code (19,010 rows) |
| all files | Zip codes like `01037` lose the leading zero if read as numbers | Read them as text |

Some more detail on the decisions:

- **Dates:** all date columns are parsed as datetimes; anything unparseable becomes blank instead of breaking the load.
- **New order columns:**
  - `delivery_days`: purchase to delivery
  - `estimated_days`: purchase to promised date
  - `days_late`: delivery minus promised date, in days; positive means late
  - `is_late`: set for delivered orders only
  - `purchase_month`
- **Missing dates** are left blank rather than filled in. Most belong to canceled, unavailable or still-shipping orders.
- **Revenue** is item price + freight, excluding canceled and unavailable orders. Category revenue uses item price only.
- **Payments:** when an order is split across methods (e.g. card + voucher), the one carrying the largest amount counts as the main payment type. The 9 payments of R$ 0.00 are vouchers, so I kept them.
- **Review comments:** 58,247 reviews have no comment. That's normal, since only the score is required, so I added a `has_comment` flag instead of dropping them.
- **Products:**
  - Translations: `pc_gamer` stays `pc_gamer`, and `portateis_cozinha_e_preparadores_de_alimentos` becomes `portable_kitchen_food_processors`.
  - Uncategorised products are kept as `unknown` so their sales still count.
  - The 2 products with no weight or dimensions are kept, because those columns aren't used.
- **Geolocation:** Brazil's bounding box is latitude -34 to 5.5 and longitude -74 to -34. For each zip code, the state comes from its first point.
- **Duplicate checks:** customers, orders, order items, payments, products and sellers had no duplicate keys or duplicate rows.
- **Database:** dates are stored as `YYYY-MM-DD HH:MM:SS` text so SQLite's date functions work, and the join keys are indexed.

Rules I applied in the analysis:
- **Delivery and review metrics:** delivery metrics only use delivered orders, and review metrics only use orders that have a review.
- **Ratios:** guarded against dividing by zero (`NULLIF` in SQL).
- **RFM:** only includes customers whose orders have items (94,983 people).
- **Review model:** rows with missing inputs are dropped.
- **Time windows:**
  - Sep-Dec 2016 and Sep-Oct 2018 have very few orders, so trend and cohort charts use Jan 2017 to Aug 2018.
  - Year-on-year comparisons use Jan-Aug of both years.
- **Same-day repeat orders:** 896 customers placed a "second" order on the same day as their first. These are probably split checkouts, so the 3% repeat rate is, if anything, a bit generous.

## SQL

[`src/run_sql.py`](src/run_sql.py) runs the files in [`sql/`](sql) in order and saves each query's result as a CSV in [`outputs/sql_results/`](outputs/sql_results).

| File | What's in it |
|---|---|
| [`00_views.sql`](sql/00_views.sql) | Two views used everywhere else: one row per order (`v_orders`) and one row per item (`v_items`), plus the analysis-ready orders table |
| [`01_business_kpis.sql`](sql/01_business_kpis.sql) | KPI summary, monthly trend with MoM growth / 3-month average / running total, order status, weekday × hour, payment mix |
| [`02_customers_retention.sql`](sql/02_customers_retention.sql) | Repeat purchases, days to second order, cohort retention, state performance |
| [`03_delivery_reviews.sql`](sql/03_delivery_reviews.sql) | Reviews by delivery delay, late vs on time, multi-seller orders, most delayed routes |
| [`04_products_sellers.sql`](sql/04_products_sellers.sql) | Category Pareto, category growth 2017 vs 2018, seller scorecard, seller concentration |
| [`05_rfm_segmentation.sql`](sql/05_rfm_segmentation.sql) | RFM scores, cut-offs, segments, churn flag, At Risk revenue by state |

Mostly CTEs and window functions (`LAG`, `RANK`, `NTILE`, `PERCENT_RANK`, `ROW_NUMBER`, running totals), plus `CASE` bucketing and date maths with `julianday` / `strftime`.

Here's the query result that led to the main finding:

| Delivered vs promised date | Orders | Avg review | 1-2 star reviews |
|---|---:|---:|---:|
| 10+ days early | 61,523 | 4.32 | 8.9% |
| 0-4 days early / on time | 7,888 | 4.12 | 11.4% |
| 1-3 days late | 1,852 | 3.29 | 32.1% |
| 4-7 days late | 1,748 | 2.10 | 67.7% |
| 8-14 days late | 1,446 | 1.67 | 80.2% |

## Python

The notebook [`notebooks/olist_analysis.ipynb`](notebooks/olist_analysis.ipynb) picks up the SQL results and does the parts that are easier in Python:
- the Mann-Whitney test on late vs on-time reviews
- the logistic regression for bad reviews
- the state-level regression of review score on delivery time
- the cohort heatmap, the customer map and the rest of the charts

It's generated from [`src/analysis.py`](src/analysis.py) by [`src/make_notebook.py`](src/make_notebook.py).

| | |
|---|---|
| ![Monthly revenue](reports/figures/01_monthly_revenue.png) | ![Review vs delay](reports/figures/05_review_vs_delay.png) |
| ![Cohort retention](reports/figures/03_cohort_retention.png) | ![Negative review drivers](reports/figures/06_negative_review_drivers.png) |
| ![States](reports/figures/07_states.png) | ![Top categories](reports/figures/09_top_categories.png) |
| ![Customer map](reports/figures/08_customer_map.png) | ![Orders by weekday and hour](reports/figures/02_weekday_hour_heatmap.png) |

## Excel

[`excel/Olist_Customer_Dashboard.xlsx`](excel/Olist_Customer_Dashboard.xlsx) has a one-page dashboard, built from 7 charts and KPI tiles. It also has a dropdown where you pick a state and see its numbers next to the national ones (`INDEX`/`MATCH`).

The other tabs hold the query results, with formulas on top for shares, growth rates, rankings, Pareto classes and segment summaries (`SUMIFS`, `COUNTIFS`, `AVERAGEIFS`, `SUMPRODUCT`, `RANK`):
- **Analysis:** Monthly, States, Categories, Delivery_Reviews, Retention, RFM_Segments, Sellers, Payments
- **Checks:** Data_Quality
- **Orders data:**
  - Orders_Raw is the orders file exactly as downloaded (99,441 rows, 8 columns).
  - Orders_Clean is the version the analysis actually uses (98,199 rows, 19 columns). Canceled, unavailable and empty orders are removed, and each order is joined with the real customer, location, order value, payment, review and delivery times.

## Running it

```bash
pip install -r requirements.txt
python run_all.py
```

`run_all.py` runs the cleaning, the SQL, the notebook and the Excel build in order. On Windows with Excel installed, it also runs [`src/excel_recalc.ps1`](src/excel_recalc.ps1). That script adds the two orders tabs, recalculates the workbook and saves the dashboard image.

## Project structure

```
olist-customer-analytics/
├── run_all.py
├── src/            etl.py, run_sql.py, analysis.py, make_notebook.py, build_excel.py, excel_recalc.ps1
├── sql/            00_views ... 05_rfm_segmentation
├── notebooks/      olist_analysis.ipynb
├── excel/          Olist_Customer_Dashboard.xlsx
├── outputs/        sql_results/, data_quality_report.csv
├── reports/        RFM_recommendation.md, figures/
└── data/           raw/, cleaned/, processed/
```
