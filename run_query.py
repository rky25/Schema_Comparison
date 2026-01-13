import sys
import os
import pandas as pd
from sqlalchemy import create_engine, text

# Ensure backend folder is visible
sys.path.append(os.getcwd())

from backend.database import SQLALCHEMY_DATABASE_URL

def run_query(sql_query):
    print(f"Executing: {sql_query}")
    print("-" * 50)
    
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        with engine.connect() as conn:
            # Check if it's a SELECT statement to fetch results
            if sql_query.strip().upper().startswith("SELECT"):
                df = pd.read_sql(text(sql_query), conn)
                if df.empty:
                    print("Query executed successfully but returned no results.")
                else:
                    print(df.to_markdown(index=False, tablefmt="grid"))
                    print(f"\nRows returned: {len(df)}")
            else:
                # For INSERT, UPDATE, DELETE, etc.
                result = conn.execute(text(sql_query))
                conn.commit()
                print(f"Query executed successfully. Rows affected: {result.rowcount}")
                
    except Exception as e:
        print(f"Error executing query: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Take query from command line argument
        query = " ".join(sys.argv[1:])
        run_query(query)
    else:
        # Interactive mode
        print("Enter your SQL query (or 'exit' to quit):")
        while True:
            try:
                user_input = input("\nSQL> ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input.strip():
                    continue
                run_query(user_input)
            except KeyboardInterrupt:
                print("\nExiting...")
                break
