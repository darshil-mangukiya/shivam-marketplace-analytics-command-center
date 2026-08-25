from pipeline_utils import validate_outputs


if __name__ == "__main__":
    summary = validate_outputs()
    failures = summary[summary["check_status"] != "PASS"]
    print(summary.to_string(index=False))
    if not failures.empty:
        raise SystemExit(1)
