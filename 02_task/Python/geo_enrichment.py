import os
os.environ['HOME'] = '/tmp'
os.makedirs('/tmp/.cache', exist_ok=True)

import pandas as pd
import pgeocode
import requests
import time

# NAČÍTANIE DÁT

orders = pd.read_csv('/data/in/tables/sales_order.csv')
items  = pd.read_csv('/data/in/tables/sales_order_item.csv')

print(f"Orders: {len(orders)} riadkov")
print(f"Items:  {len(items)} riadkov")
print(f"Krajiny: {orders['country_code'].value_counts().to_dict()}")

# ČISTENIE ORDERS

dup_orders = orders.duplicated(subset='pk_sales_order').sum()
orders.drop_duplicates(subset='pk_sales_order', inplace=True)
print(f"Duplikáty v orders: {dup_orders}")

orders['postal_code_clean'] = (
    orders['postal_code']
    .fillna('')
    .astype(str)
    .str.replace(r'\.0$', '', regex=True)
    .str.strip()
    .str.replace(' ', '')
    .str.replace('-', '')
)
orders['postal_code_valid'] = orders['postal_code_clean'].str.match(r'^\d{3,5}$')
print(f"Neplatných PSČ: {(~orders['postal_code_valid']).sum()}")

# ČISTENIE ITEMS

dup_items = items.duplicated(subset='pk_sales_order_item').sum()
items.drop_duplicates(subset='pk_sales_order_item', inplace=True)
null_items = items['fk_item'].isnull().sum()
items = items[items['fk_item'].notna()].copy()
print(f"Duplikáty v items: {dup_items}, Null fk_item: {null_items}")

# KONVERZIA CIEN DO EUR

items = items.merge(
    orders[['pk_sales_order', 'currency_rate', 'currency', 'created_at']],
    left_on='fk_sales_order',
    right_on='pk_sales_order',
    how='left'
)

items['product_price_local_currency'] = pd.to_numeric(items['product_price_local_currency'], errors='coerce').fillna(0)
items['product_cost_eur']             = pd.to_numeric(items['product_cost_eur'], errors='coerce').fillna(0)
items['currency_rate']                = pd.to_numeric(items['currency_rate'], errors='coerce').fillna(1)
items['sold_qty']                     = pd.to_numeric(items['sold_qty'], errors='coerce').fillna(0)

items['price_eur']   = (items['product_price_local_currency'] * items['currency_rate']).round(4)
items['revenue_eur'] = (items['price_eur'] * items['sold_qty']).round(4)
items['cost_eur']    = (items['product_cost_eur'] * items['sold_qty']).round(4)
items['margin_eur']  = (items['revenue_eur'] - items['cost_eur']).round(4)
items['margin_pct']  = (
    items['margin_eur'] / items['revenue_eur'].replace(0, float('nan')) * 100
).round(2)

items['created_at'] = pd.to_datetime(items['created_at'])
items['month']      = items['created_at'].dt.to_period('M').astype(str)

# PSČ FIX FUNKCIA

def fix_psc(psc, cc):
    psc = str(psc).replace('.0','').strip()
    if cc == 'SK' and len(psc) == 4:
        psc = '0' + psc
    return psc

# GEO ENRICHMENT

valid_orders  = orders[orders['postal_code_valid']].copy()
valid_orders['psc_fixed'] = valid_orders.apply(
    lambda r: fix_psc(r['postal_code_clean'], r['country_code']), axis=1
)

unique_combos = (
    valid_orders[['postal_code_clean', 'psc_fixed', 'country_code']]
    .drop_duplicates()
    .reset_index(drop=True)
)
print(f"\nUnikátnych PSČ kombinácií: {len(unique_combos)}")

# Funkcia Nominatim
def nominatim_lookup(psc, country):
    try:
        url = 'https://nominatim.openstreetmap.org/search'
        params = {
            'postalcode': psc,
            'country': country,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {'User-Agent': 'gymbeam-case-study/1.0'}
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        data = resp.json()
        if data:
            addr = data[0].get('address', {})
            city = (addr.get('city') or addr.get('town') or
                   addr.get('village') or addr.get('municipality') or
                   data[0]['display_name'].split(',')[0].strip())
            region = addr.get('state', '')
            return city, region, float(data[0]['lat']), float(data[0]['lon']), 'nominatim'
    except Exception:
        pass
    return None, None, None, None, 'not_found'

results = []
nominatim_count = 0

for cc, group in unique_combos.groupby('country_code'):
    print(f"Lookup pre {cc}: {len(group)} PSČ")

    if cc == 'HU':
        nomi     = pgeocode.Nominatim('hu')
        psc_list = group['psc_fixed'].tolist()
        batch    = nomi.query_postal_code(psc_list)

        for i, (_, row) in enumerate(group.iterrows()):
            found = pd.notna(batch.iloc[i]['place_name'])
            if found:
                results.append({
                    'postal_code_clean': row['postal_code_clean'],
                    'country_code': cc,
                    'city':      batch.iloc[i]['place_name'],
                    'region':    batch.iloc[i]['state_name'],
                    'latitude':  float(batch.iloc[i]['latitude']),
                    'longitude': float(batch.iloc[i]['longitude']),
                    'source':    'pgeocode'
                })
            else:
                # Fallback na Nominatim
                time.sleep(1)
                city, region, lat, lon, src = nominatim_lookup(row['psc_fixed'], cc)
                nominatim_count += 1
                results.append({
                    'postal_code_clean': row['postal_code_clean'],
                    'country_code': cc,
                    'city': city, 'region': region,
                    'latitude': lat, 'longitude': lon,
                    'source': src
                })
    else:
        for _, row in group.iterrows():
            time.sleep(1)
            city, region, lat, lon, src = nominatim_lookup(row['psc_fixed'], cc)
            nominatim_count += 1
            results.append({
                'postal_code_clean': row['postal_code_clean'],
                'country_code': cc,
                'city': city, 'region': region,
                'latitude': lat, 'longitude': lon,
                'source': src
            })
            if nominatim_count % 100 == 0:
                print(f"  Nominatim: {nominatim_count} volaní")

geo_df = pd.DataFrame(results)
orders = orders.merge(geo_df, on=['postal_code_clean', 'country_code'], how='left')

# QUALITY REPORT

total     = len(orders)
found     = orders['city'].notna().sum()
not_found = orders['city'].isna().sum()

print(f"\n=== GEO LOOKUP REPORT ===")
print(f"Celkom objednávok:    {total}")
print(f"Mesto nájdené:        {found} ({found/total*100:.1f}%)")
print(f"Mesto nenájdené:      {not_found} ({not_found/total*100:.1f}%)")
print(f"Zdroj: {geo_df['source'].value_counts().to_dict()}")
print(f"\nTop 10 miest:")
print(orders['city'].value_counts().head(10))

# AOV PER MESTO — úloha 2.1

order_revenue = (
    items[items['price_eur'] > 0]
    .groupby('fk_sales_order')['revenue_eur']
    .sum()
    .reset_index()
)
orders_with_rev = orders.merge(
    order_revenue,
    left_on='pk_sales_order',
    right_on='fk_sales_order',
    how='left'
)
aov_by_city = (
    orders_with_rev[orders_with_rev['city'].notna()]
    .groupby(['city', 'region', 'country_code', 'latitude', 'longitude'])
    .agg(
        order_count=('pk_sales_order', 'nunique'),
        total_revenue=('revenue_eur', 'sum')
    )
    .reset_index()
)
aov_by_city['aov']           = (aov_by_city['total_revenue'] / aov_by_city['order_count']).round(2)
aov_by_city['total_revenue'] = aov_by_city['total_revenue'].round(2)
aov_by_city = aov_by_city.sort_values('aov', ascending=False)

print(f"\nTop 5 miest podľa AOV:")
print(aov_by_city[['city', 'country_code', 'order_count', 'aov']].head(5).to_string())

# MESAČNÁ MARŽA PER PRODUKT — úloha 2.2

monthly_margin = (
    items[items['price_eur'] > 0]
    .groupby(['fk_item', 'month'])
    .agg(
        total_revenue_eur=('revenue_eur', 'sum'),
        total_cost_eur=('cost_eur', 'sum'),
        total_qty=('sold_qty', 'sum'),
        order_count=('fk_sales_order', 'nunique')
    )
    .reset_index()
)
monthly_margin['margin_eur'] = (
    monthly_margin['total_revenue_eur'] - monthly_margin['total_cost_eur']
).round(4)
monthly_margin['margin_pct'] = (
    monthly_margin['margin_eur'] / monthly_margin['total_revenue_eur'] * 100
).round(2)

print(f"\nMesačná marža: {len(monthly_margin)} riadkov")

# TOP PRODUKTY — úloha 2.3

top_products = (
    items
    .groupby('fk_item')
    .agg(
        total_revenue_eur=('revenue_eur', 'sum'),
        total_cost_eur=('cost_eur', 'sum'),
        total_qty=('sold_qty', 'sum'),
        order_count=('fk_sales_order', 'nunique')
    )
    .reset_index()
)

top_products = top_products[top_products['order_count'] >= 100].copy()

top_products['margin_pct'] = (
    (top_products['total_revenue_eur'] - top_products['total_cost_eur'])
    / top_products['total_revenue_eur'].replace(0, float('nan')) * 100
).round(2)
top_products['impact_score'] = (
    top_products['total_revenue_eur'] * top_products['margin_pct'] / 100
).round(2)
top_products = top_products[top_products['impact_score'] > 0]
top_products = top_products.sort_values('impact_score', ascending=False)

print(f"\nTop 5 produktov:")
print(top_products[['fk_item', 'total_revenue_eur', 'margin_pct', 'order_count', 'impact_score']].head(5).to_string())

# EXPORT

orders.to_csv('/data/out/tables/orders_enriched.csv', index=False)
items.to_csv('/data/out/tables/items_clean.csv', index=False)
geo_df.to_csv('/data/out/tables/geo_lookup_cache.csv', index=False)
monthly_margin.to_csv('/data/out/tables/monthly_margin.csv', index=False)
aov_by_city.to_csv('/data/out/tables/aov_by_city.csv', index=False)
top_products.to_csv('/data/out/tables/top_products.csv', index=False)

print("\n✓ Všetky výstupy exportované!")