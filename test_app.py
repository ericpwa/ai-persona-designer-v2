import py_compile
import os
import json
import re
import sys

def test_syntax():
    print("[TEST 1/5] Testing syntax compilation of app.py...")
    py_compile.compile("app.py", doraise=True)
    print("✅ app.py compiled with zero syntax errors!")

def test_assets():
    print("[TEST 2/5] Testing asset availability (style.css & config.toml)...")
    assert os.path.exists("style.css"), "style.css missing!"
    assert os.path.exists(".streamlit/config.toml"), ".streamlit/config.toml missing!"
    with open("style.css", "r", encoding="utf-8") as f:
        css = f.read()
        assert ".glass-card" in css, "Glassmorphism CSS missing!"
        assert "wizard-container" in css, "Wizard CSS missing!"
    print("✅ Assets verified successfully!")

def test_json_cleaner():
    print("[TEST 3/5] Testing clean_json_string robustness...")
    # Import clean_json_string from app
    from app import clean_json_string
    
    # Edge case 1: Raw JSON
    raw_1 = '[{"name": "Test"}]'
    assert json.loads(clean_json_string(raw_1)) == [{"name": "Test"}]
    
    # Edge case 2: Markdown fenced ```json
    raw_2 = '```json\n[{"name": "Test"}]\n```'
    assert json.loads(clean_json_string(raw_2)) == [{"name": "Test"}]
    
    # Edge case 3: Markdown fenced ``` with extra spaces
    raw_3 = '``` \n[{"name": "Test"}]\n ```'
    assert json.loads(clean_json_string(raw_3)) == [{"name": "Test"}]
    
    # Edge case 4: Text with prefix and suffix surrounding JSON
    raw_4 = 'Here is the JSON:\n[{"name": "Test"}]\nHope this helps!'
    assert json.loads(clean_json_string(raw_4)) == [{"name": "Test"}]
    
    print("✅ clean_json_string passed all edge case tests!")

def test_dependencies():
    print("[TEST 4/5] Testing core package imports...")
    import streamlit as st
    from google import genai
    from PIL import Image
    print("✅ All required packages (streamlit, google-genai, pillow) imported successfully!")

def test_session_schema():
    print("[TEST 5/5] Testing Session State Schema Default Variables...")
    from app import session_vars
    required_keys = ["step", "api_key", "api_key_valid", "model_name", "brand_name", "brand_desc", "num_personas", "personas"]
    for k in required_keys:
        assert k in session_vars, f"Missing key in session_vars: {k}"
    print("✅ Session state variables verified!")

if __name__ == "__main__":
    try:
        test_syntax()
        test_assets()
        test_json_cleaner()
        test_dependencies()
        test_session_schema()
        print("\n🎉 ALL 5 DD AUDIT VERIFICATION TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ DD TEST FAILED: {str(e)}")
        sys.exit(1)
