"""Load the raw Olist CSVs, clean them and save to SQLite + data/cleaned/."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "olist.db"
CLEAN = ROOT / "data" / "cleaned"
OUT = ROOT / "outputs"

FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "geolocation": "olist_geolocation_dataset.csv",
}

# Zip prefixes keep leading zeros, so read them as text.
STR_COLS = {
    "customers": {"customer_zip_code_prefix": str},
    "sellers": {"seller_zip_code_prefix": str},
    "geolocation": {"geolocation_zip_code_prefix": str},
}

DATE_COLS = {
    "orders": [
        "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

# Two categories in products have no English name in the translation file.
EXTRA_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_processors",
}


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(RAW / FILES[name], dtype=STR_COLS.get(name), encoding="utf-8-sig")
    for c in DATE_COLS.get(name, []):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def quality(name: str, df: pd.DataFrame, key: list[str] | None) -> dict:
    return {
        "table": name,
        "rows": len(df),
        "columns": df.shape[1],
        "null_cells": int(df.isna().sum().sum()),
        "cols_with_nulls": ", ".join(df.columns[df.isna().any()]) or "-",
        "duplicate_full_rows": int(df.duplicated().sum()),
        "primary_key": "+".join(key) if key else "-",
        "duplicate_keys": int(df.duplicated(key).sum()) if key else 0,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    CLEAN.mkdir(parents=True, exist_ok=True)
    report = []

    # customers
    customers = load("customers")
    customers["customer_city"] = customers["customer_city"].str.strip().str.title()
    report.append(quality("customers", customers, ["customer_id"]))

    # orders
    orders = load("orders")
    report.append(quality("orders", orders, ["order_id"]))
    # A handful of 'delivered' orders have no delivery date; flag rather than drop.
    orders["is_delivered"] = (
        (orders["order_status"] == "delivered") & orders["order_delivered_customer_date"].notna()
    ).astype(int)
    orders["delivery_days"] = (
        orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
    ).dt.total_seconds().div(86400).round(2)
    orders["estimated_days"] = (
        orders["order_estimated_delivery_date"] - orders["order_purchase_timestamp"]
    ).dt.total_seconds().div(86400).round(2)
    # positive = late, negative = early (in days vs the promised date)
    orders["days_late"] = (
        orders["order_delivered_customer_date"].dt.normalize() - orders["order_estimated_delivery_date"]
    ).dt.days
    orders["is_late"] = (orders["days_late"] > 0).astype(int).where(orders["is_delivered"] == 1)
    orders["purchase_month"] = orders["order_purchase_timestamp"].dt.to_period("M").astype(str)

    # order items
    items = load("order_items")
    report.append(quality("order_items", items, ["order_id", "order_item_id"]))

    # payments
    payments = load("payments")
    report.append(quality("payments", payments, ["order_id", "payment_sequential"]))
    payments = payments[payments["payment_type"] != "not_defined"]

    # reviews
    reviews = load("reviews")
    report.append(quality("reviews", reviews, ["review_id"]))
    # Some orders have >1 review; keep the most recent answer per order.
    reviews = (
        reviews.sort_values("review_answer_timestamp")
        .drop_duplicates("order_id", keep="last")
        .reset_index(drop=True)
    )
    reviews["has_comment"] = reviews["review_comment_message"].notna().astype(int)

    # products + categories
    products = load("products")
    report.append(quality("products", products, ["product_id"]))
    products = products.rename(columns={
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length",
    })
    trans = load("category_translation")
    trans = pd.concat([trans, pd.DataFrame(
        {"product_category_name": list(EXTRA_TRANSLATIONS),
         "product_category_name_english": list(EXTRA_TRANSLATIONS.values())})])
    products = products.merge(trans, on="product_category_name", how="left")
    products["category"] = products["product_category_name_english"].fillna("unknown")
    report.append(quality("category_translation", trans, ["product_category_name"]))

    # sellers
    sellers = load("sellers")
    sellers["seller_city"] = sellers["seller_city"].str.strip().str.title()
    report.append(quality("sellers", sellers, ["seller_id"]))

    # geolocation: 1M rows -> one point per zip prefix
    geo = load("geolocation")
    report.append(quality("geolocation", geo, None))
    # Keep only points inside Brazil's bounding box, then average per zip prefix.
    geo = geo[geo["geolocation_lat"].between(-34, 5.5) & geo["geolocation_lng"].between(-74, -34)]
    geo = (geo.groupby("geolocation_zip_code_prefix", as_index=False)
              .agg(lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean"),
                   state=("geolocation_state", "first"))
              .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"}))

    # write SQLite
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    tables = {
        "customers": customers, "orders": orders, "order_items": items, "payments": payments,
        "reviews": reviews, "products": products, "sellers": sellers, "geolocation": geo,
    }
    for name, df in tables.items():
        df = df.copy()
        for c in df.select_dtypes("datetime").columns:
            df[c] = df[c].dt.strftime("%Y-%m-%d %H:%M:%S")
        df.to_sql(name, con, index=False)
        df.to_csv(CLEAN / f"{name}.csv", index=False, lineterminator="\n")
        print(f"  {name:<14} {len(df):>9,} rows")

    con.executescript("""
        CREATE INDEX ix_orders_id        ON orders(order_id);
        CREATE INDEX ix_orders_customer  ON orders(customer_id);
        CREATE INDEX ix_customers_id     ON customers(customer_id);
        CREATE INDEX ix_customers_unique ON customers(customer_unique_id);
        CREATE INDEX ix_items_order      ON order_items(order_id);
        CREATE INDEX ix_items_product    ON order_items(product_id);
        CREATE INDEX ix_items_seller     ON order_items(seller_id);
        CREATE INDEX ix_payments_order   ON payments(order_id);
        CREATE INDEX ix_reviews_order    ON reviews(order_id);
        CREATE INDEX ix_products_id      ON products(product_id);
        CREATE INDEX ix_sellers_id       ON sellers(seller_id);
        CREATE INDEX ix_geo_zip          ON geolocation(zip_code_prefix);
    """)
    con.commit()
    con.close()

    pd.DataFrame(report).to_csv(OUT / "data_quality_report.csv", index=False, lineterminator="\n")
    print(f"\nDatabase written to {DB.relative_to(ROOT)}")
    print(pd.DataFrame(report).to_string(index=False))


if __name__ == "__main__":
    main()
