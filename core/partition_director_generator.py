import os
import logging
import asyncio
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict
from core.unified_content_generator import GeneratorConfig, extract_json_from_response, call_openrouter_llm, normalize_output
from core.utils.smart_partitioner import SmartPartitioner
from core.tts_duration import update_durations_simplified

logger = logging.getLogger(__name__)


def inject_missing_image_ids(sections: List[Dict], images_list: str, source_content: str) -> int:
    """
    Pipeline-level fix: Scan visual_beats for diagram/image types with null image_id
    and inject the correct image_id based on markdown_pointer matching.
    
    Returns: Number of image_ids injected
    """
    injected_count = 0
    
    # Parse images_list (could be JSON string, comma-separated string, or list)
    available_images = []
    if images_list and images_list != "None":
        if isinstance(images_list, list):
            available_images = images_list
        elif isinstance(images_list, dict):
            available_images = images_list
        elif isinstance(images_list, str):
            # Try JSON first
            try:
                available_images = json.loads(images_list)
            except json.JSONDecodeError:
                # Fallback: Comma-separated string of filenames
                available_images = [img.strip() for img in images_list.split(',') if img.strip()]
                logger.info(f"[ImageInjection] Parsed {len(available_images)} images from comma-separated string")
    
    if not available_images:
        logger.info("[ImageInjection] No images available to inject")
        return 0
    
    # Extract image references from source markdown: ![alt](filename.jpg)
    image_refs_in_source = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', source_content)
    # Create map: {filename: alt_text, ...}
    source_image_map = {ref[1]: ref[0] for ref in image_refs_in_source}
    
    logger.info(f"[ImageInjection] Found {len(source_image_map)} image refs in source, {len(available_images)} available images")
    
    for section in sections:
        visual_beats = section.get("visual_beats", [])
        for beat in visual_beats:
            visual_type = beat.get("visual_type", "")
            image_id = beat.get("image_id")
            
            # Only process diagram/image types with no image_id
            if visual_type in ["diagram", "image"] and not image_id:
                # Try to match based on markdown_pointer
                pointer = beat.get("markdown_pointer", {})
                start_phrase = pointer.get("start_phrase", "")
                
                # Strategy 1: Check if start_phrase contains an image reference
                matched_image = None
                for img_filename in source_image_map.keys():
                    if img_filename in start_phrase:
                        matched_image = img_filename
                        break
                
                # Strategy 2: Find image whose alt text matches pointer content
                if not matched_image:
                    for img_filename, alt_text in source_image_map.items():
                        if alt_text and len(alt_text) > 10:  # Skip empty/short alt texts
                            # Check if alt text keywords appear in source near pointer
                            if any(word.lower() in start_phrase.lower() for word in alt_text.split()[:3]):
                                matched_image = img_filename
                                break
                
                # Strategy 3: Check available_images list directly
                if not matched_image and isinstance(available_images, dict):
                    for key, info in available_images.items():
                        filename = info.get("filename", "") if isinstance(info, dict) else str(info)
                        alt = info.get("alt_text", "") if isinstance(info, dict) else ""
                        if alt and any(word.lower() in start_phrase.lower() for word in alt.split()[:3]):
                            matched_image = filename
                            break
                
                # Strategy 4: Proximity Check (Look for images near the pointer in source content)
                if not matched_image and source_content:
                    # Find start_phrase location
                    idx = source_content.find(start_phrase)
                    if idx != -1:
                        # Define scan window (e.g., +/- 500 chars)
                        window_start = max(0, idx - 500)
                        window_end = min(len(source_content), idx + 1000)
                        window_text = source_content[window_start:window_end]
                        
                        # Find images in this window
                        nearby_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', window_text)
                        if nearby_images:
                            # Use the first found image in proximity
                            matched_image = nearby_images[0][1]
                            logger.info(f"[ImageInjection] Strategy 4 (Proximity) found '{matched_image}' near pointer")

                # Strategy 5: Single Image Fallback (If only 1 image provided, use it!)
                if not matched_image:
                     # Check if available_images has exactly 1 entry
                     if isinstance(available_images, list) and len(available_images) == 1:
                         # Check if this image looks like a diagram or relevant asset (simple heuristic)
                         matched_image = available_images[0]
                         logger.info(f"[ImageInjection] Strategy 5 (Fallback) used single available image '{matched_image}'")
                     elif isinstance(available_images, dict) and len(available_images) == 1:
                         key = list(available_images.keys())[0]
                         val = available_images[key]
                         matched_image = val.get("filename", str(val)) if isinstance(val, dict) else str(val)
                         logger.info(f"[ImageInjection] Strategy 5 (Fallback) used single available image '{matched_image}'")

                if matched_image:
                    beat["image_id"] = matched_image
                    injected_count += 1
                    logger.info(f"[ImageInjection] Injected image_id '{matched_image}' for beat {beat.get('beat_id')}")
                else:
                    logger.warning(f"[ImageInjection] Could not find matching image for beat {beat.get('beat_id')} (visual_type={visual_type})")
    
    logger.info(f"[ImageInjection] Total injected: {injected_count} image_ids")
    return injected_count



class PartitionDirectorGenerator:
    """
    Phase 7 Architecture: "Partition & Conquer".
    1. Physically partitions MD into chunks.
    2. Runs Global Worker on Full Doc.
    3. Runs Parallel Topic Workers on Chunks (Context + Target).
    """
    
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        self.partitioner = SmartPartitioner(self.config)
        
        # Load Prompts (We will use inline prompts or load from file if complex)
        self.global_system = "You are the Global Director. Output JSON with Intro, Summary, Memory, Recap, Quiz."
        self.content_system = "You are the Content Director. Visualize the TARGET TEXT using the Context."

    async def generate_presentation_parallel__REMOVED_ASYNC(self):
         pass

    def generate_presentation_partitioned(
        self,
        markdown_content: str,
        subject: str = "Science",
        grade: str = "Grade 10",
        images_list: str = "None",
        update_status_callback=None,
        generation_scope: str = "full" # New: "full", "global", "content"
    ) -> dict:
        
        # A. PARTITIONING (Skip if global-only)
        chunks = []
        if generation_scope in ["full", "content"]:
            if generation_scope == "content":
                # Treat the whole input as one single chunk (Manual Mode)
                chunks = [{"title": "Target Content", "content": markdown_content}]
                logger.info("Manual Scope: Treating input as a single target chunk.")
            else:
                msg = "Phase 1: Intelligent Partitioning..."
                logger.info(msg)
                if update_status_callback: update_status_callback("partitioning", msg)
                chunks = self.partitioner.partition_markdown(markdown_content, subject, grade)
                logger.info(f"Partitioned into {len(chunks)} physical chunks.")

        # B & C: PARALLEL EXECUTION (Global + Content)
        global_results = {}
        content_results = []
        
        msg = f"Phase 2 & 3: Generating Global and {len(chunks)} Content Chunks in Parallel..."
        logger.info(msg)
        if update_status_callback: update_status_callback("llm_generation", msg)

        max_workers = min(len(chunks) + 1, 12)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 1. Submit Global Worker (if needed)
            global_future = None
            if generation_scope in ["full", "global"]:
                global_future = executor.submit(self._run_global_worker, markdown_content, subject, grade)
            
            # 2. Submit Content Workers (if needed)
            future_to_index = {}
            if generation_scope in ["full", "content"]:
                for i, chunk in enumerate(chunks):
                    f = executor.submit(
                        self._run_content_worker_sync, 
                        i, 
                        chunk, 
                        markdown_content if generation_scope == "full" else "", 
                        subject, 
                        grade, 
                        images_list
                    )
                    future_to_index[f] = i
                
                content_results = [None] * len(chunks)

            # 3. Collect Results
            if global_future:
                try:
                    global_results = global_future.result()
                except Exception as e:
                    logger.error(f"Global Worker failed: {e}")
                    global_results = {}

            if future_to_index:
                for future in as_completed(future_to_index):
                    i = future_to_index[future]
                    try:
                        content_results[i] = future.result()
                    except Exception as e:
                        logger.error(f"Worker {i} generated an exception: {e}")
                        content_results[i] = []
        
        # D. STITCHING
        msg = "Phase 4: Stitching Presentation..."
        logger.info(msg)
        
        final_presentation = {
            "presentation_title": global_results.get("presentation_title", f"{subject} Lesson"),
            "sections": [],
            "metadata": {
                "generated_by": "v2.5-partition-director",
                "doc_length": len(markdown_content),
                "chunks": len(chunks),
                "llm_calls": 1 + len(chunks) + (1 if generation_scope in ["full", "global"] else 0),
                "generation_scope": generation_scope
            }
        }
        
        # 1. Intro
        if global_results.get("intro"):
            intro = global_results["intro"]
            intro["section_id"] = 1
            final_presentation["sections"].append(intro)
        
        # 2. Summary (V2.5 Bible: Summary comes BEFORE Content)
        if global_results.get("summary"):
            summary = global_results["summary"]
            summary["section_id"] = len(final_presentation["sections"]) + 1
            final_presentation["sections"].append(summary)
            
        # 3. Content Sections (Order matters - logic preserves chunk order)
        current_id = len(final_presentation["sections"]) + 1
        for chunk_res in content_results:
            if chunk_res:
                for sec in chunk_res:
                    sec["section_id"] = current_id
                    current_id += 1
                    # Ensure visual_beats is not empty for player compatibility
                    if not sec.get("visual_beats"):
                        sec["visual_beats"] = []
                final_presentation["sections"].extend(chunk_res)
        
        # 3.5 IMAGE INJECTION FIX (Pipeline-level)
        # Scan for visual_type=diagram/image with null image_id and inject correct references
        content_sections = [s for s in final_presentation["sections"] if s.get("section_type") in ["content", "example"]]
        if content_sections:
            injected = inject_missing_image_ids(content_sections, images_list, markdown_content)
            if injected > 0:
                msg = f"Phase 4.5: Injected {injected} missing image_ids"
                logger.info(msg)
                if update_status_callback: update_status_callback("image_injection", msg)
                
        # 4. Memory and Recap (Global Footer)
        for key in ["memory", "recap"]:
            if global_results.get(key):
                sec = global_results[key]
                sec["section_id"] = current_id
                current_id += 1
                final_presentation["sections"].append(sec)
                
        return final_presentation

    def _run_global_worker(self, full_md, subject, grade) -> dict:
        """Generates Intro, Summary, Memory, Recap ONLY."""
        # Use existing 'director_global_prompt.txt' if available, or inline.
        # Strict Load of Global Prompt
        with open("core/prompts/director_global_prompt.txt", "r", encoding="utf-8") as f:
            sys_p = f.read()
             
        usr_p = f"Subject: {subject}\nGrade: {grade}\nCONTENT:\n{full_md}" # Full context - let the LLM see everything
        from core.validators.v25_validator import V25Validator

        retries = 0
        max_retries = 3
        current_prompt = usr_p
        
        while retries < max_retries:
            try:
                r, _ = call_openrouter_llm(sys_p, current_prompt, self.config)
                data = extract_json_from_response(r)
                
                # VALIDATION GATE (GLOBAL)
                # VALIDATION GATE (GLOBAL)
                print(f"\n[PHASE 1 DEBUG] Global Worker Response ({subject}, {grade}):")
                print(json.dumps(data, indent=2))
                print(f"[PHASE 1 DEBUG] --------------------------------------------------\n")
                
                errors = V25Validator.validate_global_response(data)
                
                if not errors:
                    return data
                    
                # Validation Failed
                logger.warning(f"Global Worker Validation Failed (Attempt {retries+1}): {errors}")
                
                # Feedback Loop
                error_msg = "\n- ".join(errors)
                current_prompt += (
                    f"\n\n[SYSTEM: PREVIOUS ATTEMPT REJECTED]\n"
                    f"Your previous JSON output was invalid for the following reasons:\n- {error_msg}\n"
                    f"Please FIX these errors and regenerate the JSON strictly following the schema."
                )
                retries += 1
            except Exception as e:
                logger.error(f"Global Worker Exception (Attempt {retries+1}): {e}")
                retries += 1
                
        logger.error("Global Worker failed all validation attempts. Returning empty dict.")
        return {}

    def _run_content_worker_sync(self, index, chunk, full_context, subject, grade, images_list):
        """
        Sync Worker for Content chunks (for ThreadPoolExecutor).
        """
        try:
            # Load specialized prompt
            # Load specialized prompt (STRICT LOADING - NO FALLBACK)
            with open("core/prompts/director_partition_prompt.txt", "r", encoding="utf-8") as f:
                sys_p = f.read()
            
            usr_p = (
                f"SUBJECT: {subject}\n"
                f"Target Chunk Title: {chunk.get('title')}\n\n"
                f"=== FULL DOCUMENT CONTEXT (Read Only) ===\n{full_context}\n\n"
                f"=== AVAILABLE IMAGES (Usage Mandatory if relevant) ===\n{json.dumps(images_list, indent=2)}\n\n"
                f"=== TARGET CHUNK (VISUALIZE THIS) ===\n{chunk.get('content')}\n\n"
                f"Instructions: Create slides for the TARGET CHUNK only. Use images from the list above."
            )
            
            # Run LLM (Sync) with Validation Retry Loop
            from core.validators.v25_validator import V25Validator
            
            retries = 0
            max_retries = 3
            current_prompt = usr_p
            
            while retries < max_retries:
                try:
                    response, _ = call_openrouter_llm(sys_p, current_prompt, self.config)
                    
                    # [DEBUG] Save Raw LLM Response to verify if it's String or Dict
                    try:
                        debug_file = f"debug_llm_chunk_{index}_attempt_{retries}.txt"
                        with open(debug_file, "w", encoding="utf-8") as f:
                            f.write(response)
                        logger.info(f"Saved raw LLM response to {debug_file}")
                    except Exception as e:
                        logger.warning(f"Failed to save debug LLM response: {e}")
                    data = extract_json_from_response(response)
                    
                    # VALIDATION GATE (PARTITION)
                    # VALIDATION GATE (PARTITION)
                    print(f"\n[PHASE 1 DEBUG] Content Worker Response (Chunk {index}):")
                    print(json.dumps(data, indent=2))
                    print(f"[PHASE 1 DEBUG] --------------------------------------------------\n")
                    
                    # Validation with Source Text for Pointer Check
                    errors = V25Validator.validate_content_chunk(data, source_text=chunk.get("content", ""))
                    
                    if not errors:
                        # Success!
                        sections_result = data.get("sections", [])
                        # INJECT CONTENT FIDELITY (Restore source text)
                        if sections_result and chunk.get("content"):
                            # Assign full chunk content to first section to ensure "content" field is populated
                            # This overrides any empty/missing content from LLM
                            sections_result[0]["content"] = chunk.get("content")
                            # If there are multiple sections, we only map to first for now (1:1 chunk mapping assumption)
                            
                        return sections_result
                    
                    # Validation Failed
                    logger.warning(f"Worker {index} Validation Failed (Attempt {retries+1}/{max_retries}): {errors}")
                    
                    # Feedback Loop
                    error_msg = "\n- ".join(errors)
                    current_prompt += (
                        f"\n\n[SYSTEM: PREVIOUS ATTEMPT REJECTED]\n"
                        f"Your previous JSON output was invalid for the following reasons:\n- {error_msg}\n"
                        f"Please FIX these errors and regenerate the JSON strictly following the schema."
                    )
                    retries += 1
                    
                except Exception as e:
                    logger.error(f"Worker {index} Exception (Attempt {retries+1}): {e}")
                    retries += 1
                    
            # If all retries fail, log and return empty (or partial data)
            logger.error(f"Worker {index} failed all {max_retries} attempts.")
            return []
            
        except Exception as e:
            logger.error(f"Partition Worker {index} failed outer: {e}")
            return []

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
    # Revert to standard loop (Sync) until ThreadPool implemented in V2
    # partition_director_generator is the class above, DirectorGenerator is legacy
    # The pipeline calls generate_presentation_partitioned directly on PartitionDirectorGenerator instance
    # IF this function is intended to call PartitionDirectorGenerator:
    
    # Correction: The pipeline uses PartitionDirectorGenerator directly.
    # This helper function seems to be for DirectorGenerator (legacy/loop).
    # Since we are modifying PartitionDirectorGenerator in this file, we don't need to change this function
    # unless it's used by the pipeline.
    
    # Wait, the pipeline calls `generate_presentation_partitioned` directly if using partition mode.
    # If using 'director' mode (legacy), it calls this. 
    # Let's leave this as is (sync loop) or upgrade it if needed. 
    # For now, we are fixing PartitionDirectorGenerator.generate_presentation_partitioned.
    
    return generator.generate_presentation_loop(markdown_content, subject, grade, images_list, update_status_callback)
