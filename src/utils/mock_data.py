SAMPLE_LEGAL_TEXT = """LEGAL SERVICES AGREEMENT

This Legal Services Agreement ("Agreement") is entered into as of [Date],
by and between [Client Name] ("Client") and [Law Firm Name] ("Firm").

1. SCOPE OF SERVICES
The Firm agrees to provide legal services to the Client as requested from
time to time and agreed upon by both parties.

2. FEES AND PAYMENT
Client agrees to pay Firm at the hourly rates agreed upon, with invoices
submitted monthly.

3. TERM AND TERMINATION
This Agreement shall continue until terminated by either party with 30 days
written notice.
"""


def sample_request() -> dict:
    return {
        "source_language": "en",
        "target_language": "es",
        "document_type": "legal",
        "page_count": 3,
        "raw_text": SAMPLE_LEGAL_TEXT,
        "max_retries": 1,
        "parallel_execution": True,
    }
