import streamlit as st
import psycopg2
import re
import google.generativeai as genai
import numpy as np
import psycopg2.extras

# Configure Google Generative AI API
genai.configure(api_key="your api key")

# Database connection settings
DB_NAME = "vector_db"
DB_USER = "postgres"
DB_PASSWORD = "mysecretpassword"

# Schema description for LLM give according to you db
schema = '''The database "vector_db" consists of four tables: departments, 
employees, orders, and products. The "departments" table has (id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL). 
The "employees" table has (id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL, department_id INT REFERENCES 
departments(id), email VARCHAR(255) UNIQUE NOT NULL, salary DECIMAL(10,2) NOT NULL). 
The "orders" table has (id SERIAL PRIMARY KEY, customer_name VARCHAR(100) NOT NULL, employee_id INT REFERENCES 
employees(id), order_total DECIMAL(10,2) NOT NULL, order_date DATE NOT NULL, embedding vector(768) 
for vector search). The "products" table has (id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL, price DECIMAL(10,2) 
NOT NULL, embedding vector(768) for vector search). 

Relationships: employees.department_id → departments.id (each employee belongs to a department), 
orders.employee_id → employees.id (each order is handled by an employee). 

If the query involves searching for similar products or orders, generate an embedding for the query and use 
vector similarity search: `embedding <=> QUERY_VECTOR`. Combine it with SQL filters if necessary.
'''

# Initialize Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

def get_text_embedding(text):
    try:
        response = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_query"
        )
        return response.get("embedding", None)  # Extract embedding vector safely
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def generate_sql_query(user_input):
    try:
        # Detect if the query requires vector search
        similarity_keywords = ["similar", "like", "related", "matching", "relevant"]
        use_vector_search = any(word in user_input.lower() for word in similarity_keywords)

        if use_vector_search:
            query_embedding = get_text_embedding(user_input)

            if query_embedding is None:
                return None, None  # Error in embedding

            # Use the correct hybrid search SQL query
            sql_query = "SELECT * FROM products ORDER BY embedding <=> %s LIMIT 5;"
            return sql_query, query_embedding

        else:
            # Standard SQL query generation
            prompt = f"""
            Convert this natural language query into a **PostgreSQL SQL query** using the schema provided.
            Your response should **ONLY** contain the SQL query. if that is vector search, please use this syntax  
        SELECT content, 1 - (embedding <=> %s) AS similarity
        FROM documents
        ORDER BY similarity DESC
        LIMIT %s
    

            User query: {user_input}
            Schema: {schema}
            """

            response = model.generate_content(prompt)
            sql_query = response.text.strip()
            return sql_query, None

    except Exception as e:
        print(f"Error generating SQL query: {e}")
        return None, None

# Function to adapt NumPy arrays to PostgreSQL


def execute_sql_query(query, query_embedding=None, top_k=1):
    conn = None
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        cur = conn.cursor()

        if query_embedding:
            # Ensure embedding is in correct format
            query_embedding = np.array(query_embedding, dtype=np.float32).tolist()
            embedding_str = f"ARRAY{query_embedding}::vector"

            # Inject embedding directly into SQL query
            sql_query = query.replace("%s", embedding_str)  
            sql_query = sql_query.replace("LIMIT 5", f"LIMIT {top_k}")  # Adjust top_k dynamically

            cur.execute(sql_query)

        else:
            cur.execute(query)

        results = cur.fetchall()
        return results
    except Exception as e:
        print(f"Error executing query: {e}")
        return None
    finally:
        if conn:
            conn.close()

# Streamlit UI
st.title("Natural Language Search for PostgreSQL")

user_input = st.text_input("Enter your query:")
if st.button("Search"):
    sql_query, query_embedding = generate_sql_query(user_input)

    if sql_query:
        # Clean unnecessary markdown formatting
        sql_query = re.sub(r"```sql|```", "", sql_query).strip()
        st.write(f"Generated SQL Query:\n{sql_query}")

        if "SELECT" in sql_query:
            results = execute_sql_query(sql_query, query_embedding)
            if results:
                st.write(results)
            else:
                st.error("No results found or query execution failed.")
        else:
            st.error("Invalid SQL Query!")
    else:
        st.error("Failed to generate a valid SQL query.")
