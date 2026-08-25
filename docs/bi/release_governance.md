# Release Checks

Run the local validation gate before staging a release:

```bash
make validate
```

| Check | Pass condition |
|---|---|
| Python tests | 0 failures |
| Upload and output contracts | all 8 YAML files load; declared output contracts have no reject-level result |
| Privacy scan | `content_hit_count: 0`, `is_safe: true` |
| Public outputs | 17 readable CSV files |
| Workflow | 290 queue items build and invalid transitions are rejected |
| UAT | 33 scenarios show PASS |
| Defects | no unresolved High-severity entry |
| Documentation | links, images, and current counts resolve |

GitHub Actions repeats compilation, pytest, privacy, contract, and public-output checks on Python 3.11 and 3.13.
