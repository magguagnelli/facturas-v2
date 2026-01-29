import os
import psycopg2

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
