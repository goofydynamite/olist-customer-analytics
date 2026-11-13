"""
Step 4 - build the Excel dashboard from the SQL + Python outputs.

    python src/build_excel.py   ->  excel/Olist_Customer_Dashboard.xlsx

Data sheets hold the query results as values; every KPI, ratio, growth rate,
lookup and summary on top of them is a live Excel formula.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.comments import Comment
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "outputs" / "sql_results"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "excel" / "Olist_Customer_Dashboard.xlsx"

FONT = "Arial"
NAVY, BLUE, LIGHT, GREY = "1F2937", "2563EB", "EFF6FF", "6B7280"
F_TITLE = Font(name=FONT, size=18, bold=True, color=NAVY)
F_SUB = Font(name=FONT, size=10, italic=True, color=GREY)
F_H = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_B = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_KPI = Font(name=FONT, size=20, bold=True, color=BLUE)
F_KPI_L = Font(name=FONT, size=9, color=GREY)
FILL_H = PatternFill("solid", fgColor=NAVY)
FILL_TILE = PatternFill("solid", fgColor=LIGHT)
FILL_INPUT = PatternFill("solid", fgColor="FFFF00")
THIN = Side(style="thin", color="D1D5DB")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

FMT = {"int": "#,##0", "brl": '"R$" #,##0', "brl2": '"R$" #,##0.00', "pct": "0.0%",
       "dec1": "0.0", "dec2": "0.00", "txt": "@"}

r = lambda name: pd.read_csv(RES / f"{name}.csv")


def write_table(ws, df: pd.DataFrame, start_row: int, start_col: int, name: str,
                fmts: dict[str, str] | None = None, widths: dict[str, int] | None = None):
    """Write df as a formatted Excel Table. Returns (first_data_row, last_data_row)."""
    fmts = fmts or {}
    for j, col in enumerate(df.columns):
        c = ws.cell(start_row, start_col + j, col)
        c.font, c.fill, c.alignment = F_H, FILL_H, Alignment(horizontal="center", wrap_text=True)
    for i, row in enumerate(df.itertuples(index=False), start=start_row + 1):
        for j, v in enumerate(row):
            c = ws.cell(i, start_col + j, None if pd.isna(v) else v)
            c.font = F_B
            f = fmts.get(df.columns[j])
            if f:
                c.number_format = FMT.get(f, f)
    last = start_row + len(df)
    ref = f"{get_column_letter(start_col)}{start_row}:{get_column_letter(start_col + df.shape[1] - 1)}{last}"
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(t)
    for j, col in enumerate(df.columns):
        w = (widths or {}).get(col, max(10, min(32, len(str(col)) + 3)))
        ws.column_dimensions[get_column_letter(start_col + j)].width = w
    return start_row + 1, last


def header(ws, title: str, subtitle: str):
    ws["A1"], ws["A2"] = title, subtitle
    ws["A1"].font, ws["A2"].font = F_TITLE, F_SUB
    ws.sheet_view.showGridLines = False
    ws.row_dimensions[1].height = 28


def pct(df, cols):
    """SQL returns percentages as 0-100; Excel stores them as fractions."""
    for c in cols:
        df[c] = df[c] / 100
    return df


def main() -> None:
    wb = Workbook()
    wb.properties.creator = "Deepti Singh Kushwaha"
    wb.properties.title = "Olist Customer & Delivery Dashboard"
    dash = wb.active
    dash.title = "Dashboard"

    # ------------------------------------------------------------------ Monthly
    ws = wb.create_sheet("Monthly")
    header(ws, "Monthly performance", "Source: sql/01_business_kpis.sql > monthly_trend  (Jan-2017 to Aug-2018, complete months only)")
    m = r("monthly_trend")[["purchase_month", "orders", "customers", "revenue", "avg_review", "late_rate_pct"]]
    m = pct(m, ["late_rate_pct"]).rename(columns={
        "purchase_month": "Month", "orders": "Orders", "customers": "Customers", "revenue": "Revenue (R$)",
        "avg_review": "Avg review", "late_rate_pct": "Late rate"})
    m["AOV (R$)"] = None; m["MoM growth"] = None; m["3M avg revenue"] = None; m["Cumulative revenue"] = None
    m0, m1 = write_table(ws, m, 4, 1, "tMonthly",
                         {"Orders": "int", "Customers": "int", "Revenue (R$)": "brl", "Avg review": "dec2",
                          "Late rate": "pct", "AOV (R$)": "brl2", "MoM growth": "pct",
                          "3M avg revenue": "brl", "Cumulative revenue": "brl"})
    for i in range(m0, m1 + 1):
        ws[f"G{i}"] = f"=IFERROR(D{i}/B{i},0)"
        ws[f"H{i}"] = "" if i == m0 else f"=IFERROR(D{i}/D{i-1}-1,\"\")"
        ws[f"I{i}"] = f"=AVERAGE(D{max(m0, i-2)}:D{i})"
        ws[f"J{i}"] = f"=SUM(D${m0}:D{i})"
        for col, f in zip("GHIJ", ["brl2", "pct", "brl", "brl"]):
            ws[f"{col}{i}"].number_format, ws[f"{col}{i}"].font = FMT[f], F_B
    ws.conditional_formatting.add(f"H{m0+1}:H{m1}", FormulaRule(formula=[f"H{m0+1}<0"], font=Font(color="DC2626")))
    ws.conditional_formatting.add(f"D{m0}:D{m1}", DataBarRule(start_type="min", end_type="max", color="93C5FD"))
    ws.freeze_panes = "B5"

    # ------------------------------------------------------------------ States
    ws = wb.create_sheet("States")
    header(ws, "Performance by customer state", "Source: sql/02_customers_retention.sql > customers_by_state")
    s = pct(r("customers_by_state"), ["freight_pct_of_items", "late_pct"]).rename(columns={
        "customer_state": "State", "customers": "Customers", "orders": "Orders", "revenue": "Revenue (R$)",
        "aov": "AOV (R$)", "avg_freight": "Avg freight (R$)", "freight_pct_of_items": "Freight % of items",
        "avg_delivery_days": "Avg delivery days", "late_pct": "Late rate", "avg_review": "Avg review"})
    s["Revenue share"] = None; s["Revenue rank"] = None
    s0, s1 = write_table(ws, s, 4, 1, "tStates",
                         {"Customers": "int", "Orders": "int", "Revenue (R$)": "brl", "AOV (R$)": "brl2",
                          "Avg freight (R$)": "brl2", "Freight % of items": "pct", "Avg delivery days": "dec1",
                          "Late rate": "pct", "Avg review": "dec2", "Revenue share": "pct", "Revenue rank": "int"})
    for i in range(s0, s1 + 1):
        ws[f"K{i}"] = f"=D{i}/SUM($D${s0}:$D${s1})"
        ws[f"L{i}"] = f"=RANK(D{i},$D${s0}:$D${s1})"
        ws[f"K{i}"].number_format, ws[f"K{i}"].font, ws[f"L{i}"].font = FMT["pct"], F_B, F_B
    ws.conditional_formatting.add(f"H{s0}:H{s1}", ColorScaleRule(start_type="min", start_color="D1FAE5",
                                  mid_type="percentile", mid_value=50, mid_color="FEF3C7", end_type="max", end_color="FCA5A5"))
    ws.conditional_formatting.add(f"J{s0}:J{s1}", ColorScaleRule(start_type="min", start_color="FCA5A5",
                                  mid_type="percentile", mid_value=50, mid_color="FEF3C7", end_type="max", end_color="D1FAE5"))
    ws.conditional_formatting.add(f"I{s0}:I{s1}", DataBarRule(start_type="num", start_value=0, end_type="max", color="FCA5A5"))
    ws.freeze_panes = "B5"

    # ------------------------------------------------------------------ Categories
    ws = wb.create_sheet("Categories")
    header(ws, "Category performance (Pareto)", "Source: sql/04_products_sellers.sql > category_performance. Revenue = item price, excl. freight")
    c = r("category_performance")[["category", "items_sold", "orders", "revenue", "avg_price",
                                    "freight_pct_of_price", "avg_review", "late_pct"]]
    c = pct(c, ["freight_pct_of_price", "late_pct"]).rename(columns={
        "category": "Category", "items_sold": "Items sold", "orders": "Orders", "revenue": "Revenue (R$)",
        "avg_price": "Avg price (R$)", "freight_pct_of_price": "Freight % of price",
        "avg_review": "Avg review", "late_pct": "Late rate"})
    c["Share"] = None; c["Cumulative share"] = None; c["Pareto class"] = None
    c0, c1 = write_table(ws, c, 4, 1, "tCategories",
                         {"Items sold": "int", "Orders": "int", "Revenue (R$)": "brl", "Avg price (R$)": "brl2",
                          "Freight % of price": "pct", "Avg review": "dec2", "Late rate": "pct",
                          "Share": "pct", "Cumulative share": "pct"}, widths={"Category": 34})
    for i in range(c0, c1 + 1):
        ws[f"I{i}"] = f"=D{i}/SUM($D${c0}:$D${c1})"
        ws[f"J{i}"] = f"=SUM($I${c0}:I{i})"
        ws[f"K{i}"] = f'=IF(J{i}<=0.8,"A (top 80%)",IF(J{i}<=0.95,"B (next 15%)","C (tail 5%)"))'
        for col in "IJ":
            ws[f"{col}{i}"].number_format = FMT["pct"]
        for col in "IJK":
            ws[f"{col}{i}"].font = F_B
    ws.conditional_formatting.add(f"D{c0}:D{c1}", DataBarRule(start_type="min", end_type="max", color="93C5FD"))
    ws.conditional_formatting.add(f"G{c0}:G{c1}", FormulaRule(formula=[f"G{c0}<3.8"], fill=PatternFill("solid", fgColor="FEE2E2")))
    ws.freeze_panes = "B5"

    # ------------------------------------------------------------------ Delivery & reviews
    ws = wb.create_sheet("Delivery_Reviews")
    header(ws, "Delivery delay vs customer review", "Source: sql/03_delivery_reviews.sql. Delivered orders that have a review")
    d = r("review_by_delivery_delay")
    d["delay_band"] = d["delay_band"].str[2:]
    d = pct(d, ["pct_negative", "pct_five_star"]).rename(columns={
        "delay_band": "Delivery vs promised date", "orders": "Orders", "avg_review": "Avg review",
        "pct_negative": "1-2 star share", "pct_five_star": "5 star share"})
    d["Share of orders"] = None
    d0, d1 = write_table(ws, d, 4, 1, "tDelay", {"Orders": "int", "Avg review": "dec2", "1-2 star share": "pct",
                                                "5 star share": "pct", "Share of orders": "pct"},
                         widths={"Delivery vs promised date": 30})
    for i in range(d0, d1 + 1):
        ws[f"F{i}"] = f"=B{i}/SUM($B${d0}:$B${d1})"
        ws[f"F{i}"].number_format, ws[f"F{i}"].font = FMT["pct"], F_B
    ws.conditional_formatting.add(f"C{d0}:C{d1}", ColorScaleRule(start_type="min", start_color="FCA5A5",
                                  end_type="max", end_color="A7F3D0"))

    rs = r("review_score_distribution")
    rs = pct(rs, ["pct", "pct_with_comment", "pct_late"]).rename(columns={
        "review_score": "Review score", "orders": "Orders", "pct": "Share", "pct_with_comment": "Has comment",
        "pct_late": "Late rate"})
    rs0, rs1 = write_table(ws, rs, d1 + 3, 1, "tReviewDist",
                           {"Orders": "int", "Share": "pct", "Has comment": "pct", "Late rate": "pct"})

    lv = pct(r("late_vs_ontime_summary"), ["pct_negative"]).rename(columns={
        "delivery": "Delivery", "orders": "Orders", "avg_review": "Avg review",
        "pct_negative": "1-2 star share", "avg_delivery_days": "Avg delivery days"})
    lv0, lv1 = write_table(ws, lv, rs1 + 3, 1, "tLateVsOnTime",
                           {"Orders": "int", "Avg review": "dec2", "1-2 star share": "pct", "Avg delivery days": "dec1"})
    ws[f"A{lv1 + 2}"] = "Review gap (on time minus late)"
    ws[f"A{lv1 + 2}"].font = F_BOLD
    ws[f"C{lv1 + 2}"] = (f'=INDEX(C{lv0}:C{lv1},MATCH("On time",A{lv0}:A{lv1},0))'
                         f'-INDEX(C{lv0}:C{lv1},MATCH("Late",A{lv0}:A{lv1},0))')
    ws[f"C{lv1 + 2}"].number_format, ws[f"C{lv1 + 2}"].font = "0.00", F_BOLD
    review_gap_cell = f"Delivery_Reviews!$C${lv1 + 2}"

    lanes = pct(r("delivery_route_state_pairs"), ["late_pct"]).rename(columns={
        "seller_state": "Seller state", "customer_state": "Customer state", "items": "Items",
        "avg_delivery_days": "Avg delivery days", "late_pct": "Late rate", "avg_review": "Avg review"})
    ws.cell(3, 9, "Worst seller -> customer lanes (min 200 items)").font = F_BOLD
    write_table(ws, lanes, 4, 9, "tLanes", {"Items": "int", "Avg delivery days": "dec1",
                                            "Late rate": "pct", "Avg review": "dec2"})

    # ------------------------------------------------------------------ Retention
    ws = wb.create_sheet("Retention")
    header(ws, "Repeat purchase & cohort retention", "Source: sql/02_customers_retention.sql. Customer = customer_unique_id")
    rp = pct(r("repeat_purchase_distribution"), ["pct_customers", "pct_revenue"]).rename(columns={
        "orders_per_customer": "Orders per customer", "customers": "Customers", "pct_customers": "Share of customers",
        "revenue": "Revenue (R$)", "pct_revenue": "Share of revenue"})
    rp["Orders per customer"] = rp["Orders per customer"].astype(str)
    rp0, rp1 = write_table(ws, rp, 4, 1, "tRepeat", {"Customers": "int", "Share of customers": "pct",
                                                    "Revenue (R$)": "brl", "Share of revenue": "pct"})
    ws[f"A{rp1 + 2}"], ws[f"A{rp1 + 2}"].font = "Repeat-customer rate", F_BOLD
    ws[f"B{rp1 + 2}"] = f'=1-INDEX(B{rp0}:B{rp1},MATCH("1",A{rp0}:A{rp1},0))/SUM(B{rp0}:B{rp1})'
    ws[f"B{rp1 + 2}"].number_format, ws[f"B{rp1 + 2}"].font = FMT["pct"], F_BOLD
    repeat_cell = f"Retention!$B${rp1 + 2}"

    coh = r("cohort_retention")
    piv = coh.pivot(index="cohort", columns="month_n", values="retention_pct").reindex(columns=range(0, 13))
    sizes = coh.drop_duplicates("cohort").set_index("cohort")["cohort_size"]
    top = rp1 + 5
    ws.cell(top - 1, 1, "Cohort retention: % of each first-purchase cohort that ordered again N months later").font = F_BOLD
    hdrs = ["Cohort", "New customers"] + [f"M{k}" for k in range(1, 13)]
    for j, h in enumerate(hdrs, 1):
        cc = ws.cell(top, j, h); cc.font, cc.fill, cc.alignment = F_H, FILL_H, Alignment(horizontal="center")
    for i, (cohort, row) in enumerate(piv.iterrows(), start=top + 1):
        ws.cell(i, 1, cohort).font = F_B
        ws.cell(i, 2, int(sizes[cohort])).number_format = FMT["int"]
        for k in range(1, 13):
            v = row[k]
            if pd.notna(v):
                cc = ws.cell(i, 2 + k, v / 100); cc.number_format = "0.00%"; cc.font = F_B
    last = top + len(piv)
    ws.cell(last + 1, 1, "Weighted avg").font = F_BOLD
    for k in range(1, 13):
        col = get_column_letter(2 + k)
        cc = ws.cell(last + 1, 2 + k,
                     f'=IFERROR(SUMPRODUCT($B${top+1}:$B${last},{col}{top+1}:{col}{last})'
                     f'/SUMIFS($B${top+1}:$B${last},{col}{top+1}:{col}{last},"<>"),"")')
        cc.number_format, cc.font = "0.00%", F_BOLD
    ws.conditional_formatting.add(f"C{top+1}:N{last}", ColorScaleRule(start_type="min", start_color="FFFFFF",
                                                                      end_type="max", end_color="EF4444"))
    for col in range(1, 15):
        ws.column_dimensions[get_column_letter(col)].width = 12 if col > 2 else 18

    # ------------------------------------------------------------------ RFM
    ws = wb.create_sheet("RFM_Segments")
    header(ws, "RFM customer segments", "Source: src/analysis.py (Recency & Monetary quintiles; any repeat purchase = loyalty signal)")
    seg = pd.read_csv(PROC / "rfm_segment_summary.csv")[[
        "segment", "customers", "revenue", "avg_spend", "avg_recency_days", "avg_orders", "avg_review", "recommended_action"]]
    seg = seg.rename(columns={"segment": "Segment", "customers": "Customers", "revenue": "Revenue (R$)",
                              "avg_spend": "Avg spend (R$)", "avg_recency_days": "Avg days since last order",
                              "avg_orders": "Avg orders", "avg_review": "Avg review",
                              "recommended_action": "Recommended action"})
    seg.insert(2, "Share of customers", None)
    seg.insert(4, "Share of revenue", None)
    g0, g1 = write_table(ws, seg, 4, 1, "tRFM",
                         {"Customers": "int", "Share of customers": "pct", "Revenue (R$)": "brl", "Share of revenue": "pct",
                          "Avg spend (R$)": "brl2", "Avg days since last order": "int", "Avg orders": "dec2",
                          "Avg review": "dec2"}, widths={"Recommended action": 55, "Segment": 24})
    for i in range(g0, g1 + 1):
        ws[f"C{i}"] = f"=B{i}/SUM($B${g0}:$B${g1})"
        ws[f"E{i}"] = f"=D{i}/SUM($D${g0}:$D${g1})"
        for col in "CE":
            ws[f"{col}{i}"].number_format, ws[f"{col}{i}"].font = FMT["pct"], F_B
    ws.conditional_formatting.add(f"E{g0}:E{g1}", DataBarRule(start_type="num", start_value=0, end_type="max", color="93C5FD"))

    # ------------------------------------------------------------------ Sellers
    ws = wb.create_sheet("Sellers")
    header(ws, "Seller scorecard", "Source: sql/04_products_sellers.sql > seller_scorecard. Filter the table by segment or state")
    sel = pct(r("seller_scorecard"), ["late_pct"]).rename(columns={
        "seller_id": "Seller ID", "seller_state": "State", "orders": "Orders", "revenue": "Revenue (R$)",
        "avg_review": "Avg review", "late_pct": "Late rate", "n_categories": "Categories",
        "seller_segment": "Segment", "revenue_decile": "Revenue decile"})
    sl0, sl1 = write_table(ws, sel, 4, 12, "tSellers",
                           {"Orders": "int", "Revenue (R$)": "brl", "Avg review": "dec2", "Late rate": "pct"},
                           widths={"Seller ID": 36, "Segment": 24})
    ws["A4"], ws["A4"].font = "Summary by segment (live COUNTIFS / SUMIFS over the table)", F_BOLD
    summ_hdr = ["Segment", "Sellers", "Revenue (R$)", "Share of revenue", "Avg review"]
    for j, h in enumerate(summ_hdr, 1):
        cc = ws.cell(5, j, h); cc.font, cc.fill = F_H, FILL_H
    segs = ["Star seller", "Core", "At risk - low rating", "At risk - late shipping", "Long tail"]
    for i, sg in enumerate(segs, start=6):
        ws.cell(i, 1, sg).font = F_B
        ws[f"B{i}"] = f'=COUNTIFS($S${sl0}:$S${sl1},A{i})'
        ws[f"C{i}"] = f'=SUMIFS($O${sl0}:$O${sl1},$S${sl0}:$S${sl1},A{i})'
        ws[f"D{i}"] = f'=C{i}/SUM($O${sl0}:$O${sl1})'
        ws[f"E{i}"] = f'=IFERROR(AVERAGEIFS($P${sl0}:$P${sl1},$S${sl0}:$S${sl1},A{i}),"")'
        for col, f in zip("BCDE", ["int", "brl", "pct", "dec2"]):
            ws[f"{col}{i}"].number_format, ws[f"{col}{i}"].font = FMT[f], F_B
    ws["A11"], ws["A11"].font = "Total", F_BOLD
    ws["B11"], ws["C11"], ws["D11"] = "=SUM(B6:B10)", "=SUM(C6:C10)", "=SUM(D6:D10)"
    for col, f in zip("BCD", ["int", "brl", "pct"]):
        ws[f"{col}11"].number_format, ws[f"{col}11"].font = FMT[f], F_BOLD
    conc = pct(r("seller_concentration"), ["pct_revenue"]).rename(
        columns={"seller_group": "Seller group", "pct_revenue": "Share of revenue"})
    write_table(ws, conc, 14, 1, "tSellerConc", {"Share of revenue": "pct"})
    for col, w in zip("ABCDE", [24, 10, 14, 16, 11]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"

    # ------------------------------------------------------------------ Payments
    ws = wb.create_sheet("Payments")
    header(ws, "Payment methods", "Source: sql/01_business_kpis.sql > payment_mix, installments_vs_ticket")
    pm = pct(r("payment_mix"), ["pct_value"]).rename(columns={
        "payment_type": "Payment type", "orders": "Orders", "value": "Value (R$)", "pct_value": "Share of value",
        "avg_installments": "Avg installments", "avg_payment": "Avg payment (R$)"})
    p0, p1 = write_table(ws, pm, 4, 1, "tPayments", {"Orders": "int", "Value (R$)": "brl", "Share of value": "pct",
                                                    "Avg installments": "dec2", "Avg payment (R$)": "brl2"})
    it = r("installments_vs_ticket").rename(columns={"installments_band": "Installments (credit card)",
                                                     "orders": "Orders", "avg_order_value": "Avg order value (R$)"})
    it["Installments (credit card)"] = it["Installments (credit card)"].astype(str)
    write_table(ws, it, p1 + 3, 1, "tInstallments", {"Orders": "int", "Avg order value (R$)": "brl2"},
                widths={"Installments (credit card)": 26})

    # ------------------------------------------------------------------ Data quality + notes
    ws = wb.create_sheet("Data_Quality")
    header(ws, "Data quality checks on the raw files", "Source: src/etl.py > outputs/data_quality_report.csv")
    write_table(ws, r("../data_quality_report"), 4, 1, "tDQ", {"rows": "int", "null_cells": "int"},
                widths={"cols_with_nulls": 60})
    notes = [
        "Cleaning decisions",
        "- reviews: 814 duplicate review_ids and orders with several reviews -> kept the latest answer per order.",
        "- payments: 3 rows with payment_type 'not_defined' removed.",
        "- products: 2 categories missing from the translation file were translated by hand; 610 products with no category -> 'unknown'.",
        "- geolocation: 1M rows (many duplicates) filtered to Brazil's bounding box and averaged to one point per zip prefix.",
        "- 'delivered' orders without a delivery date are not counted as delivered.",
        "- Revenue = item price + freight on orders not canceled/unavailable. Category revenue uses item price only.",
    ]
    for i, n in enumerate(notes, start=16):
        ws.cell(i, 1, n).font = F_BOLD if i == 16 else F_B

    # ------------------------------------------------------------------ Dashboard
    ws = dash
    ws.sheet_view.showGridLines = False
    ws["B1"], ws["B1"].font = "Olist E-commerce  |  Customer & Delivery Dashboard", F_TITLE
    ws["B2"] = "Brazilian marketplace, ~99k orders, Sep-2016 to Aug-2018. Every number below is a formula over the data tabs."
    ws["B2"].font = F_SUB
    ws.row_dimensions[1].height = 30
    for col in range(1, 26):
        ws.column_dimensions[get_column_letter(col)].width = 11
    ws.column_dimensions["A"].width = 2

    st = f"States!$D${s0}:$D${s1}"
    tiles = [
        ("Revenue (R$)", f"=SUM({st})", '"R$" #,##0.00,,"M"'),
        ("Orders", f"=SUM(States!$C${s0}:$C${s1})", FMT["int"]),
        ("Customers", f"=SUM(Retention!$B${rp0}:$B${rp1})", FMT["int"]),
        ("Avg order value", "=B5/E5", FMT["brl2"]),
        ("Avg review (1-5)", f"=SUMPRODUCT(Delivery_Reviews!$A${rs0}:$A${rs1},Delivery_Reviews!$B${rs0}:$B${rs1})"
                             f"/SUM(Delivery_Reviews!$B${rs0}:$B${rs1})", "0.00"),
        ("Late deliveries", f'=SUMIFS(Delivery_Reviews!$B${lv0}:$B${lv1},Delivery_Reviews!$A${lv0}:$A${lv1},"Late")'
                            f"/SUM(Delivery_Reviews!$B${lv0}:$B${lv1})", FMT["pct"]),
        ("Repeat customers", f"={repeat_cell}", FMT["pct"]),
        ("Review drop when late", f"={review_gap_cell}", '0.00" stars"'),
    ]
    for k, (label, formula, fmt) in enumerate(tiles):
        col = 2 + 3 * k
        ws.merge_cells(start_row=4, start_column=col, end_row=4, end_column=col + 2)
        ws.merge_cells(start_row=5, start_column=col, end_row=6, end_column=col + 2)
        lab, val = ws.cell(4, col, label), ws.cell(5, col, formula)
        lab.font, val.font, val.number_format = F_KPI_L, F_KPI, fmt
        lab.alignment = val.alignment = Alignment(horizontal="center", vertical="center")
        for rr in range(4, 7):
            for cc in range(col, col + 3):
                ws.cell(rr, cc).fill = FILL_TILE
    ws.row_dimensions[5].height = ws.row_dimensions[6].height = 18

    # --- interactive state lookup
    ws["B8"], ws["B8"].font = "State lookup  -  pick a state in the yellow cell:", F_BOLD
    ws["F8"] = "RJ"
    ws["F8"].fill, ws["F8"].font, ws["F8"].border = FILL_INPUT, F_BOLD, BOX
    ws["F8"].comment = Comment("Input cell: choose any Brazilian state code from the dropdown.", "Analyst")
    dv = DataValidation(type="list", formula1=f"=States!$A${s0}:$A${s1}", allow_blank=False)
    ws.add_data_validation(dv); dv.add("F8")
    look = [("Revenue", "D", '"R$" #,##0.00,,"M"'), ("Revenue rank", "L", "0"), ("AOV", "E", FMT["brl2"]),
            ("Delivery days", "H", "0.0"), ("Late rate", "I", FMT["pct"]), ("Avg review", "J", "0.00"),
            ("Freight % items", "G", FMT["pct"])]
    for k, (label, col, fmt) in enumerate(look):
        c_ = 8 + 2 * k
        ws.cell(8, c_ - 0, None)
        lab = ws.cell(7, c_, label); lab.font = F_KPI_L
        val = ws.cell(8, c_, f"=INDEX(States!${col}${s0}:${col}${s1},MATCH($F$8,States!$A${s0}:$A${s1},0))")
        val.font, val.number_format, val.border = F_BOLD, fmt, BOX
    ws["B9"] = "vs national: late rate"
    ws["B9"].font = F_KPI_L
    ws["F9"] = '=IF(P8>Q5,"worse than avg","better than avg")'
    ws["F9"].font = F_B

    # --- charts
    PALETTE = ["2563EB", "F59E0B", "1F2937"]

    def place(chart, anchor, w=16, h=7.5):
        chart.width, chart.height = w, h
        if not isinstance(chart, PieChart):
            chart.x_axis.delete = False          # newer Excel hides axes unless told otherwise
            chart.y_axis.delete = False
            chart.varyColors = False
            charts = [chart] + list(getattr(chart, "_charts", []))
            k = 0
            for sub in charts:
                for s in sub.series:
                    col = PALETTE[k % len(PALETTE)]
                    if isinstance(sub, LineChart):
                        s.graphicalProperties.line.solidFill = col
                        s.graphicalProperties.line.width = 28000
                        s.smooth = False
                    else:
                        s.graphicalProperties.solidFill = col
                        s.graphicalProperties.line.solidFill = col
                    k += 1
        if chart.title is not None:
            chart.title.overlay = False
        if chart.legend is not None:
            chart.legend.overlay = False
        if isinstance(chart, BarChart) and chart.type == "bar":
            chart.y_axis.crosses = "max"         # value axis at the bottom when categories run top-down
        if chart.dataLabels is not None:
            dl = chart.dataLabels
            dl.showSerName = dl.showCatName = dl.showLegendKey = False
            if isinstance(chart, PieChart):
                dl.showVal, dl.showPercent = False, True
        ws.add_chart(chart, anchor)

    ch = BarChart(); ch.type = "col"; ch.title = "Monthly revenue (R$)"; ch.style = 10
    msheet = wb["Monthly"]
    ch.add_data(Reference(msheet, min_col=4, min_row=m0 - 1, max_row=m1), titles_from_data=True)
    ch.set_categories(Reference(msheet, min_col=1, min_row=m0, max_row=m1))
    ln = LineChart()
    ln.add_data(Reference(msheet, min_col=9, min_row=m0 - 1, max_row=m1), titles_from_data=True)
    ch += ln
    ch.legend.position = "t"; ch.y_axis.numFmt = '#,##0,"k"'
    place(ch, "B11", 20)

    ch = BarChart(); ch.type = "col"; ch.title = "Avg review by delivery delay"; ch.style = 10
    dsheet = wb["Delivery_Reviews"]
    ch.add_data(Reference(dsheet, min_col=3, min_row=d0 - 1, max_row=d1), titles_from_data=True)
    ch.set_categories(Reference(dsheet, min_col=1, min_row=d0, max_row=d1))
    ch.y_axis.scaling.min, ch.y_axis.scaling.max = 0, 5
    ch.dataLabels = DataLabelList(); ch.dataLabels.showVal = True
    ch.legend = None
    place(ch, "N11", 18)

    ch = BarChart(); ch.type = "bar"; ch.title = "Top 10 categories by revenue (R$)"; ch.style = 10
    csheet = wb["Categories"]
    ch.add_data(Reference(csheet, min_col=4, min_row=c0 - 1, max_row=c0 + 9), titles_from_data=True)
    ch.set_categories(Reference(csheet, min_col=1, min_row=c0, max_row=c0 + 9))
    ch.x_axis.scaling.orientation = "maxMin"; ch.legend = None; ch.y_axis.numFmt = '#,##0,"k"'
    place(ch, "B27", 20, 8)

    ch = BarChart(); ch.type = "bar"; ch.title = "RFM segments: share of customers vs revenue"; ch.style = 10
    gsheet = wb["RFM_Segments"]
    for colnum in (3, 5):
        ch.add_data(Reference(gsheet, min_col=colnum, min_row=g0 - 1, max_row=g1), titles_from_data=True)
    ch.set_categories(Reference(gsheet, min_col=1, min_row=g0, max_row=g1))
    ch.x_axis.scaling.orientation = "maxMin"; ch.legend.position = "t"; ch.y_axis.numFmt = "0%"
    place(ch, "N27", 18, 8)

    ch = PieChart(); ch.title = "Payment value by method"
    psheet = wb["Payments"]
    ch.add_data(Reference(psheet, min_col=3, min_row=p0 - 1, max_row=p1), titles_from_data=True)
    ch.set_categories(Reference(psheet, min_col=1, min_row=p0, max_row=p1))
    ch.dataLabels = DataLabelList(); ch.dataLabels.showPercent = True
    place(ch, "B44", 12, 7.5)

    ch = LineChart(); ch.title = "Late-delivery rate by month"; ch.style = 12
    ch.add_data(Reference(msheet, min_col=6, min_row=m0 - 1, max_row=m1), titles_from_data=True)
    ch.set_categories(Reference(msheet, min_col=1, min_row=m0, max_row=m1))
    ch.y_axis.numFmt = "0%"; ch.legend = None
    place(ch, "J44", 14, 7.5)

    ch = BarChart(); ch.type = "col"; ch.title = "Late rate - top 10 states by revenue"; ch.style = 10
    ssheet = wb["States"]
    ch.add_data(Reference(ssheet, min_col=9, min_row=s0 - 1, max_row=s0 + 9), titles_from_data=True)
    ch.set_categories(Reference(ssheet, min_col=1, min_row=s0, max_row=s0 + 9))
    ch.y_axis.numFmt = "0%"; ch.legend = None
    place(ch, "R44", 14, 7.5)

    # key insights box
    ins = [
        "Key insights",
        "1. Delivery is the #1 driver of satisfaction: late orders score ~2 stars lower and most get 1-2 stars.",
        "2. ~97% of customers buy only once - retention, not acquisition, is the growth lever.",
        "3. Revenue grew ~140% Jan-Aug 2018 vs 2017; Nov-2017 (Black Friday) is the peak month.",
        "4. North/Northeast states wait 2-3x longer than SP, pay more freight, and rate lower.",
        "5. Top 10% of sellers carry ~2/3 of revenue; a handful of big sellers are 'at risk'.",
    ]
    for i, t in enumerate(ins, start=60):
        ws.cell(i, 2, t).font = F_BOLD if i == 60 else F_B
    ws.freeze_panes = "A4"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print("Saved", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
