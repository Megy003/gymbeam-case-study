# Architektonické rozhodnutia — Dátový model

## 1. Prečo dvojvrstvový model (OLTP + Star Schema)

OLTP vrstva je normalizovaná pre rýchle zápisy a integritu dát.
Pre analytiku je JOIN cez 6+ tabuliek pomalý a ťažko čitateľný
pre non-technical stakeholderov. Star Schema denormalizuje dimenzie
- jednoduchšie queries, rýchlejší BI nástroj.

## 2. Prečo SCD Type 2 pre produkty

Cena produktu sa mení. Ak reportujem tržby za Q1 2024 dnes vs. o rok,
chcem vidieť ROVNAKÉ čísla — teda cenu platnú v čase transakcie.
SCD Type 2 (valid_from / valid_to / is_current) to garantuje.
Používam oboje: unit_price snapshot v fact_sales + SCD v dim_product
pre audit histórie zmien cien.

## 3. Prečo samostatná tabuľka addresses

Zákazník môže mať viacero adries (fakturačná vs. doručovacia).
Normalizácia do samostatnej tabuľky umožňuje sledovať históriu
adries bez duplikácie zákazníckych dát.

## 4. Prečo dim_geography ako samostatná dimenzia

PSČ → mesto lookup je výpočtovo drahá operácia.
Raz vypočítaná geografia uložená v dimenzii = lookup raz,
JOIN vždy. Pri 30K objednávkach z ~500 unikátnych PSČ
je to 60x menej práce pre databázu.

## 5. Indexy

Pridané indexy na všetky JOIN a WHERE stĺpce —
orders(customer_id), orders(ordered_at), order_items(order_id),
fact_sales(date_id, product_key, geo_key).
Bez indexov by analytické queries pri rastúcom objeme
dát prechádzali na Full Table Scan.