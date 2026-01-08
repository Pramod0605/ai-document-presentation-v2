import sys
import os
import logging
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agents.manim_code_generator import ManimCodeGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ManimStressTest")

def run_stress_test():
    print("=== STARTING MANIM STRESS TEST SUITE ===")
    
    # --- CONFIGURATION ---
    # PASTE YOUR API KEY HERE IF ENV VARS FAIL
    HARDCODED_API_KEY = "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"
 
    # Example: HARDCODED_API_KEY = "sk-or-..." 

    # Initialize Generator
    api_key = HARDCODED_API_KEY
    
    if not api_key:
        try:
            from dotenv import load_dotenv
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            env_path = os.path.join(project_root, '.env')
            load_dotenv(env_path)
            api_key = os.environ.get("OPENROUTER_API_KEY")
        except ImportError:
            pass

    if api_key:
        print(f"API Key active: {api_key[:5]}...{api_key[-4:]}")
    else:
        print("WARNING: No API Key found (Env or Hardcoded). Generation checks will fail.")

    # Pass key explicitly to generator
    generator = ManimCodeGenerator(openrouter_api_key=api_key)
    
    # Define Test Cases adapted for ManimCodeGenerator input format
    test_cases = [
        {
            "name": "physics_heavy_math",
            "section_title": "Quantum Wave Function",
            "narration_segments": [
                {"text": "The wave function collapses.", "duration_seconds": 5.0},
                {"text": "Probability distribution.", "duration_seconds": 5.0}
            ],
            "manim_spec": "Show the Schrodinger equation. Then show a bell curve flattening out.",
            "formulas": ["Psi(x, t) = A * e^(i(kx - wt))"],
            "key_terms": ["Wave Function", "Probability"],
            "previous_errors": None
        },
        {
            "name": "currency_encoding",
            "section_title": "Inflation in India",
            "narration_segments": [
                {"text": "Prices rose by 50 rupees.", "duration_seconds": 5.0},
                {"text": "This affects savings.", "duration_seconds": 5.0}
            ],
            "visual_description": "Show a price tag of 100 rupees increasing to 150 rupees. Use a bulleted list for impacts. Mention 'Prices > 50'",
            "key_terms": ["Inflation", "CPI"],
            "previous_errors": None
        },
        {
            "name": "rapid_fire_timing",
            "section_title": "Quick Facts",
            "narration_segments": [
                {"text": "Fact one.", "duration_seconds": 2.0},
                {"text": "Fact two.", "duration_seconds": 2.0},
                {"text": "Fact three.", "duration_seconds": 2.0}
            ],
            "visual_description": "Flash a square. Flash a circle. Flash a triangle.",
            "key_terms": ["Shapes"],
            "previous_errors": None
        },
         {
             "name": "particle_system_attempt",
             "section_title": "Gas Simulation",
             "narration_segments": [
                 {"text": "The gas molecules move randomly in the container.", "duration_seconds": 5.0}
             ],
             "visual_description": "Show 50 small circles bouncing around inside a box to simulate gas temperature.",
             "key_terms": ["Thermodynamics"],
             "previous_errors": None
        }
    ]

    results = []

    for case in test_cases:
        print(f"\n--- Testing Case: {case['name']} ---")
        try:
            # Generate Code (this runs generation + validation + repair loop)
            # We rely on the internal validation we just added to catch issues
            code = generator.generate_code(case)
            
            if code:
                # Extra check: Run our manual validator again just to be sure
                errors = generator.validate_code(code, case)
                if errors:
                     print(f"[{case['name']}] PASS-ish: Code generated but has validation warnings: {errors}")
                     results.append((case['name'], "WARN"))
                else:
                    print(f"[{case['name']}] PASS: Code generated and validated successfully.")
                    results.append((case['name'], "PASS"))
                
                # Save for inspection
                output_path = f"tests/output_{case['name']}.py"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"Saved to {output_path}")

            else:
                print(f"[{case['name']}] FAIL: Generator returned empty code (Max retries exceeded).")
                results.append((case['name'], "FAIL"))
                
        except Exception as e:
            print(f"[{case['name']}] FAIL: Exception - {str(e)}")
            results.append((case['name'], "ERROR"))

    print("\n=== TEST SUMMARY ===")
    for name, status in results:
        print(f"{name}: {status}")

if __name__ == "__main__":
    run_stress_test()
