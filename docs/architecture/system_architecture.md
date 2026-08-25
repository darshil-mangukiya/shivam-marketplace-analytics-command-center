# System Architecture

## Data flow

```mermaid
flowchart TD
    A[Product and cost master] --> C[Upload contracts]
    B[Marketplace transactions] --> C
    C --> D[Cleaning and normalization]
    D --> E[SKU reconciliation]
    E --> F[Privacy and anonymization]
    F --> G[Metrics, recommendations, and variance analysis]
    G --> H[17 public CSV outputs]
    H --> I[Streamlit: 9 pages]
    H --> J[Power BI Desktop: 8 pages]
    H --> K[Azure SQL Database]
    K --> L[Fabric Data Factory]
    L --> M[OneLake Lakehouse: Bronze]
    M --> N[PySpark: Silver and Gold Delta tables]
```

The Python path is the source of the public analytical layer. Streamlit and Power BI read that layer directly. Azure SQL reshapes the same outputs into a dimensional model. Fabric copies the 10 Azure SQL tables into OneLake and produces 10 Bronze, 10 Silver, and 5 Gold tables.

## Upload processing

```mermaid
flowchart LR
    U[Two uploaded files] --> V[YAML contract validation]
    V -->|accepted| C[Normalize and join]
    V -->|rejected| Q[Safe quarantine metadata]
    C --> P[Privacy scan]
    P --> O[Analytics and exports]
```

Uploaded files use temporary local storage for processing. Public frames pass column and full-content privacy scans before the application stores or exports them.

## Azure SQL model

```mermaid
erDiagram
    dim_product ||--o{ fact_product_performance : has
    dim_marketplace ||--o{ fact_product_performance : has
    dim_product ||--o{ fact_inventory_action : has
    dim_marketplace ||--o{ fact_inventory_action : has
    dim_month ||--o{ fact_marketplace_activity : has
    dim_marketplace ||--o{ fact_marketplace_activity : has
    dim_month ||--o{ fact_performance_variance : compares
    dim_marketplace ||--o{ fact_performance_variance : has
```

The warehouse uses deterministic surrogate keys and a reserved `Unknown` member in every dimension. Foreign keys and row-count reconciliation protect the load.

## Fabric medallion path

```mermaid
flowchart LR
    A[Azure SQL: 10 tables] --> B[Copy Job and Pipeline]
    B --> C[Bronze: 10 Delta tables]
    C --> D[PySpark notebook]
    D --> E[Silver: 10 Delta tables]
    E --> F[Gold: 5 Delta tables]
```

Fabric refreshes use full-table overwrite. Reconciliation, key checks, duplicate checks, Delta validation, retry, and recovery results are recorded in [Fabric runtime evidence](../evidence/fabric_runtime_evidence.md).
