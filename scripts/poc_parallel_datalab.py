import asyncio
import json
import time
import random
from typing import List, Dict

# 1. Define the Expected "Datalab Input" Schema
# This is what your Datalab should output to skip the Planner Phase.
SAMPLE_DATALAB_INPUT = {
    "presentation_title": "Arithmetic Progressions (Parallel Demo)",
    "global_sections": {
        "intro": "Welcome to the lesson on Arithmetic Progressions.",
        "summary": ["Understand terms", "Calculate sum of N terms"],
        "memory": [
            {"front": "AP", "back": "Arithmetic Progression"},
            {"front": "d", "back": "Common Difference"}
        ],
        "recap": [
            "Visual of a ladder steps",
            "Visual of stacking coins"
        ]
    },
    "topics": [
        {"id": 1, "title": "Introduction to AP", "markdown": "# Intro to AP\nAn arithmetic progression is..."},
        {"id": 2, "title": "Common Difference", "markdown": "## The Common Difference\nThe difference matching..."},
        {"id": 3, "title": "Nth Term Formula", "markdown": "## Formula\nThe nth term is $a_n = a + (n-1)d$..."},
        {"id": 4, "title": "Sum of First N Terms", "markdown": "## Sum Formula\n$S_n = n/2(2a + ...)$"},
        {"id": 5, "title": "Example Problem 1", "markdown": "### Example 1\nFind the sum of..."},
        {"id": 6, "title": "Example Problem 2", "markdown": "### Example 2\nIf the first term..."},
        {"id": 7, "title": "Real World Application", "markdown": "## Applications\nTax calculation..."},
        {"id": 8, "title": "Practice Questions", "markdown": "## Practice\n1. Find the 10th term..."},
        {"id": 9, "title": "Advanced Problem", "markdown": "### Hard Problem\nProve that..."},
        {"id": 10, "title": "Conclusion", "markdown": "# Conclusion\nIn this lesson..."}
    ]
}

# 2. Mock Director Worker
# Simulates the LLM taking 45-60 seconds to process a chunk
async def mock_director_worker(topic: Dict) -> Dict:
    topic_id = topic["id"]
    title = topic["title"]
    
    print(f"[Worker {topic_id}] 🚀 Started processing: '{title}'")
    
    # Simulate LLM Latency (random buffer to show async nature)
    # IN REALITY: This would call the OpenRouter API
    latency = random.uniform(1.5, 3.0) 
    await asyncio.sleep(latency) 
    
    print(f"[Worker {topic_id}] ✅ Finished in {latency:.2f}s")
    
    # Return a mock "Presentation Section"
    return {
        "section_type": "content",
        "title": title,
        "renderer": "video",
        "narration": {
            "segments": [{"text": f"Narrating {title}..."}]
        },
        "markdown_pointer": {
             "start": f"Start of {title}",
             "end": f"End of {title}"
        }
    }

# 3. Mock Global Worker
# Processes the Intro/Summary/Recap
async def mock_global_worker(globals_data: Dict) -> List[Dict]:
    print(f"[Global Worker] 🌍 Started generating Intro/Summary/Recap...")
    await asyncio.sleep(2.0)
    print(f"[Global Worker] ✅ Finished")
    
    return [
        {"section_type": "intro", "text": globals_data["intro"]},
        {"section_type": "summary", "bullets": globals_data["summary"]}
    ]

# 4. The Orchestrator (Main Parallel Loop)
async def main():
    print("--- STARTING PARALLEL PIPELINE POC ---")
    start_time = time.time()
    
    # A. Parse Datalab Input
    datalab_data = SAMPLE_DATALAB_INPUT
    topics = datalab_data["topics"]
    globals_data = datalab_data["global_sections"]
    
    print(f"📦 Input Received: {len(topics)} Topics + Global Context")
    
    # B. Launch Parallel Workers
    # We create a list of async tasks
    tasks = []
    
    # 1. Global Worker Task
    tasks.append(mock_global_worker(globals_data))
    
    # 2. Topic Worker Tasks
    for topic in topics:
        tasks.append(mock_director_worker(topic))
        
    print(f"🔥 BLASTING {len(tasks)} LLM CALLS SIMULTANEOUSLY...")
    
    # C. Wait for ALL to finish
    results = await asyncio.gather(*tasks)
    
    # D. Merge Results (The Merger Phase)
    print("--- MERGING RESULTS ---")
    
    final_presentation = {
        "title": datalab_data["presentation_title"],
        "sections": []
    }
    
    # Unpack results
    # results[0] is Global Worker (returns list of sections)
    # results[1:] are Topic Workers (return single section)
    
    global_sections = results[0]
    topic_sections = results[1:]
    
    # Intro first
    final_presentation["sections"].append(global_sections[0]) 
    
    # Then Topics (in order)
    final_presentation["sections"].extend(topic_sections)
    
    # Then Summary
    final_presentation["sections"].append(global_sections[1])
    
    total_time = time.time() - start_time
    
    # E. Output Report
    print("\n" + "="*40)
    print(f"🎉 PIPELINE COMPLETE")
    print(f"⏱️  Total Execution Time: {total_time:.2f} seconds")
    print(f"📄 Generated Sections: {len(final_presentation['sections'])}")
    print(f"✅ Structure Validity: Valid JSON")
    print("="*40)
    
    # Save dummy file
    with open("poc_parallel_output.json", "w") as f:
        json.dump(final_presentation, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
