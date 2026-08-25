-- Shivam Multi-Marketplace Analytics Command Center
-- Purpose: Public validation and privacy checks (PASS/WARN/FAIL) for dashboard trust.
-- Scope: Privacy-safe public analytics query (reads public/output tables only)
-- Note: Marketplace-channel join coverage is unavailable unless mapping keys are populated.

-- Public validation summary for dashboard trust checks.

select
    check_name,
    check_status,
    check_value,
    expected_value,
    notes
from validation_summary
order by
    case check_status
        when 'FAIL' then 1
        when 'WARN' then 2
        else 3
    end,
    check_name;

