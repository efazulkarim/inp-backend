"""
Application-wide constants. Avoid magic numbers and strings.
"""

# Report generation
REPORT_STATUS_QUEUED = "queued"
REPORT_STATUS_PROCESSING = "processing"
REPORT_STATUS_COMPLETED = "completed"
REPORT_STATUS_FAILED = "failed"

# Stale report threshold: reset processing -> queued if no update for this many seconds
REPORT_STALE_THRESHOLD_SECONDS = 300

# Billing period approximation (days) when period_start is not stored
BILLING_PERIOD_DAYS = 31
