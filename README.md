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

## Status
Work in progress: data cleaning, SQL analysis, Python analysis and an Excel dashboard are being added.
