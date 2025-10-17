#!/usr/bin/env python3
"""
Test script to verify Dagster sensor setup
Run this to check if all components load correctly
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_imports():
    """Test if all modules can be imported."""
    print("Testing imports...")
    
    try:
        print("  ✓ Importing dagster...")
        from dagster import Definitions
        
        print("  ✓ Importing Google Drive resource...")
        from dagster_pipeline.resources import GoogleDriveResource
        
        print("  ✓ Importing asset...")
        from dagster_pipeline.assets.google_drive_etl import process_drive_files
        
        print("  ✓ Importing sensor...")
        from dagster_pipeline.sensors import google_drive_new_file_sensor
        
        print("  ✓ Importing definitions...")
        from dagster_pipeline.definitions import defs
        
        print("\n✅ All imports successful!\n")
        return True
    except ImportError as e:
        print(f"\n❌ Import failed: {e}\n")
        print("Make sure to install dependencies:")
        print("  pip install -e \".[dagster,google-api]\"\n")
        return False


def test_definitions():
    """Test if definitions are properly configured."""
    print("Testing Dagster definitions...")
    
    try:
        from dagster_pipeline.definitions import defs
        
        print(f"  ✓ Assets: {len(defs.assets)} loaded")
        for asset in defs.assets:
            print(f"    - {asset.key}")
        
        print(f"  ✓ Sensors: {len(defs.sensors)} loaded")
        for sensor in defs.sensors:
            print(f"    - {sensor.name}")
        
        print(f"  ✓ Resources: {len(defs.resources)} configured")
        for name in defs.resources.keys():
            print(f"    - {name}")
        
        print("\n✅ Definitions are valid!\n")
        return True
    except Exception as e:
        print(f"\n❌ Definitions test failed: {e}\n")
        return False


def test_google_drive_credentials():
    """Test if Google Drive credentials exist."""
    print("Testing Google Drive credentials...")
    
    import os
    
    creds_path = "auth/credentials.json"
    token_path = "token.json"
    
    if os.path.exists(creds_path):
        print(f"  ✓ Credentials file found: {creds_path}")
    else:
        print(f"  ⚠️  Credentials file not found: {creds_path}")
        print("     Download from Google Cloud Console")
    
    if os.path.exists(token_path):
        print(f"  ✓ Token file found: {token_path}")
    else:
        print(f"  ℹ️  Token file not found: {token_path}")
        print("     Will be created on first authentication")
    
    print()
    return True


def test_folders():
    """Test if required folders exist."""
    print("Testing local folders...")
    
    import os
    
    folders = ["downloaded_csv", "processed_data"]
    
    for folder in folders:
        if os.path.exists(folder):
            print(f"  ✓ Folder exists: {folder}/")
        else:
            print(f"  ℹ️  Folder will be created: {folder}/")
    
    print()
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("  Dagster Google Drive Sensor - Setup Verification")
    print("="*60)
    print()
    
    tests = [
        test_imports,
        test_definitions,
        test_google_drive_credentials,
        test_folders,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}\n")
            results.append(False)
    
    print("="*60)
    if all(results):
        print("✅ All tests passed! You're ready to start Dagster.")
        print("\nNext steps:")
        print("  1. Run: dagster dev -f dagster_pipeline/definitions.py")
        print("  2. Open: http://localhost:3000")
        print("  3. Enable the sensor in the UI")
        print("  4. Upload a CSV to Google Drive 'raw_data' folder")
        print("="*60)
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
