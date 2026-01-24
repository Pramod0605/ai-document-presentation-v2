import requests
import json

# Test the new structured content API
job_id = "1cd6d75c"
url = f"http://localhost:5005/job/{job_id}/presentation_for_review"

print(f"Fetching review data from: {url}\n")

try:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    print(f"✓ Successfully fetched data for job: {data.get('job_id')}")
    print(f"✓ Title: {data.get('title')}")
    print(f"✓ Number of sections: {len(data.get('sections', []))}\n")
    
    # Display structure of first section
    if data.get('sections'):
        section = data['sections'][0]
        print(f"=== Section {section.get('section_id')}: {section.get('title')} ===")
        print(f"Type: {section.get('section_type')}")
        print(f"Narration length: {len(section.get('narration_text', ''))} chars")
        
        content = section.get('content', {})
        print(f"\nContent structure:")
        print(f"  - Explanation Plan: {'✓' if content.get('explanation_plan') else '✗'}")
        print(f"  - Visual Beats: {len(content.get('visual_beats', []))} items")
        print(f"  - Bullet Items: {len(content.get('bullet_items', []))} items")
        print(f"  - Images: {len(content.get('images', []))} items")
        print(f"  - Quiz Data: {'✓' if content.get('quiz_data') else '✗'}")
        print(f"  - Flashcards: {len(content.get('flashcards', []))} items")
        
        # Show bullet items if present
        if content.get('bullet_items'):
            print(f"\n📌 Bullet Items:")
            for idx, item in enumerate(content['bullet_items'][:3], 1):
                print(f"  {idx}. {item}")
            if len(content['bullet_items']) > 3:
                print(f"  ... and {len(content['bullet_items']) - 3} more")
        
        # Show quiz if present
        if content.get('quiz_data'):
            quiz = content['quiz_data']
            questions = quiz.get('questions', [])
            print(f"\n❓ Quiz Questions: {len(questions)}")
            if questions:
                q = questions[0]
                print(f"  Q1: {q.get('question', '')[:80]}...")
                print(f"  Options: {len(q.get('options', []))}")
                print(f"  Correct: {q.get('correct_answer', '')}")
        
        # Show images if present
        if content.get('images'):
            print(f"\n🖼️ Images:")
            for idx, img in enumerate(content['images'], 1):
                print(f"  {idx}. ID: {img.get('image_id')} - {img.get('description', '')[:50]}...")
    
    # Save full response for inspection
    with open('review_structure_test.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Full response saved to: review_structure_test.json")
    
except requests.exceptions.RequestException as e:
    print(f"✗ Error fetching data: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
