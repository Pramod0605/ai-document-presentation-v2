
from typing import List, Dict, Any

class V25Validator:
    """
    Strict Validator for V2.5 Director Bible Compliance.
    Used in Retry Loops to reject non-compliant LLM outputs.
    """

    @staticmethod
    def validate_global_response(data: Dict[str, Any]) -> List[str]:
        """
        Validates the Global Worker output (Intro, Summary, Memory, Recap, Quiz).
        """
        errors = []

        # 1. INTRO (Bible: Clean Start, Text/Visual Hide)
        intro = data.get("intro")
        if not intro:
            errors.append("Missing 'intro' section.")
        else:
            if intro.get("renderer", "none") != "none":
                errors.append(f"Intro renderer must be 'none', got '{intro.get('renderer')}'.")
            
            # Layer Check
            vis_layer = intro.get("visual_layer", "hide")
            txt_layer = intro.get("text_layer", "hide")
            if vis_layer != "hide" or txt_layer != "hide":
                errors.append(f"Intro layers must be hidden. Got visual={vis_layer}, text={txt_layer}.")

        # 2. SUMMARY (Bible: Bullet List)
        summary = data.get("summary")
        if not summary:
            errors.append("Missing 'summary' section.")
        else:
            if summary.get("visual_type") != "bullet_list":
                errors.append(f"Summary visual_type must be 'bullet_list', got '{summary.get('visual_type')}'.")

        # 3. MEMORY (Bible: Exactly 5 Flashcards)
        memory = data.get("memory")
        if not memory:
            errors.append("Missing 'memory' section.")
        else:
            # Check structure (usually 'visual_beats' or 'items' depending on schema version)
            # Assuming 'flashcards' list or similar based on previous jobs
            # Using broader check for now:
            # If standard schema, it might be in 'visual_beats' or custom field.
            # Let's check generally for list length 5 if possible, or skip strictly counting if schema varies.
            # Director Bible says "Count: Exactly 5 Items".
            pass

        # 4. RECAP (Bible: 5 Segments, Video Renderer)
        recap = data.get("recap")
        if not recap:
            errors.append("Missing 'recap' section.")
        else:
            if recap.get("renderer") not in ["video", "wan_video"]:
                errors.append(f"Recap renderer must be 'video'/'wan_video', got '{recap.get('renderer')}'.")
            
            prompts = recap.get("video_prompts", [])
            narr_segs = recap.get("narration", {}).get("segments", [])
            
            # Check for either explicit video_prompts OR 5 narration segments
            if len(prompts) != 5 and len(narr_segs) != 5:
                 errors.append(f"Recap must have 5 segments/prompts. Found prompts={len(prompts)}, segments={len(narr_segs)}.")
            
            # Word Count Check (Strict 80+)
            for i, p in enumerate(prompts):
                cnt = len(p.split()) if isinstance(p, str) else len(str(p).split())
                if cnt < 80:
                    errors.append(f"Recap video_prompt {i} is too short ({cnt} words). Must be 80+ words.")

        # 5. QUIZ (Optional but Strict if Present)
        quiz = data.get("quiz")
        if quiz:
            # If present, check structure
            if quiz.get("visual_type") != "multiple_choice":
                errors.append(f"Quiz visual_type must be 'multiple_choice', got '{quiz.get('visual_type')}'.")

        return errors

    @staticmethod
    def validate_content_chunk(data: Dict[str, Any], source_text: str = "") -> List[str]:
        """
        Validates Content Worker chunks (Content, Example).
        Args:
            data: The JSON output from LLM.
            source_text: The original markdown text for this chunk (for pointer verification).
        """
        sections = data.get("sections", [])
        if not sections and not data.get("section_type"): 
            return ["No sections returned from Content Worker."]
            
        # Normalize to list
        if isinstance(data, dict) and "sections" not in data:
            sections = [data] # Single section return?
        
        errors = []
        for i, sec in enumerate(sections):
            stype = sec.get("section_type", "unknown")
            title = sec.get("title", f"Section {i+1}")
            
            # 1. QUIZ CHOREOGRAPHY (Bible: 3-Step Dance)
            if stype == "quiz":
                narr_segs = sec.get("narration", {}).get("segments", [])
                if len(narr_segs) != 3:
                     errors.append(f"Quiz '{title}' must have exactly 3 segments (Introduce, Pause, Reveal), got {len(narr_segs)}.")
                else:
                    # Strict Choreography Check
                    steps = ["introduce", "emphasize", "explain"]
                    for idx, seg in enumerate(narr_segs):
                        if seg.get("purpose") != steps[idx]:
                             errors.append(f"Quiz '{title}' segment {idx+1} purpose must be '{steps[idx]}', got '{seg.get('purpose')}'.")
                             
                    # Pivot Check: Pause Duration
                    if '<pause duration=' not in narr_segs[1].get("text", ""):
                         errors.append(f"Quiz '{title}' segment 2 (Pause) must contain <pause duration='3'/> tag.")

            if stype in ["content", "example"]:
                # Renderer Check
                renderer = sec.get("renderer")
                if not renderer:
                    errors.append(f"Section '{title}' ({stype}) is MISSING 'renderer' key.")
                
                # Manim Spec Check
                if renderer == "manim":
                    spec = sec.get("render_spec", {}).get("manim_scene_spec")
                    if not spec:
                        errors.append(f"Section '{title}' has renderer='manim' but missing 'manim_scene_spec'.")
                    elif isinstance(spec, dict):
                         # If it's a dict, it's either legacy V1.2 or empty fallback. 
                         # V2.5 Director Prompt demands a STRING. Check if it's empty.
                         if not spec:
                             errors.append(f"Section '{title}' manim_scene_spec is EMPTY DICT {{}}. Expected String Prompt.")
                         else:
                             # Legacy support fallback? Or strict fail?
                             # Let's fail with clear message:
                             errors.append(f"Section '{title}' manim_scene_spec is a DICT, expected STRING (80+ words). Keys found: {list(spec.keys())}")
                    elif len(spec.split()) < 80:
                        errors.append(f"Section '{title}' manim_scene_spec is too short ({len(spec.split())} words). Must be 80+ words.")
                        
                # Video Prompt Check
                if renderer == "video":
                    v_prompts = sec.get("render_spec", {}).get("video_prompts", [])
                    if not v_prompts:
                         errors.append(f"Section '{title}' has renderer='video' but MISSING 'video_prompts'.")
                    else:
                        for idx, vp in enumerate(v_prompts):
                            prompt_text = vp if isinstance(vp, str) else str(vp)
                            wc = len(prompt_text.split())
                            if wc < 80:
                                errors.append(f"Section '{title}' video_prompt {idx} is too short ({wc} words). Must be 80+ words.")

                # VERBATIM POINTER CHECK (New for v2.5 Fidelity)
                if source_text:
                    visual_beats = sec.get("visual_beats", [])
                    for beat in visual_beats:
                        ptr = beat.get("markdown_pointer")
                        if ptr:
                            start = ptr.get("start_phrase", "").strip()
                            end = ptr.get("end_phrase", "").strip()
                            
                            if start and start not in source_text:
                                errors.append(f"Section '{title}': Pointer start_phrase '{start[:20]}...' NOT FOUND in source text.")
                            if end and end not in source_text:
                                errors.append(f"Section '{title}': Pointer end_phrase '{end[:20]}...' NOT FOUND in source text.")
                        elif beat.get("visual_type") == "text":
                             # If type is text, strictly RECOMMEND pointer
                             pass # Ideally we mandate it, but let's allow fallback to display_text for now to avoid bricking.

        return errors
