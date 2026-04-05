#!/usr/bin/env python3
"""
Script to fix the database embedding column to be variable-size
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager

def fix_embedding_column():
    """Fix the embedding column to be variable-size"""
    print("Fixing embedding column to be variable-size...")
    
    db_manager = DatabaseManager()
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # First, let's check the current state
                cursor.execute("""
                    SELECT 
                        a.attname AS column_name,
                        pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                        a.atttypmod
                    FROM pg_catalog.pg_attribute a
                    WHERE a.attrelid = 'documents'::regclass
                    AND a.attname = 'embedding'
                    AND a.attnum > 0
                """)
                result = cursor.fetchone()
                
                if result:
                    column_name, current_type, atttypmod = result
                    print(f"Current type: {current_type}")
                    print(f"Type modifier: {atttypmod}")
                    
                    if "vector(" in current_type and ")" in current_type:
                        print("Column still has fixed dimension - need to update...")
                        
                        # ALTER the column to remove dimension constraint
                        cursor.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector USING embedding::vector")
                        conn.commit()
                        
                        # Verify the change
                        cursor.execute("""
                            SELECT 
                                pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
                            FROM pg_catalog.pg_attribute a
                            WHERE a.attrelid = 'documents'::regclass
                            AND a.attname = 'embedding'
                            AND a.attnum > 0
                        """)
                        new_result = cursor.fetchone()
                        if new_result:
                            new_type = new_result[0]
                            print(f"New type: {new_type}")
                            
                            if new_type == "vector":
                                print("✅ Column successfully updated to variable-size vector!")
                                return True
                            else:
                                print(f"❌ Column update may have failed. New type is: {new_type}")
                                return False
                    else:
                        print("Column is already variable-size or update not needed")
                        return True
                else:
                    print("❌ Could not find embedding column")
                    return False
                    
            except Exception as e:
                print(f"❌ Error updating column: {e}")
                import traceback
                traceback.print_exc()
                return False

if __name__ == "__main__":
    success = fix_embedding_column()
    if success:
        print("\n🎉 Database embedding column has been successfully updated to support variable dimensions!")
    else:
        print("\n❌ Failed to update the database embedding column.")