# Natural Language Search for PostgreSQL with Vector Embeddings

## Overview
This project implements a **natural language search interface** for querying a PostgreSQL database using **Google Generative AI** for embedding generation and **pgvector** for vector search. The UI is built with **Streamlit**, and the queries are processed using an **LLM-powered SQL generator**.

## Features
- Converts **natural language** queries into SQL
- Performs **vector similarity search** for product and order recommendations
- Uses **Google Generative AI** to generate embeddings
- Stores and retrieves embeddings in PostgreSQL with **pgvector**
- Provides a **Streamlit UI** for interactive querying

---

## Database Setup
### Step 1: Install PostgreSQL and pgvector
Ensure PostgreSQL is installed. Then, install the **pgvector** extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Step 2: Create Database
```sql
CREATE DATABASE vector_db;
```

### Step 3: Create Tables
```sql
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department_id INT REFERENCES departments(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    salary DECIMAL(10,2) NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    employee_id INT REFERENCES employees(id),
    order_total DECIMAL(10,2) NOT NULL,
    order_date DATE NOT NULL,
    embedding VECTOR(768)  -- Store vector embeddings
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    embedding VECTOR(768)  -- Store vector embeddings
);
```

### Step 4: Insert Sample Data
```sql
INSERT INTO departments (name) VALUES ('Sales'), ('Engineering');
INSERT INTO employees (name, department_id, email, salary) VALUES
    ('Alice', 1, 'alice@example.com', 60000.00),
    ('Bob', 2, 'bob@example.com', 75000.00);

INSERT INTO products (name, price) VALUES
    ('Wireless Headphones', 150.00),
    ('Smartphone', 800.00),
    ('Laptop', 1200.00);

INSERT INTO orders (customer_name, employee_id, order_total, order_date) VALUES
    ('John Doe', 1, 1200.00, '2024-02-01'),
    ('Jane Smith', 2, 150.00, '2024-02-05');
```

---

## Embedding Storage Script
This script **generates and stores embeddings** for products in the database.
```python
from google.generativeai import configure, embed_content
import psycopg2

configure(api_key="YOUR_API_KEY")

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
```

---

## Main Application Code
This **Streamlit app** allows users to query the database using natural language.
```python
import streamlit as st
import psycopg2
import google.generativeai as genai
import re

# Configure API
genai.configure(api_key="YOUR_API_KEY")

DB_NAME = "vector_db"
DB_USER = "postgres"
DB_PASSWORD = "mysecretpassword"

# Schema description
schema = '''The database "vector_db" consists of four tables: departments, employees, orders, and products...'''

# Initialize Model
model = genai.GenerativeModel("gemini-1.5-flash")

def get_text_embedding(text):
    response = genai.embed_content(model="models/embedding-001", content=text, task_type="retrieval_query")
    return response.get("embedding", None)

def generate_sql_query(user_input):
    similarity_keywords = ["similar", "like", "related"]
    use_vector_search = any(word in user_input.lower() for word in similarity_keywords)
    
    if use_vector_search:
        query_embedding = get_text_embedding(user_input)
        return "SELECT * FROM products ORDER BY embedding <=> %s LIMIT 5;", query_embedding
    else:
        prompt = f"""
        Convert this natural language query into a PostgreSQL SQL query using the schema provided.
        Your response should **ONLY** contain the SQL query.
        User query: {user_input}
        Schema: {schema}
        """
        response = model.generate_content(prompt)
        return response.text.strip(), None

def execute_sql_query(query, query_embedding=None):
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cur = conn.cursor()
    cur.execute(query, (query_embedding,)) if query_embedding else cur.execute(query)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

# Streamlit UI
st.title("Natural Language Search for PostgreSQL")
user_input = st.text_input("Enter your query:")
if st.button("Search"):
    sql_query, query_embedding = generate_sql_query(user_input)
    if sql_query:
        st.write(f"Generated SQL Query:\n{sql_query}")
        results = execute_sql_query(sql_query, query_embedding)
        st.write(results if results else "No results found.")
```

---

## Test Cases
| User Query | Expected SQL Query |
|------------|--------------------|
| "Find all employees in Sales" | `SELECT * FROM employees WHERE department_id = (SELECT id FROM departments WHERE name = 'Sales');` |
| "Show products similar to Smartphone" | `SELECT * FROM products ORDER BY embedding <=> %s LIMIT 5;` |
| "List orders handled by Alice" | `SELECT * FROM orders WHERE employee_id = (SELECT id FROM employees WHERE name = 'Alice');` |

---

## Running the Application
1. Install dependencies:
   ```sh
   pip install streamlit psycopg2 google-generativeai numpy
   ```
2. Run Streamlit app:
   ```sh
   streamlit run generatequery.py
   ```

Enjoy your **AI-powered database search!** 

