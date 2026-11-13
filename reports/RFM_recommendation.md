# Recommendation: protect the At Risk revenue and convert first-time buyers

**To:** Head of CRM / Marketing, Olist · **Data:** 94,983 customers, R$ 15.74M revenue, valid orders Sep 2016 to Sep 2018 · **Method:** [`sql/05_rfm_segmentation.sql`](../sql/05_rfm_segmentation.sql)

## The answer

**Which segments generate the most revenue?** Two segments of one-time, high-spending customers. **At Risk** customers (22% of customers) hold **40% of revenue**, and **Potential Loyalists** (15%) hold **28%**. Together, 38% of customers account for **68% of revenue**.

**Which are at risk of churning?** **79% of customers (77% of revenue)** match the churn flag: one order and no purchase in over 90 days. The flag is too broad to act on by itself, so we rank it by value. **29,006 high-value flagged customers (30.5% of customers) hold R$ 8.73M, or 55% of all revenue.** They are the priority list.

## Key findings

| Segment | Customers | Share of customers | Share of revenue | Avg spend | Days since last order |
|---|---:|---:|---:|---:|---:|
| At Risk | 21,092 | 22.2% | **40.2%** | R$ 300 | 342 |
| Potential Loyalists | 14,604 | 15.4% | **28.1%** | R$ 303 | 97 |
| Lost | 22,912 | 24.1% | 10.6% | R$ 73 | 402 |
| New Customers | 22,156 | 23.3% | 10.3% | R$ 73 | 96 |
| About to Sleep | 11,332 | 11.9% | 5.2% | R$ 72 | 226 |
| Loyal | 1,653 | 1.7% | 3.1% | R$ 299 | 327 |
| Champions | 1,234 | 1.3% | 2.5% | R$ 321 | 94 |

1. **Repeat buyers barely exist.** Champions and Loyal together are 3.0% of customers and 5.6% of revenue. Olist's revenue rests on one-time purchases, so its growth depends on getting a second order.
2. **At Risk customers spend 4x more than Lost ones** (R$ 300 vs R$ 73) and rate Olist lower (3.99 vs 4.16 stars). Earlier analysis shows late deliveries are the main driver of low reviews.
3. **At Risk revenue is concentrated geographically.** SP (R$ 2.11M), RJ (R$ 0.92M) and MG (R$ 0.75M) hold 60% of it. In RJ, At Risk customers rate just **3.73**, the lowest among the top states.
4. **Potential Loyalists are recent** (97 days on average) and high-value, so the second-order window for them is open now.

## Recommendations

| # | Action | Target | Illustrative size of the prize |
|---|---|---|---|
| 1 | **Win-back campaign** for At Risk: a personalised offer in the customer's last category, plus a "what went wrong?" survey. Start with RJ and orders that were delivered late. | 21,092 customers | Winning back 5% at their average spend ≈ **R$ 316k** |
| 2 | **Second-order programme** for Potential Loyalists and New Customers: a coupon 7-30 days after delivery and category reminders. | 36,760 customers | 10% making one more average order (R$ 160) ≈ **R$ 588k** |
| 3 | **Use the value-ranked churn list**, not the raw flag: contact the 29,006 high-value flagged customers first, and send low-cost email only to the 46,016 low-value ones. | 75,022 flagged | Focuses spend on 55% of revenue |
| 4 | **VIP treatment** for Champions and Loyal: early access, referral rewards, free shipping. | 2,887 customers | Protects the only proven repeat base |
| 5 | **Fix the cause:** delivery reliability. Late orders average 2.3 stars vs 4.3 on time. | All | Prevents new At Risk customers |

The sizes in the last column are scenarios built on assumed response rates (5% and 10%), not forecasts. They should be validated with an A/B test before any budget is committed.

## How the segments were built
- **One row per customer:** `customer_unique_id`, because Olist issues a new `customer_id` for every order. Canceled and unavailable orders, and orders with no items, are excluded.
- **Recency** is measured from 2018-09-04, the day after the last valid order. Quintile cut-offs: 99 / 183 / 274 / 389 days.
- **Monetary** is total spend. Quintile cut-offs: R$ 55 / 88 / 133 / 209.
- **Frequency** uses business logic (1 / 2 / 3+ orders), because 97% of customers bought once.
- **Labels:**
  - Champions = 2+ orders and R 4-5; Loyal = 2+ orders and R 1-3.
  - Potential Loyalists = R 4-5 and M 4-5; New Customers = R 4-5 and M 1-3.
  - At Risk = R 1-3 and M 4-5.
  - About to Sleep = R 3 and M 1-3; Lost = R 1-2 and M 1-3.
- **Caveat:** the data ends in 2018, so absolute recency is long for everyone. The ranking between customers is what matters.
