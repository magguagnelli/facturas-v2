import os
import psycopg2
import uvicorn
from app import app  # tu instancia FastAPI

if __name__ == "__main__":
    port = int(os.environ["DATABRICKS_APP_PORT"])
    uvicorn.run(app, host="0.0.0.0", port=port)

conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    port=int(os.environ.get("DB_PORT", "5432")),
    connect_timeout=5,
)
cur = conn.cursor()
cur.execute("SELECT 1;")
print("DB OK ✅", cur.fetchone())
cur.close()
conn.close()
