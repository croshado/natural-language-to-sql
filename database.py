from google.generativeai import configure, embed_content
import psycopg2

configure(api_key="your api key")

conn = psycopg2.connect("dbname=vector_db user=postgres password=mysecretpassword")
cur = conn.cursor()

cur.execute("SELECT id, name FROM products;")
products = cur.fetchall()

for product_id, name in products:
    embedding = embed_content(model="models/embedding-001", content=name)["embedding"]
    cur.execute("UPDATE products SET embedding = %s WHERE id = %s;", (embedding, product_id))

conn.commit()
cur.close()
conn.close()
