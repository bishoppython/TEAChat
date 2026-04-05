#!/usr/bin/env python3
"""
Script to check and fix the database embedding column type
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager

def check_and_fix_embedding_column():
    """Check the current state of the embedding column and fix it if needed"""
    print("Checking database embedding column type...")
    
    db_manager = DatabaseManager()
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            # Check the current type of the embedding column
            cursor.execute("""
                SELECT column_name, data_type, udt_name, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name = 'embedding'
            """)
            result = cursor.fetchone()
            
            if result:
                column_name, data_type, udt_name, char_max_len = result
                print(f"Current embedding column info:")
                print(f"  - Column name: {column_name}")
                print(f"  - Data type: {data_type}")
                print(f"  - UDT name: {udt_name}")
                print(f"  - Max length: {char_max_len}")
                
                # If it's still a fixed-size vector, we need to update it
                if udt_name == 'USER-DEFINED' and char_max_len is not None:
                    print(f"  - This indicates a fixed-size vector (size: {char_max_len})")
                    print("  - Need to update to variable-size vector")
                    
                    # Try to update the column type
                    try:
                        cursor.execute(f"ALTER TABLE documents ALTER COLUMN embedding TYPE vector USING embedding::vector")
                        conn.commit()
                        print("✅ Embedding column updated to variable-size vector")
                    except Exception as e:
                        print(f"❌ Could not update embedding column: {e}")
                        # Try alternative approach
                        try:
                            # Check if there's a specific dimension constraint
                            cursor.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid = 'documents'::regclass AND attname = 'embedding'")
                            result = cursor.fetchone()
                            if result:
                                typmod = result[0]
                                print(f"Type modifier: {typmod}")
                                if typmod > 0:
                                    print(f"This confirms the column has a fixed dimension constraint of {typmod-4} (minus 4 for header)")
                                    # The typmod includes 4 bytes of header, so actual dimension is typmod-4
                                    actual_dim = typmod - 4
                                    print(f"Attempting to change to variable vector...")
                                    cursor.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector USING embedding::vector")
                                    conn.commit()
                                    print("✅ Successfully updated to variable-size vector")
                        except Exception as e2:
                            print(f"❌ Alternative approach also failed: {e2}")
                            return False
                else:
                    print("  - Column appears to be variable-size vector or already updated")
                    
            else:
                print("❌ Could not find embedding column in documents table")
                return False
    
    print("✅ Database check and fix completed")
    return True

if __name__ == "__main__":
    success = check_and_fix_embedding_column()
    if success:
        print("\n🎉 Database embedding column is properly configured for variable dimensions!")
    else:
        print("\n❌ Failed to fix the database embedding column.")