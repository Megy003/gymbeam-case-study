# SQL Transformation Performance Post-Mortem

## Symptóm
Transformácia ktorá pôvodne trvala ~20 minút
dnes trvá 2h 44min (8x pomalšie za 5 dní).
Trend je lineárne rastúci — bez zásahu sa situácia zhorší.

## Root Cause Analysis (5 Whys)

**Prečo trvá transformácia dlhšie?**
Query planner volí Full Table Scan namiesto Index Scan.

**Prečo volí Full Table Scan?**
Štatistiky tabuľky sú zastarané, planner podceňuje
  skutočný počet riadkov.

**Prečo sú štatistiky zastarané?**
AUTOVACUUM nestíha pri raste dát.

**Prečo rastie objem dát takto rýchlo?**
Transformácia appenduje výsledky namiesto TRUNCATE + INSERT.
  Staging tabuľka narástla z 1M na 8M riadkov za 5 dní.

**Prečo appenduje namiesto replace?**
Chyba v konfigurácii — Output Mapping nastavený
  na "Append" namiesto "Replace".


## Najčastejšie príčiny spomalenia

### 1. Rast objemu dát
Transformácia pôvodne bežala na 1M riadkoch, teraz na 8M+.
Každý beh pridáva nové dáta bez čistenia starých.

**Riešenie:**
- Output Mapping → zmeniť na Replace
- Implementovať inkrementálne spracovanie:
  WHERE updated_at > last_run_timestamp

### 2. Chýbajúce indexy
Full Table Scan namiesto Index Scan na JOIN a WHERE stĺpcoch.

**Riešenie:**
```sql
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(created_at);
CREATE INDEX idx_items_order ON order_items(order_id);
```

### 3. Zastaralé štatistiky
Query planner robí zlé rozhodnutia na základe
neaktuálnych odhadov počtu riadkov.

**Riešenie:**
```sql
ANALYZE orders;
ANALYZE order_items;
```

### 4. Kartézsky súčin v JOINoch
Chybný JOIN bez správnej podmienky → počet riadkov exploduje.

**Riešenie:**
```sql
-- Zlé:
SELECT * FROM orders, order_items
WHERE orders.order_id = order_items.order_id;

-- Správne:
SELECT * FROM orders o
JOIN order_items i ON o.order_id = i.order_id;
```

### 5. Korelované subquery v SELECT
```sql
-- Zlé (N+1 queries):
SELECT o.*,
  (SELECT COUNT(*) FROM items WHERE order_id = o.order_id)
FROM orders o;

-- Správne (jeden JOIN):
SELECT o.*, i.item_count
FROM orders o
LEFT JOIN (
  SELECT order_id, COUNT(*) AS item_count
  FROM items GROUP BY 1
) i ON o.order_id = i.order_id;
```

### 6. Spill na disk pri Hash Join
Veľké intermediate výsledky sa nevmestia do pamäte.

**Riešenie:**
- Zvýšiť work_mem
- Rozbiť transformáciu na menšie kroky
- Použiť CTE pre intermediate výsledky

### 7. Nekontrolovaný rast staging tabuliek
Staging tabuľka rastie s každým behom transformácie.

**Riešenie:**
- TRUNCATE staging_table pred každým behom
- Partition pruning pre veľké tabuľky

## Ako identifikovať problém

```sql
-- Krok 1: Pozri execution plan
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT ... -- tvoja transformácia

-- Krok 2: Hľadaj varovné signály:
-- "Seq Scan" → potrebuješ index
-- "rows=1000 actual rows=8000000" → zastarané štatistiky
-- "Batches: 8" pri Hash Join → spill na disk
```
