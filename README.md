# gymbeam-case-study

# GymBeam — Data Automation Specialist Case Study

## O projekte
Case study pre pozíciu Data Automation Specialist.

## Kľúčové rozhodnutia
- **Geo enrichment:** pgeocode (primárne) + Nominatim API (fallback)
  → pokrytie globálnych PSČ bez vendor lock-in
- **Pricing engine:** pravidlový systém s guardrailmi
  → okamžite použiteľný nástroj, nie len analýza
- **Marža:** trend alert na klesajúce produkty
  → proaktívny monitoring, nie len reporting

## Nástroje
- **ETL:** Keboola
- **Transformácie:** Python + SQL
- **Vizualizácie:** Looker Studio
- **Dátový model:** dbdiagram.io

## Čo by som robila ďalej
- Automatický web scraping konkurenčných cien (týždenný pipeline)
- dbt pre transformačnú vrstvu namiesto čistého SQL
- ML model na demand forecasting pre pricing optimalizáciu
