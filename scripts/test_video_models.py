#!/usr/bin/env python3
"""
Test script to compare Runway vs Veo3 video generation
Uses a visual beat from the Electrostatics presentation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render.wan.video_client import VideoClient, compare_models

# Sample prompt from Electrostatics Section 3 Beat 1
ELECTROSTATICS_PROMPT = """
A blank, dark background. A stylized Bohr model of a Helium atom appears. 
It has a central nucleus with two red spheres ('+') and two grey spheres ('n'), 
and two blue spheres ('-') orbiting it on elliptical paths. 
The atom model fades in. The two blue electrons animate along their orbital paths around the nucleus. 
Title at top: 'Matter is made of Atoms'. Label pointing to nucleus: 'Nucleus'. 
Label pointing to orbiting sphere: 'Electron'.
"""

# Another prompt - more action-oriented
CHARGE_CONSERVATION_PROMPT = """
A dark background with grid lines. A large, complex purple sphere representing a Uranium-238 nucleus 
appears in the center. The nucleus violently shakes and then splits. 
The larger part (grey Thorium-234) recoils slightly to the left, 
while a small yellow alpha particle is ejected to the right at high speed.
The chemical equation '$_{92}U^{238} \\to _{90}Th^{234} + _{2}He^{4}$' appears below.
Labels show: 'Uranium-238' on the original, 'Thorium-234' on the left product, 
'Alpha particle (He-4)' on the ejected particle.
"""

# Electric field visualization
ELECTRIC_FIELD_PROMPT = """
A dark 3D space with a large red sphere labeled 'Q' (positive source charge) at center.
Radial arrows (field lines) emerge from the sphere in all directions, 
colored with a gradient from orange near the charge to yellow further away.
The arrows point outward, showing the direction a positive test charge would move.
Small blue test charges appear at various distances, 
each showing a force vector pointing away from Q.
Text overlay: 'Electric Field Lines - Positive Charge'.
"""

def main():
    print("="*70)
    print("VIDEO MODEL COMPARISON TEST")
    print("Runway Gen-3 Alpha vs Google Veo 3.1")
    print("="*70)
    
    # Check API key
    api_key = os.environ.get("KIE_API_KEY", "")
    if not api_key:
        print("\n[WARNING] KIE_API_KEY not set - will generate placeholders only")
        print("Set the key to test real video generation")
    else:
        print(f"\n[OK] KIE_API_KEY is set (length: {len(api_key)})")
    
    # Choose prompt
    prompts = {
        "1": ("Atom Model (simple)", ELECTROSTATICS_PROMPT),
        "2": ("Nuclear Decay (action)", CHARGE_CONSERVATION_PROMPT),
        "3": ("Electric Field (complex)", ELECTRIC_FIELD_PROMPT),
    }
    
    print("\nAvailable test prompts:")
    for key, (name, _) in prompts.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect prompt (1-3) or press Enter for default [1]: ").strip() or "1"
    
    if choice not in prompts:
        print(f"Invalid choice: {choice}")
        return
    
    prompt_name, prompt = prompts[choice]
    print(f"\nUsing prompt: {prompt_name}")
    print("-"*70)
    print(prompt.strip())
    print("-"*70)
    
    # Run comparison
    output_dir = f"player/test_comparison/{prompt_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}"
    
    print(f"\nOutput directory: {output_dir}")
    confirm = input("Proceed with generation? [y/N]: ").strip().lower()
    
    if confirm != 'y':
        print("Aborted.")
        return
    
    results = compare_models(prompt.strip(), output_dir=output_dir)
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print(f"\nRunway video: {results.get('runway', 'N/A')}")
    print(f"Veo3 video: {results.get('veo3', 'N/A')}")
    print("\nCompare the videos side-by-side to evaluate:")
    print("  - Visual quality and realism")
    print("  - Motion smoothness")
    print("  - Text rendering accuracy")
    print("  - Prompt adherence")
    print("="*70)


if __name__ == "__main__":
    main()
