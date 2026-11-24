# Architektura rozwiązania

```mermaid
flowchart TB
    subgraph Źródła["Źródła danych (demo: generate_data.py)"]
        S1[Sklep WWW<br/>Shopify / WooCommerce]
        S2[Allegro<br/>REST API]
        S3[Amazon.pl<br/>SP-API]
        S4[Meta / Google /<br/>Allegro / Amazon Ads]
    end

    subgraph Raw["data/raw"]
        R1[orders_raw.csv]
        R2[marketing_spend.csv]
        R3[products.csv<br/>katalog + koszty zakupu]
    end

    S1 & S2 & S3 --> R1
    S4 --> R2

    R1 & R2 & R3 --> C["clean_data.py<br/>deduplikacja · testy · daty · kanały<br/>przecinki dziesiętne · marża · nowy/powracający"]
    C --> P1[orders_clean.csv]
    C --> P2[marketing_clean.csv]
    C --> DQ[data_quality_report.md]

    P1 & P2 --> K["kpis.py<br/>definicje KPI + reguły alertów"]
    K --> D["build_dashboard.py<br/>→ dashboard/index.html<br/>(interaktywny, offline)"]
    K --> RP["build_report.py<br/>→ PDF · e-mail HTML · summary.json"]
    RP --> N["notify.py<br/>→ webhook Make"]
    N --> M["Make: Gmail · Slack ·<br/>Google Sheets · Trello"]

    GH["GitHub Actions<br/>co poniedziałek 7:00"] -.uruchamia.-> C
    D -.publikacja.-> GP[GitHub Pages]
```

## Decyzje projektowe

| Decyzja | Uzasadnienie |
|---|---|
| **Python do obliczeń, Make do komunikacji** | Logika KPI jest wersjonowana i testowalna w kodzie. Odbiorcy, kanały i treści wiadomości zmienia się w Make bez programisty. |
| **Jeden moduł KPI** (`kpis.py`) | Jedna definicja „przychodu” czy „marży” w całej firmie – koniec dyskusji, czyja tabelka ma rację. |
| **Dashboard jako jeden plik HTML bez bibliotek** | Działa offline, otwiera się w każdej przeglądarce, hosting za 0 zł (GitHub Pages), brak licencji BI. Przy większej skali ten sam `orders_clean.csv` można podpiąć do Looker Studio lub Power BI. |
| **Wykresy w SVG pisane od zera** | Pełna kontrola nad czytelnością: jedna oś Y, etykiety bezpośrednie przy liniach, paleta sprawdzona pod kątem daltonizmu, tryb ciemny, tooltipy. |
| **Raport PDF z HTML przez Chrome headless** | Ten sam szablon do podglądu w przeglądarce i do druku; polskie znaki i fonty bez problemów. |
| **Raport jakości danych przy każdym uruchomieniu** | Widać, ile wierszy poprawiono i dlaczego – zaufanie do liczb. |
| **Progi alertów w konfiguracji** | Biznes ustala, co jest „problemem”, bez zmian w kodzie. |
