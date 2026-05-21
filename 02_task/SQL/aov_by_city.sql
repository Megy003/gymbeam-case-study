SELECT
    o.city,
    o.region,
    o.country_code,
    o.latitude,
    o.longitude,
    COUNT(DISTINCT o.pk_sales_order)                    AS order_count,
    ROUND(SUM(i.revenue_eur), 2)                        AS total_revenue,
    ROUND(SUM(i.revenue_eur) / COUNT(DISTINCT o.pk_sales_order), 2) AS aov
FROM orders_enriched o
JOIN items_clean i ON o.pk_sales_order = i.fk_sales_order
WHERE o.city IS NOT NULL
  AND i.price_eur > 0
GROUP BY o.city, o.region, o.country_code, o.latitude, o.longitude
ORDER BY aov DESC;