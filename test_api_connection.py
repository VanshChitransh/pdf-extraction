"""
Quick diagnostic script to test Gemini API connectivity and key validity.

Run this FIRST before running any cost estimation pipelines.

Usage:
    python test_api_connection.py
"""

import os
import sys

def test_api_key():
    """Check if API key is set."""
    print("="*70)
    print("STEP 1: Checking API Key")
    print("="*70)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable is NOT set")
        print("\nTo fix:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        print("\nOr add to your ~/.zshrc:")
        print("  echo 'export GEMINI_API_KEY=\"your-api-key-here\"' >> ~/.zshrc")
        print("  source ~/.zshrc")
        return False
    
    print(f"✓ GEMINI_API_KEY is set: {api_key[:20]}..." if len(api_key) > 20 else f"✓ GEMINI_API_KEY is set: {api_key}")
    return True

def test_import():
    """Check if google-generativeai is installed."""
    print("\n" + "="*70)
    print("STEP 2: Checking google-generativeai Installation")
    print("="*70)
    
    try:
        import google.generativeai as genai
        print("✓ google-generativeai is installed")
        return True
    except ImportError as e:
        print(f"❌ google-generativeai NOT installed: {e}")
        print("\nTo fix:")
        print("  pip install google-generativeai")
        return False

def test_api_call():
    """Test actual API call with simple prompt."""
    print("\n" + "="*70)
    print("STEP 3: Testing API Call")
    print("="*70)
    
    try:
        import google.generativeai as genai
        
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        
        # Test with Gemini 2.5 Flash (best for complex reasoning)
        # Free tier: 5 requests/min, 100 requests/day
        model_names = [
            'gemini-2.5-flash',
            'gemini-2.5-flash-latest'
        ]
        
        last_error = None
        for model_name in model_names:
            try:
                print(f"Trying {model_name}...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Say 'Hello from Gemini API!'")
                print(f"✓ Success with {model_name}!")
                break
            except Exception as e:
                last_error = e
                continue
        else:
            # All models failed
            raise last_error
        
        print(f"✓ API call successful!")
        print(f"Response: {response.text}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ API call failed: {error_msg}")
        
        if "429" in error_msg or "quota" in error_msg.lower():
            print("\n⚠ Rate limit or quota exceeded")
            print("Solutions:")
            print("  1. Wait 60 seconds and try again")
            print("  2. Check quota at: https://aistudio.google.com/app/apikey")
            print("  3. Use gemini-1.5-flash (15 req/min) instead of gemini-2.5-pro (2 req/min)")
        elif "api" in error_msg.lower() and "key" in error_msg.lower():
            print("\n⚠ API key is invalid")
            print("Solutions:")
            print("  1. Verify key at: https://aistudio.google.com/app/apikey")
            print("  2. Generate new key if needed")
            print("  3. Make sure key has no extra spaces/quotes")
        elif "permission" in error_msg.lower():
            print("\n⚠ Permission denied")
            print("Solutions:")
            print("  1. Check API key permissions")
            print("  2. Ensure Gemini API is enabled in your project")
        
        return False

def test_json_response():
    """Test JSON response format (required for cost estimation)."""
    print("\n" + "="*70)
    print("STEP 4: Testing JSON Response Format")
    print("="*70)
    
    try:
        import google.generativeai as genai
        import json
        
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        
        # Use Gemini 2.5 Flash for JSON test
        model_names = [
            'gemini-2.5-flash',
            'gemini-2.5-flash-latest'
        ]
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                print(f"Requesting JSON response format from {model_name}...")
                response = model.generate_content(
                    'Return a JSON object with two fields: "status": "success", "message": "JSON works"',
                    generation_config={
                        "temperature": 0.3,
                        "response_mime_type": "application/json"
                    }
                )
                break
            except:
                continue
        
        # Try to parse as JSON
        data = json.loads(response.text)
        
        print(f"✓ JSON response successful!")
        print(f"Parsed data: {data}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"Raw response: {response.text[:200]}")
        print("\n⚠ API is returning non-JSON format")
        print("This will cause cost estimation to fail!")
        return False
        
    except Exception as e:
        print(f"❌ JSON test failed: {str(e)}")
        return False

def main():
    """Run all diagnostic tests."""
    print("\n🔍 GEMINI API DIAGNOSTIC TOOL")
    print("="*70)
    
    results = {
        "API Key Set": test_api_key(),
        "Library Installed": test_import(),
        "API Call": False,
        "JSON Response": False
    }
    
    # Only test API if key is set and library is installed
    if results["API Key Set"] and results["Library Installed"]:
        results["API Call"] = test_api_call()
        
        # Only test JSON if basic API call works
        if results["API Call"]:
            results["JSON Response"] = test_json_response()
    
    # Print summary
    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print("="*70)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("Your API is ready for cost estimation.")
        print("\nNext steps:")
        print("  python enhanced_cost_estimator.py --input enriched_data/6-report_enriched.json")
        return 0
    else:
        print("\n⚠ SOME TESTS FAILED")
        print("Fix the issues above before running cost estimation.")
        print("\nCommon fixes:")
        print("  1. Set API key: export GEMINI_API_KEY='your-key'")
        print("  2. Install library: pip install google-generativeai")
        print("  3. Check quota: https://aistudio.google.com/app/apikey")
        return 1

if __name__ == "__main__":
    sys.exit(main())

