import os
import logging
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict
from core.unified_content_generator import GeneratorConfig, extract_json_from_response, call_openrouter_llm, normalize_output
from core.utils.smart_partitioner import SmartPartitioner
from core.tts_duration import update_durations_simplified

logger = logging.getLogger(__name__)

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
            
        # 2. Content Sections (Order matters - logic preserves chunk order)
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
                
        # 3. Global Footer
        for key in ["summary", "memory", "recap"]:
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
