SELECT
    i.fk_item,
    i.month,
    ROUND(SUM(i.revenue_eur), 4)                        AS total_revenue_eur,
    ROUND(SUM(i.cost_eur), 4)                           AS total_cost_eur,
    ROUND(SUM(i.revenue_eur) - SUM(i.cost_eur), 4)     AS margin_eur,
    ROUND(
        (SUM(i.revenue_eur) - SUM(i.cost_eur))
        / NULLIF(SUM(i.revenue_eur), 0) * 100, 2
    )                                                   AS margin_pct
FROM items_clean i
WHERE i.price_eur > 0
GROUP BY i.fk_item, i.month
ORDER BY i.fk_item, i.month;