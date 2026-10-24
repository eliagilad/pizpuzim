import time

from googleapiclient.errors import HttpError

RETRYABLE = {429, 500, 502, 503}


class GoogleApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def execute(request, attempts: int = 4):
    status = None
    for attempt in range(attempts):
        try:
            return request.execute()
        except HttpError as exc:
            status = int(exc.resp.status)
            if status not in RETRYABLE or attempt == attempts - 1:
                raise GoogleApiError(f"Google API error {status}", status=status) from exc
            time.sleep(2**attempt)
    raise GoogleApiError(f"Google API error {status}", status=status)
