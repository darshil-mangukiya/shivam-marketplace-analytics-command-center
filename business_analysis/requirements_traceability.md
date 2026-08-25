# Requirements Traceability

The canonical traceability artifact is [docs/requirements_traceability_matrix.csv](../docs/requirements_traceability_matrix.csv).

Each of its 25 rows links a requirement to:

```text
source system and field
  → transformation
  → business rule and KPI
  → analytical output
  → Streamlit, Power BI, or SQL implementation
  → acceptance criterion
  → automated test or UAT case
```

The CSV format is versionable and can be loaded directly by pandas, Excel, or Power BI. Status values distinguish implemented requirements from those also exercised through a runtime or UAT path.

Related artifacts:

- [Business Requirements Document](business_requirements_document.md)
- [Functional Requirements](functional_requirements.md)
- [Non-Functional Requirements](non_functional_requirements.md)
- [User Stories](user_stories.md)
- [Acceptance Criteria](../docs/acceptance_criteria.md)
