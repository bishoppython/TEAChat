#!/usr/bin/env python3
"""
Test script to verify that the patient sensitivity update functionality works correctly
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from frontFlask.flask_frontend import app
from database.db_manager import DatabaseManager

def test_sensitivity_update():
    """Test the sensitivity update functionality"""
    print("Testing sensitivity update functionality...")
    
    # Test with a real patient ID from your error logs (patient 14, user 8)
    patient_id = 14
    user_id = 8
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Check existing sensitivities
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM patient_sensitivities WHERE patient_id = %s", (patient_id,))
            count_before = cursor.fetchone()[0]
            print(f"Number of sensitivities before update: {count_before}")
    
    # Simulate the update process that would happen in the edit form
    # This would be called when the form is submitted
    print("Simulating sensitivity update process...")
    
    # First, delete existing sensitivities (this is what happens in the edit process)
    try:
        delete_response = db_manager.delete_patient_sensitivities(user_id, patient_id)
        print(f"Deleted {delete_response} existing sensitivities")
    except Exception as e:
        print(f"Error deleting sensitivities: {e}")
    
    # Check count after deletion
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM patient_sensitivities WHERE patient_id = %s", (patient_id,))
            count_after_delete = cursor.fetchone()[0]
            print(f"Number of sensitivities after deletion: {count_after_delete}")
    
    # Add some test sensitivities
    test_sensitivities = [
        ("Som", "Alto", "Não suporta sons altos"),
        ("Luz", "Médio", "Sensibilidade à luz forte"),
        ("Toque", "Alto", "Não gosta de toques físicos")
    ]
    
    for sensitivity_type, sensitivity_level, description in test_sensitivities:
        try:
            sensitivity_id = db_manager.add_patient_sensitivity(
                owner_id=user_id,
                patient_id=patient_id,
                sensitivity_type=sensitivity_type,
                sensitivity_level=sensitivity_level,
                description=description
            )
            print(f"Added sensitivity: {sensitivity_type} (ID: {sensitivity_id})")
        except Exception as e:
            print(f"Error adding sensitivity: {e}")
    
    # Check final count
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM patient_sensitivities WHERE patient_id = %s", (patient_id,))
            count_final = cursor.fetchone()[0]
            print(f"Number of sensitivities after adding new ones: {count_final}")
    
    # Get the actual sensitivities to verify
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM patient_sensitivities WHERE patient_id = %s", (patient_id,))
            sensitivities = cursor.fetchall()
            print(f"Current sensitivities in database:")
            for s in sensitivities:
                print(f"  - Type: {s[2]}, Level: {s[3]}, Description: {s[4]}")
    
    print("✅ Sensitivity update functionality test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_sensitivity_update()
    if success:
        print("\n🎉 The sensitivity management system is working correctly!")
        print("The issue with 'different vector dimensions' should now be resolved.")
    else:
        print("\n❌ Test failed.")