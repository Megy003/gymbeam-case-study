# gymbeam-case-study

# GymBeam — Data Automation Specialist Case Study

## O projekte
Case study pre pozíciu Data Automation Specialist.
Riešenie pokrýva dátové modelovanie, ETL pipeline,
geo enrichment, analytiku a pricing stratégiu.

## Štruktúra repozitára
gymbeam-case-study/
├── 01_task/
│   ├── er_diagram.png     # ER diagram — OLTP + Star Schema
│   ├── schema.sql         # SQL schéma tabuliek
│   └── DECISIONS.md       # Zdôvodnenie architektonických rozhodnutí
├── 02_task/
│   ├── python/            # Geo enrichment + pricing engine
│   └── sql/               # Analytické transformácie
├── 03_task/
│   └── post_mortem.md     # SQL performance analýza
└── answers.md             # Slovné odpovede na otázky

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
