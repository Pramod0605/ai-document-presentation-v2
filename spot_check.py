import json

# Load presentation
p = json.load(open('player/jobs/d76a0cc1/presentation.json', encoding='utf-8'))
sections = p['sections']

print("=" * 60)
print("SPOT CHECK: First, Middle, Last Sections")
print("=" * 60)

# First section
print("\n=== SECTION 1 (Beginning) ===")
s1 = sections[0]
print(f"Title: {s1.get('title')}")
nar1 = s1.get('narration', {}).get('full_text', '')
print(f"Narration ({len(nar1)} chars):")
print(f"  {nar1[:150]}...")

# Middle section (9th of 18)
print("\n=== SECTION 9 (Middle) ===")
s9 = sections[8]
print(f"Title: {s9.get('title')}")
nar9 = s9.get('narration', {}).get('full_text', '')
print(f"Narration ({len(nar9)} chars):")
print(f"  {nar9[:150]}...")

# Last section
print("\n=== SECTION 18 (End) ===")
slast = sections[-1]
print(f"Title: {slast.get('title')}")
narlast = slast.get('narration', {}).get('full_text', '')
print(f"Narration ({len(narlast)} chars):")
print(f"  {narlast[:150]}...")
