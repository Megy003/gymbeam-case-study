SELECT
    fk_item,
    ROUND(SUM(revenue_eur), 2)                          AS total_revenue_eur,
    ROUND(SUM(cost_eur), 2)                             AS total_cost_eur,
    COUNT(DISTINCT fk_sales_order)                      AS order_count,
    ROUND(
        (SUM(revenue_eur) - SUM(cost_eur))
        / NULLIF(SUM(revenue_eur), 0) * 100, 2
    )                                                   AS margin_pct,
    ROUND(
        SUM(revenue_eur) *
        ((SUM(revenue_eur) - SUM(cost_eur))
        / NULLIF(SUM(revenue_eur), 0)), 2
    )                                                   AS impact_score
FROM items_clean
GROUP BY fk_item
HAVING COUNT(DISTINCT fk_sales_order) >= 100
ORDER BY impact_score DESC
LIMIT 5;