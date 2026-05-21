-- Produkty kde marža klesá 3 mesiace po sebe
WITH monthly AS (
    SELECT
        fk_item,
        month,
        ROUND(
            (SUM(revenue_eur) - SUM(cost_eur))
            / NULLIF(SUM(revenue_eur), 0) * 100, 2
        ) AS margin_pct,
        LAG(ROUND(
            (SUM(revenue_eur) - SUM(cost_eur))
            / NULLIF(SUM(revenue_eur), 0) * 100, 2
        ), 1) OVER (PARTITION BY fk_item ORDER BY month) AS prev_margin
    FROM items_clean
    WHERE price_eur > 0
    GROUP BY fk_item, month
),
declining AS (
    SELECT fk_item, COUNT(*) AS months_declining
    FROM monthly
    WHERE margin_pct < prev_margin
    GROUP BY fk_item
)
SELECT * FROM declining
WHERE months_declining >= 3
ORDER BY months_declining DESC;