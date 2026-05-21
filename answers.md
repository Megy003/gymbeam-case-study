# GymBeam Case Study — Answers

## Task 1 — Historické zmeny (SCD)

Historické zmeny riešim pomocou SCD Type 2 v analytických dimenziách.
Každá zmena ceny produktu alebo adresy zákazníka vytvorí nový záznam
s atribútmi valid_from, valid_to a is_current. Faktová tabuľka
odkazuje vždy na product_key platný v čase transakcie — nie na
aktuálny stav — čím garantuje historickú konzistentnosť reportov.
Navyše unit_price je uložený ako snapshot priamo v order_items,
čo umožňuje audit ceny v čase nákupu bez závislosti na dimenzii.

---

## Task 2.1 — Postup doplnenia miest

### Použitá metóda
Implementovala som dvojstupňový geo enrichment pipeline:
1. pgeocode (offline batch lookup) — primárna metóda pre HU
2. Nominatim API (OpenStreetMap) — fallback pre SK a CZ

### Nájdené problémy v dátach
- PSČ boli uložené ako float (napr. 9437.0 namiesto 9437)
  → opravené odstránením .0 suffixu
- SK PSČ začínajúce číslicou 1-9 mali chýbajúcu leading nulu
  (napr. 1001 namiesto 01001) → opravené doplnením prefixu 0
- 6 objednávok malo null PSČ → označené ako neplatné
- pgeocode mal permission chybu v Keboola prostredí
  → vyriešené Nominatim API fallbackom

### Výsledok
- Celková geo coverage: 99.2% (29 755 z 30 000 objednávok)
- SK: 98.6%, CZ: 99.2%, HU: 99.9%
- 245 objednávok zostalo bez mesta (neplatné PSČ)

---

## Task 2.2 — Mesačná marža

Marža je vypočítaná ako:
margin_pct = (revenue_eur - cost_eur) / revenue_eur × 100

Ceny boli konvertované do EUR pomocou currency_rate z orders tabuľky.
Produkty s nulovou cenou (21% items) boli vyfiltrované z výpočtu —
pravdepodobne ide o bonusové alebo darčekové položky.

---

## Task 2.3 — Pricing stratégia

### Definícia metriky "dopad na tržby"

Revenue Impact Score = total_revenue_eur × margin_pct / 100

Táto metrika kombinuje objem tržieb s maržou. Produkt s vysokým
revenue ale nulovou maržou má nízky impact score, rovnako ako
produkt s vysokou maržou ale malým objemom. Zachytáva skutočný
príspevok produktu k zisku spoločnosti — nie len tržby.

### Identifikácia TOP 5 food produktov

Keďže dáta neobsahujú názvy produktov ani kategórie (len hash ID),
identifikovala som TOP 5 produktov podľa impact score a mapovala
ich na reálne GymBeam bestsellery podľa priemernej ceny za jednotku:

| # | Avg. cena EUR | Marža  | Mapovanie na produkt               |
|---|--------------|--------|------------------------------------|
| 1 | 16.46€       | 29.62% | Kreatin Monohydrate 500g           |
| 2 | 11.74€       | 44.22% | True Whey 1kg                      |
| 3 | 5.29€        | 47.61% | Crea7in                            |
| 4 | 4.20€        | 78.81% | Magnézium chelát bisglycinate      |
| 5 | 1.16€        | 57.26% | Kreatin Monohydrate sachet/30g     |

### Konkurenčná analýza

**Postup vyhľadávania:**
Pre každý produkt som vyhľadala ekvivalentný produkt u dvoch
konkurentov GymBeamu na SK/CZ trhu: MyProtein a BrainMarket.
Ceny som normalizovala na rovnakú gramáž pre spravodlivé porovnanie.
Kde neexistoval priamy ekvivalent, použila som najbližší
porovnateľný produkt (rovnaká forma, podobné zloženie).

**Výzvy pri vyhľadávaní:**
- Rôzne gramáže balení sťažujú priame porovnanie — nutná
  normalizácia ceny na 100g
- Konkurenti pravidelne menia akciové ceny — zaznamenaná
  bežná (neakciová) cena
- Crea7in je proprietárny blend GymBeamu — žiadny priamy
  ekvivalent u konkurencie, porovnané s podobným kreatin
  blendmi
- BrainMarket predáva vlastné private label produkty —
  zloženie podobné ale branding odlišný

**Zistené ceny konkurentov (máj 2025):**

Produkt (500g/1kg)           - GymBeam - MyProtein - BrainMarket 

Kreatin Monohydrate 500g     - 15.95€  - 10.99€    - 15.00€ 
True Whey 1kg                - 21.73€  - 23.00€    - 24.90€ 
Crea7in (~300g)              - 18.00€  - N/A*      - ~16.00€* 
Magnézium chelát             - 12.00€  - ~9.00€    - ~11.00€ 
Kreatin sachet 30g           - 1.20€   - ~0.90€    - ~1.10€ 

*ekvivalentný produkt

### Pricing logika

Pravidlá aplikované v tomto poradí:

**Pravidlo 1 — Ochrana marže (priorita)**
Ak margin_pct < 25% → zvýš cenu na úroveň kde margin = 25%,
maximálna zmena +12% za jeden cyklus

**Pravidlo 2 — Predraženie voči konkurencii**
Ak gymbeam_cena > priemer_konkurencia × 1.10 →
zníž na priemer_konkurencia × 1.05 (zostať 5% nad priemerom)

**Pravidlo 3 — Podhodnotenie voči konkurencii**
Ak gymbeam_cena < priemer_konkurencia × 0.90 →
zvýš o max 8% (využi price leadership pozíciu)

**Pravidlo 4 — Stabilná cena**
Inak → cenu nemeň (sme v zdravom pásme)

### Tabuľka odporúčaní

Produkt - Aktuálna cena - Avg. konkurencia - Odporúčaná cena - Zmena % - Marža pred - Marža po - Dopad/mes - Dôvod |

Kreatin Monohydrate 500g - 15.95€ - 12.97€ - 15.95€ - 0% - 29.62% - 29.62% - 0€ - Marža pod ideálom (29.6%) ale GymBeam je drahší ako MyProtein (10.99€). Odporúčam neznižovať cenu — konkurencia má pravdepodobne nižšie náklady pri väčšom objeme. Fokus na zníženie výrobných nákladov. 
True Whey 1kg - 21.73€ - 23.95€ - 23.46€ - +8.0% - 44.22% - 47.10% - +345€ - GymBeam je lacnejší ako obaja konkurenti. Priestor na zvýšenie ceny o 8% pri zachovaní price leadership. 
Crea7in - 18.00€ - 16.00€ - 18.00€ - 0% - 47.61% - 47.61% - 0€ - Proprietárny blend bez priameho ekvivalentu. Marža zdravá. Cenu nemeníme — riziko straty zákazníkov pri zdražení unikátneho produktu. 
Magnézium chelát - 12.00€ - 10.00€ - 12.00€ - 0% - 78.81% - 78.81% - 0€ - Sme 20% nad priemerom ale marža výborná (78.8%). Prémiová pozícia je ospravedlniteľná kvalitou bisglycinate formy vs lacnejšie formy u konkurencie. 
Kreatin sachet 30g - 1.20€ - 1.00€ - 1.20€ - 0% - 57.26% - 57.26% - 0€ - Marginálny rozdiel 0.20€ — zmena by nepriniesla merateľný dopad pri tomto objeme. Marža zdravá. 

### Škálovanie na celý food sortiment

Pre škálovanie pricing stratégie by som implementovala
automatizovaný týždenný pipeline: web scraping cien konkurentov
(MyProtein, BrainMarket, Aktin, NaMaximum) pomocou Python
a BeautifulSoup uložený do Keboola, kde SQL transformácia aplikuje
pricing pravidlá na celý sortiment automaticky. Frekvenciu by som
nastavila týždenne pre volatilné produkty (proteíny, kreatíny)
a mesačnej pre stabilné kategórie (vitamíny, minerály). Guardrails
zahŕňajú maximálnu zmenu ceny ±12% za jeden cyklus, povinné
manuálne schválenie pre top 50 produktov podľa tržieb a automatický
alert ak marža klesne pod 25%. Úzkym miestom je mapovanie
ekvivalentných produktov medzi konkurentmi — riešiteľné cez fuzzy
matching na názov a gramáž, prípadne ML product matching model.
Ďalším guardrailom by bola ochrana pred cenovými vojnami: ak
konkurent zníži cenu o viac ako 20%, systém triggeruje manuálnu
revíziu namiesto automatického nasledovania ceny.

---

## Task 3 — SQL Performance

Viď task3/post_mortem.md