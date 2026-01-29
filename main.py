import os

REQUIRED = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]

status = {k: (k in os.environ and bool(os.environ.get(k))) for k in REQUIRED}
print("ENV presence:", status)

