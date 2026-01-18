"""
V2.5 Unified Director Generator
Implements the "Director-Pointer" architecture.
Inherits from UnifiedContentGenerator but overrides validation and schema transformation.
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from core.unified_content_generator import GeneratorConfig, normalize_output, extract_json_from_response, call_openrouter_llm
from core.utils.markdown_chunker import smart_split

logger = logging.getLogger(__name__)

# Load Prompts
def get_prompts():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "prompts", "director_system_prompt.txt"), "r", encoding="utf-8") as f:
        director_system = f.read()
    with open(os.path.join(base, "prompts", "director_user_prompt.txt"), "r", encoding="utf-8") as f:
        director_user = f.read()
    with open(os.path.join(base, "prompts", "planner_system_prompt.txt"), "r", encoding="utf-8") as f:
        planner_system = f.read()
    with open(os.path.join(base, "prompts", "planner_bone_prompt.txt"), "r", encoding="utf-8") as f:
        planner_bone_system = f.read()
    return director_system, director_user, planner_system, planner_bone_system

class DirectorGenerator:
    """
    Stand-alone generator class for V2.5 Director Mode.
    We don't strictly inherit because we want clean separation of logic.
    """
    
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()

    def generate_presentation(
        self,
        markdown_content: str,
        subject: str = "Science",
        grade: str = "Grade 10",
        images_list: str = "None",
        topic_heading: str = None,
        system_prompt: str = None
    ) -> dict:
        """
        Inner Director Loop: Generate sections for a specific topic chunk.
        Uses specialized prompts if provided.
        """
        # 1. Prepare Prompts
        director_system = system_prompt
        director_user = None
        
        if not director_system:
             # Fallback to default load
             director_system, director_user_template, _, _ = get_prompts()
             director_user = director_user_template

        if not director_user:
             # Load user prompt template if we only passed system prompt (case for specialized topic prompt)
             _, director_user_template, _, _ = get_prompts()
             director_user = director_user_template
        
        user_prompt = director_user.format(
            subject=subject,
            grade=grade,
            images_list=images_list,
            markdown_content=markdown_content
        )

        logger.info("DirectorGenerator: Starting LLM call...")

        # reuse existing retry logic via function call if possible, 
        # or implement simple retry here since we are using functional core
        # For simple integration, we'll mimic the retry loop from unified_content_generator
        
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                # 1. Call LLM
                response, usage = call_openrouter_llm(director_system, user_prompt, self.config)
                
                # 2. Extract JSON
                data = extract_json_from_response(response)
                
                # 3. Normalize
                data = normalize_output(data)
                
                # 4. Validate (New Director Schema) - NON-BLOCKING
                is_valid, errors = self.validate_director_schema(data, markdown_content)
                if not is_valid:
                    logger.warning(f"⚠️ Pointer validation warnings: {errors}")
                    logger.warning("Proceeding anyway - Player will handle resolution at runtime")
                    # Don't fail - let the job complete
                
                logger.info(f"DirectorGenerator: Success (Attempt {attempt + 1})")
                data["_llm_usage"] = usage
                data["spec_version"] = "v1.5-v2.5-director"
                return data

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                # Backoff logic is in lower layers usually, but here we just continue
        
        raise last_error

    def generate_presentation_loop(
        self,
        markdown_content: str,
        subject: str = "Science",
        grade: str = "Grade 10",
        images_list: str = "None",
        update_status_callback=None
    ) -> dict:
        """
        Main entry point for V2.5 Director Planner-Executor Loop.
        1. Pass 1: Planner creates blueprint and logical chunks.
        2. Pass 2: Director executes each logical chunk in a loop.
        3. Merges results into final presentation.
        """
        director_sys, director_usr, planner_sys, _ = get_prompts()
        
        # --- PASS 1: THE PLANNER ---
        msg = "Phase 1: Generating Lesson Blueprint..."
        logger.info(f"DirectorGenerator: {msg}")
        if update_status_callback:
            update_status_callback("llm_generation", msg)

        planner_user = f"Subject: {subject}\nGrade: {grade}\n\nDOCUMENT CONTENT:\n{markdown_content}"
        
        try:
            planner_response, planner_usage = call_openrouter_llm(planner_sys, planner_user, self.config)
            blueprint = extract_json_from_response(planner_response)
        except Exception as e:
            logger.error(f"Planner failed: {e}. Falling back to blind chunking.")
            # Fallback to character-based chunking if planner fails
            return self._legacy_blind_loop(markdown_content, subject, grade, images_list, update_status_callback)

        plan = blueprint.get("logical_plan", [])
        globals = blueprint.get("global_sections", {})
        
        logger.info(f"DirectorGenerator: Planner identified {len(plan)} logical topics.")

        final_presentation = {
            "presentation_title": blueprint.get("presentation_title", "Educational Presentation"),
            "sections": [],
            "metadata": {
                "generated_by": "v1.5-v2.5-director",
                "total_topics": len(plan),
                "planner_id": "v2.5-pro-planner"
            }
        }

        # --- PASS 2: THE DIRECTOR LOOP ---
        total_usage = planner_usage

        # A. Add Intro (from Blueprint)
        intro_text = globals.get("intro", {}).get("text", "Welcome to the lesson.")
        final_presentation["sections"].append({
            "section_type": "intro",
            "title": "Introduction",
            "renderer": "none",
            "narration": {
                "segments": [{"segment_id": "intro_1", "text": intro_text}]
            }
        })

        # B. Loop through Topics
        for i, topic in enumerate(plan):
            title = topic.get("topic_heading", f"Topic {i+1}")
            msg = f"Phase 2: Directing Topic {i+1}/{len(plan)}: {title}"
            logger.info(f"DirectorGenerator: {msg}")
            if update_status_callback:
                update_status_callback("llm_generation", msg)

            # Extract partial markdown for this topic
            start_p = topic.get("start_phrase", "")
            end_p = topic.get("end_phrase", "")
            
            # Smart extraction: Find positions in source
            topic_md = self._extract_topic_markdown(markdown_content, start_p, end_p)
            
            try:
                topic_data = self.generate_presentation(topic_md, subject, grade, images_list, topic_heading=title)
                
                # Merge sections
                new_sections = topic_data.get("sections", [])
                for sec in new_sections:
                    # Filter out any duplicated intros/summaries the Director might have hallucinated
                    if sec.get("section_type") in ["intro", "summary", "recap"] and i > 0:
                        continue
                    final_presentation["sections"].append(sec)

                # Accumulate usage
                usage = topic_data.get("_llm_usage", {})
                for k in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                    total_usage[k] = total_usage.get(k, 0) + usage.get(k, 0)

            except Exception as e:
                logger.error(f"Error in Topic {i+1}: {e}")
                continue

        # C. Add Summary, Memory, Recap (from Blueprint)
        self._add_global_footer(final_presentation, globals)

        final_presentation["_llm_usage"] = total_usage
        return final_presentation

    def _extract_topic_markdown(self, full_md, start, end):
        """Extract markdown segment between two phrases."""
        if not start or not end:
            return full_md # No fallback limit
            
        start_idx = full_md.find(start)
        end_idx = full_md.find(end)
        
        if start_idx != -1 and end_idx != -1:
            return full_md[start_idx : end_idx + len(end)]
        
        # If not found, return full text
        return full_md

    def _add_global_footer(self, presentation, globals):
        """Add Summary, Memory, and Recap sections from the Planner blueprint."""
        # Summary
        summary_bullets = globals.get("summary", {}).get("bullets", [])
        if summary_bullets:
            presentation["sections"].append({
                "section_type": "summary",
                "title": "Lesson Summary",
                "renderer": "none",
                "visual_beats": [{"visual_type": "bullet_list", "display_text": "\n".join(f"• {b}" for b in summary_bullets)}],
                "narration": {"segments": [{"segment_id": "summ_1", "text": "To summarize what we've learned today..."}]}
            })

        # Memory (Flashcards)
        memory_cards = globals.get("memory", [])
        if memory_cards:
            presentation["sections"].append({
                "section_type": "memory",
                "title": "Key Concept Review",
                "flashcards": memory_cards,
                "narration": {"segments": [{"segment_id": "mem_1", "text": "Let's review the key terms for your memory."}]}
            })

        # Recap (exactly 5 scenes)
        recap_scenes = globals.get("recap", [])
        if len(recap_scenes) >= 5:
            presentation["sections"].append({
                "section_type": "recap",
                "title": "Visual Recap",
                "renderer": "video",
                "video_prompts": [
                    {"segment_id": f"rec_{j+1}", "prompt": scene, "duration_hint": 10}
                    for j, scene in enumerate(recap_scenes[:5])
                ]
            })

    def _legacy_blind_loop(self, markdown_content, subject, grade, images_list, update_status_callback):
        """Character-based chunking fallback if planner fails."""
        chunks = smart_split(markdown_content, target_chars=8000)
        # ... (reuse existing loop logic if needed) ...
        return self.generate_presentation(markdown_content, subject, grade, images_list)

    def validate_director_schema(self, data: dict, source_markdown: str) -> Tuple[bool, List[str]]:
        """
        Validate JSON structure AND pointer integrity.
        """
        errors = []
        
        if "sections" not in data:
            return False, ["Missing 'sections'"]

        for idx, section in enumerate(data.get("sections", [])):
            sec_id = section.get("section_id", f"s{idx}")
            
            # Check narration segments
            segments = section.get("narration", {}).get("segments", [])
            for s_idx, seg in enumerate(segments):
                # Validating Pointers
                vis = seg.get("visual_content", {})
                pointer = vis.get("markdown_pointer")
                
                if pointer:
                    start = pointer.get("start_phrase", "")
                    end = pointer.get("end_phrase", "")
                    
                    if not start or not end:
                        errors.append(f"[{sec_id}] Segment {s_idx}: Empty pointer phrases")
                        continue
                        
                    # SMART VALIDATION: Normalize both phrases and source before comparing
                    # This handles whitespace, punctuation differences while ensuring real matches
                    def normalize_phrase(text):
                        """Normalize text for comparison - collapse spaces, remove formatting artifacts"""
                        import re
                        # Remove extra whitespace
                        text = re.sub(r'\s+', ' ', text)
                        # Normalize quotes
                        text = text.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
                        # Remove markdown artifacts that might differ
                        text = text.replace('$$', '$').replace('**', '')
                        return text.strip().lower()
                    
                    start_norm = normalize_phrase(start)
                    end_norm = normalize_phrase(end)
                    source_norm = normalize_phrase(source_markdown)
                    
                    # Check if normalized phrase exists in normalized source
                    start_found = start_norm in source_norm
                    end_found = end_norm in source_norm
                    
                    if not start_found:
                        # Try line-by-line match for better precision
                        start_found = any(start_norm in normalize_phrase(line) 
                                        for line in source_markdown.split('\n'))
                    
                    if not end_found:
                        end_found = any(end_norm in normalize_phrase(line) 
                                      for line in source_markdown.split('\n'))
                    
                    if not start_found:
                        errors.append(f"[{sec_id}] Pointer START not found in source: '{start[:30]}...'")
                    
                    if not end_found:
                        errors.append(f"[{sec_id}] Pointer END not found in source: '{end[:30]}...'")

        return len(errors) == 0, errors

    async def generate_presentation_parallel(
        self,
        markdown_content: str,
        subject: str = "Science",
        grade: str = "Grade 10",
        images_list: str = "None",
        update_status_callback=None
    ) -> dict:
        """
        V2.5 PARALLEL Execution Pipeline:
        1. PLANNER: Extracts "Bone" structure (Topics + Global Context).
        2. WORKERS: Runs LLM for every topic + Global sections concurrently.
        3. MERGER: Stitches results into final JSON.
        """
        _, _, _, planner_bone_sys = get_prompts()
        
        # --- PHASE 1: THE BONE (PLANNER) ---
        msg = "Phase 1: Generating Lesson Blueprint (Parallel Mode)..."
        logger.info(f"DirectorGenerator: {msg}")
        if update_status_callback:
            update_status_callback("planner", msg)

        # No limit for Planner - let the LLM see the full document
        planner_user = f"Subject: {subject}\nGrade: {grade}\n\nDOCUMENT CONTENT:\n{markdown_content}"
        
        try:
            # Run Planner (Synchronous here, block main thread for 30s is fine)
            planner_response, planner_usage = call_openrouter_llm(planner_bone_sys, planner_user, self.config)
            blueprint = extract_json_from_response(planner_response)
        except Exception as e:
            logger.error(f"Planner failed: {e}. Falling back to sequential.")
            return self.generate_presentation_loop(markdown_content, subject, grade, images_list, update_status_callback)

        topics = blueprint.get("topics", [])
        global_context = blueprint.get("global_context", {})
        logger.info(f"DirectorGenerator: Planner identified {len(topics)} topics.")

        # --- PHASE 2: PARALLEL EXECUTION ---
        start_time = time.time()
        tasks = []

        # Task A: Global Worker (Intro/Summary/Recap/Memory)
        tasks.append(self._generate_globals_worker(global_context, subject, grade))
        
        # Task B: Topic Workers
        for i, topic in enumerate(topics):
            # Extract content strictly
            topic_md = self._extract_topic_markdown(markdown_content, topic.get("start_phrase"), topic.get("end_phrase"))
            tasks.append(self._generate_topic_worker(i, topic, topic_md, subject, grade, images_list))

        if update_status_callback:
            update_status_callback("director_loop", f"Phase 2: Blasting {len(tasks)} Parallel Workers...")

        # EXECUTE ALL
        results = await asyncio.gather(*tasks)
        
        logger.info(f"DirectorGenerator: Parallel processing finished in {time.time() - start_time:.2f}s")
        
        # --- PHASE 3: THE MERGER ---
        output_globals = results[0] # First result is Globals
        topic_sections = results[1:] # Rest are topics
        
        final_presentation = {
            "presentation_title": blueprint.get("presentation_title", "Lesson"),
            "sections": [],
            "metadata": {
                "generated_by": "v2.5-parallel-director",
                "doc_length": len(markdown_content),
                "planner_id": "bone-planner"
            }
        }
        
        # 1. Intro
        if output_globals.get("intro"):
            final_presentation["sections"].append(output_globals["intro"])
            
        # 2. Topics (Sorted by original index)
        # Verify order (asyncio.gather preserves order of tasks)
        for sec_list in topic_sections:
            if sec_list:
                final_presentation["sections"].extend(sec_list)
                
        # 3. Summary/Memory/Recap
        if output_globals.get("summary"):
             final_presentation["sections"].append(output_globals["summary"])
        if output_globals.get("memory"):
             final_presentation["sections"].append(output_globals["memory"])
        if output_globals.get("recap"):
             final_presentation["sections"].append(output_globals["recap"])
             
        return final_presentation

    async def _generate_topic_worker(self, index, topic_meta, topic_md, subject, grade, images_list):
        """Async worker for a single topic."""
        title = topic_meta.get("heading", f"Topic {index+1}")
        logger.info(f"[Worker {index}] Starting: {title}")
        
        # Wrap sync LLM call in thread
        try:
             # We use the existing generate_presentation method but run it in thread
             # to avoid blocking the event loop
             data = await asyncio.to_thread(
                 self.generate_presentation, 
                 topic_md, 
                 subject, 
                 grade, 
                 images_list,
                 title, # topic_heading
                 self.topic_prompt # Use specialized topic prompt
             )
             logger.info(f"[Worker {index}] Finished: {title}")
             return data.get("sections", [])
        except Exception as e:
            logger.error(f"[Worker {index}] Failed: {e}")
            return []

    async def _generate_globals_worker(self, context, subject, grade):
        """
        Async worker to generate Intro, Summary, Memory, Recap.
        For V1, we simply construct them from the planner context to save tokens/time.
        The Planner already gave us the bullets and scripts in 'global_context'.
        """
        logger.info("[Global Worker] Constructing global sections...")
        await asyncio.sleep(0.1) # Yield
        
        sections = {}
        
        # Intro
        intro_text = context.get("intro_narration_context", "Welcome to this lesson.")
        # If it's just context, we might want to expand it, but for V2.5 speed, we use it directly 
        # or assume the Planner gave us good text. 
        # ideally we would run an LLM call here, but let's trust the "Bone" planner for now 
        # or do a quick LLM call if needed. For now, Direct Construction.
        
        sections["intro"] = {
            "section_type": "intro",
            "title": "Introduction",
            "renderer": "none",
            "narration": {"segments": [{"segment_id": "intro_1", "text": intro_text}]}
        }
        
        # Summary
        summ_points = context.get("summary_points", [])
        if summ_points:
             sections["summary"] = {
                "section_type": "summary",
                "title": "Summary",
                "renderer": "none",
                "visual_beats": [{"visual_type": "bullet_list", "display_text": "\n".join(f"• {p}" for p in summ_points)}],
                "narration": {"segments": [{"segment_id": "summ_1", "text": "Let's summarize key points."}]}
            }
            
        # Memory
        mem = context.get("memory_flashcards", [])
        if mem:
            mem_segments = []
            # Intro segment
            mem_segments.append({
                "segment_id": "mem_intro", 
                "text": f"Let's review {len(mem)} key concepts to lock in your memory.",
                "display_directives": {"text_layer": "show", "visual_layer": "hide", "avatar_layer": "show"}
            })
            
            # Per-card segments
            intros = ["First up", "Next", "Another key one", "And finally"]
            
            for i, card in enumerate(mem):
                front = card.get("front", "Concept")
                back = card.get("back", "Definition")
                
                # Pick a catchy intro phrase (rotate if more cards than phrases)
                intro_phrase = intros[min(i, len(intros)-1)]
                if i == 0: intro_phrase = "First up"
                
                # Create a catchy, conversational script
                # "First up, [Front]? ... [Back]"
                # The 'back' usually contains the Mnemonic ("Remember: ...") so we let it shine.
                script = f"{intro_phrase}, {front}... {back}"
                
                mem_segments.append({
                    "segment_id": f"mem_card_{i+1}",
                    "text": script,
                    "display_directives": {
                        "text_layer": "show", 
                        "visual_layer": "hide", 
                        "avatar_layer": "show", 
                        "action_type": "flip_card",
                        "card_index": i
                    }
                })

            sections["memory"] = {
                "section_type": "memory",
                "title": "Flashcards",
                "flashcards": mem,
                "narration": {"segments": mem_segments}
            }
        recap = context.get("recap_scenes", [])
        if recap:
             sections["recap"] = {
                "section_type": "recap",
                "title": "Visual Recap",
                "renderer": "video",
                "video_prompts": [{"segment_id": f"rec_{i}", "prompt": r, "duration_hint": 10} for i,r in enumerate(recap[:5])]
            }
            
        logger.info("[Global Worker] Finished.")
        return sections

def generate_director_presentation(
    markdown_content: str,
    subject: str = "Science",
    grade: str = "Grade 10",
    images_list: str = "None",
    config: Optional[GeneratorConfig] = None,
    update_status_callback=None
) -> dict:
    """Entry point for pipeline integration."""
    generator = DirectorGenerator(config)
    # Switch to Parallel Generator for V2.5
    return asyncio.run(generator.generate_presentation_parallel(markdown_content, subject, grade, images_list, update_status_callback))
