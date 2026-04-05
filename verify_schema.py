#!/usr/bin/env python3
"""
Script to verify the database schema has been updated correctly
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager

def verify_schema_update():
    """Verify that the database schema has been updated correctly"""
    print("Verifying database schema update...")
    
    db_manager = DatabaseManager()
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            # Check all embedding columns
            cursor.execute("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name LIKE 'embedding%'
                ORDER BY column_name
            """)
            columns = cursor.fetchall()
            
            print("Embedding columns found in documents table:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} ({col[2]})")
            
            # Check if the old column still exists
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name = 'embedding'
            """)
            old_col = cursor.fetchone()
            
            if old_col:
                print(f"❌ Old embedding column still exists: {old_col[0]}")
                return False
            else:
                print("✅ Old embedding column has been removed")
            
            # Check if we have the new columns
            expected_cols = ['embedding_768', 'embedding_1536', 'embedding_3072']
            found_cols = [col[0] for col in columns]
            
            missing_cols = [col for col in expected_cols if col not in found_cols]
            if missing_cols:
                print(f"❌ Missing expected columns: {missing_cols}")
                return False
            else:
                print(f"✅ All expected columns found: {expected_cols}")
            
            return True

if __name__ == "__main__":
    success = verify_schema_update()
    if success:
        print("\n🎉 Database schema verification successful!")
    else:
        print("\n❌ Database schema verification failed.")