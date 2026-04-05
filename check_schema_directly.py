#!/usr/bin/env python3
"""
Script to check the database schema directly
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def check_schema_directly():
    """Check the database schema directly"""
    print("Checking database schema directly...")
    
    # Connect directly using psycopg2
    connection_string = os.getenv("DATABASE_URL")
    if not connection_string:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    try:
        conn = psycopg2.connect(connection_string)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check all columns in documents table
            cursor.execute("""
                SELECT column_name, data_type, udt_name, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name LIKE 'embedding%'
                ORDER BY column_name
            """)
            columns = cursor.fetchall()
            
            print("Embedding columns in documents table:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']} ({col['udt_name']}) - Max length: {col['character_maximum_length']}")
            
            # Also check for any vector columns
            cursor.execute("""
                SELECT column_name, data_type, udt_name, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND udt_name = 'vector'
                ORDER BY column_name
            """)
            vector_cols = cursor.fetchall()
            
            print(f"\nAll vector columns in documents table:")
            for col in vector_cols:
                print(f"  - {col['column_name']}: {col['data_type']} ({col['udt_name']}) - Max length: {col['character_maximum_length']}")
            
            conn.close()
            return True
            
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_schema_directly()
    if success:
        print("\n✅ Direct schema check completed!")
    else:
        print("\n❌ Direct schema check failed.")