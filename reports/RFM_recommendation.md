# Customer segments and churn risk: recommendation

Based on 94,983 Olist customers and R$ 15.74M of revenue (valid orders, Sep 2016 - Sep 2018). The segmentation is in [`sql/05_rfm_segmentation.sql`](../sql/05_rfm_segmentation.sql).

## Summary

Most of Olist's revenue comes from customers who bought once, spent well, and haven't been back. The "At Risk" segment is 22% of customers but 40% of revenue. "Potential Loyalists", who are recent high spenders, add another 28%. That means 38% of customers bring in 68% of revenue.

On churn: 79% of customers have only one order and nothing in the last 90 days, so that rule alone flags almost everyone. Ranking the flagged customers by how much they spent narrows it to 29,006 high-value customers (30.5% of the base) who account for R$ 8.73M, or 55% of all revenue. That's the list I'd start with.

## Segments

| Segment | Customers | % of customers | % of revenue | Avg spend | Days since last order |
|---|---:|---:|---:|---:|---:|
| At Risk | 21,092 | 22.2% | 40.2% | R$ 300 | 342 |
| Potential Loyalists | 14,604 | 15.4% | 28.1% | R$ 303 | 97 |
| Lost | 22,912 | 24.1% | 10.6% | R$ 73 | 402 |
| New Customers | 22,156 | 23.3% | 10.3% | R$ 73 | 96 |
| About to Sleep | 11,332 | 11.9% | 5.2% | R$ 72 | 226 |
| Loyal | 1,653 | 1.7% | 3.1% | R$ 299 | 327 |
| Champions | 1,234 | 1.3% | 2.5% | R$ 321 | 94 |

A few things stand out:
- Repeat buyers (Champions + Loyal) are only 3.0% of customers and 5.6% of revenue. Almost all revenue depends on first purchases.
- At Risk customers spent about 4x more than Lost ones (R$ 300 vs R$ 73), but they also rated Olist lower (3.99 vs 4.16). Elsewhere in this project, late delivery turned out to be the main cause of low ratings, so some of this churn is probably delivery-related.
- 60% of At Risk revenue is in three states: SP (R$ 2.11M), RJ (R$ 0.92M) and MG (R$ 0.75M). RJ's At Risk customers have the lowest rating of the large states, at 3.73.
- Potential Loyalists last ordered 97 days ago on average, so there's still time to get a second order from them.

## What I'd do

1. **Win back At Risk customers.** Send a personalised offer based on their last category, with a short "what went wrong?" survey. Start with RJ and with customers whose last order arrived late. If 5% came back and spent their usual R$ 300, that's about R$ 316k.
2. **Push for a second order.** Potential Loyalists and New Customers (36,760 people) should get a coupon 1-4 weeks after delivery, plus reminders in their category. If 10% placed one more average order (R$ 160), that's about R$ 588k.
3. **Use the ranked churn list, not the raw flag.** Spend on the 29,006 high-value flagged customers first, and keep the other 46,016 on low-cost email.
4. **Look after the few repeat customers.** The 2,887 Champions and Loyal customers should get perks like early access, referral rewards and free shipping.
5. **Fix delivery.** Late orders average 2.3 stars vs 4.3 on time. Every late order makes a future At Risk customer more likely.

The revenue figures in 1 and 2 assume 5% and 10% response rates. They're there to show scale, not as forecasts, and should be tested with a small A/B campaign first.

## How the segments were built

- **One row per customer.** I used `customer_unique_id`, because Olist creates a new `customer_id` for every order. Canceled and unavailable orders and orders without items are excluded.
- **Recency** is days since the last order, measured from 2018-09-04, the day after the last valid order. Scores are quintiles, with cut-offs at 99 / 183 / 274 / 389 days.
- **Monetary** is total spend. Scores are quintiles, with cut-offs at R$ 55 / 88 / 133 / 209.
- **Frequency** is 1, 2 or 3+ orders. Quintiles don't work here because 97% of customers bought once.
- **Segment rules:**
  - Champions: 2+ orders and recent (R 4-5). Loyal: 2+ orders, not recent.
  - Potential Loyalists: recent and high spend (M 4-5). New Customers: recent, lower spend.
  - At Risk: not recent, high spend.
  - About to Sleep: R 3 and lower spend. Lost: R 1-2 and lower spend.

The data ends in 2018, so everyone's recency looks long in absolute terms. What matters is how customers rank against each other.
