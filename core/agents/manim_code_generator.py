"""
Manim Code Generator Agent (REQ-060 through REQ-068)

Uses Claude Sonnet 3.5 via OpenRouter to generate Python code for Manim animations.
Output is raw Python code for construct(self) method body, not JSON spec.
"""
import re
import os
from typing import Dict, Any, List, Tuple, Optional

CLAUDE_SONNET_3_5 = "anthropic/claude-3.5-sonnet"

class ManimCodeGenerator:
    """
    Manim Code Generator - Creates Python code for Manim animations.
    
    Input: section data with TTS timing and visual descriptions
    Output: Python code string for construct(self) method body
    """
    
    name = "ManimCodeGenerator"
    model = CLAUDE_SONNET_3_5
    temperature = 0.3
    max_tokens = 8000
    max_retries = 3
    
    def __init__(self, openrouter_api_key: Optional[str] = None, **kwargs):
        self.api_key = openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
        self.prompts_dir = kwargs.get("prompts_dir", "core/prompts")
        self._system_prompt: Optional[str] = None
        self._user_template: Optional[str] = None
        
    def _load_prompts(self):
        """Load system prompt and user template from files."""
        if self._system_prompt is None:
            system_path = os.path.join(self.prompts_dir, "manim_system_prompt.txt")
            with open(system_path, "r") as f:
                self._system_prompt = f.read()
        
        if self._user_template is None:
            template_path = os.path.join(self.prompts_dir, "manim_user_prompt_template.txt")
            with open(template_path, "r") as f:
                self._user_template = f.read()
    
    def _build_user_prompt(self, section_data: Dict[str, Any]) -> str:
        """Build user prompt from template and section data."""
        self._load_prompts()
        
        narration_segments_text = self._format_segments(section_data.get("narration_segments", []))
        visual_description = section_data.get("visual_description", "Create appropriate visualization for the topic")
        formulas = ", ".join(section_data.get("formulas", [])) or "None"
        key_terms = ", ".join(section_data.get("key_terms", [])) or "None"
        total_duration = sum(seg.get("duration", 5.0) for seg in section_data.get("narration_segments", []))
        special_requirements = section_data.get("special_requirements", "None")
        
        if section_data.get("previous_errors"):
            special_requirements += f"\n\nFIX THESE ISSUES FROM PREVIOUS ATTEMPT:\n{section_data['previous_errors']}"
        
        assert self._user_template is not None, "User template not loaded"
        return self._user_template.format(
            section_title=section_data.get("section_title", "Educational Section"),
            narration_segments=narration_segments_text,
            visual_description=visual_description,
            formulas=formulas,
            key_terms=key_terms,
            total_duration=f"{total_duration:.1f}",
            special_requirements=special_requirements
        )
    
    def _format_segments(self, segments: List[Dict]) -> str:
        """Format narration segments for the prompt."""
        lines = []
        current_time = 0.0
        
        for i, seg in enumerate(segments, 1):
            duration = seg.get("duration", 5.0)
            text = seg.get("text", "")
            visual = seg.get("visual", "")
            end_time = current_time + duration
            
            lines.append(f"Segment {i} ({current_time:.1f}s - {end_time:.1f}s, duration {duration:.1f}s):")
            lines.append(f"  Narration: \"{text}\"")
            if visual:
                lines.append(f"  Visual: {visual}")
            lines.append("")
            
            current_time = end_time
        
        return "\n".join(lines)
    
    def generate(self, section_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Generate Manim code for a section with auto-retry on validation failure.
        
        Args:
            section_data: Dict containing section_title, narration_segments, visual_description, etc.
            
        Returns:
            Tuple of (python_code: str, errors: List[str])
            If successful, errors will be empty.
        """
        import requests
        
        self._load_prompts()
        
        code = ""
        errors: List[str] = []
        
        for attempt in range(self.max_retries):
            user_prompt = self._build_user_prompt(section_data)
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://replit.com",
                    "X-Title": "AI Education Manim Generator"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                },
                timeout=120
            )
            
            if response.status_code != 200:
                return "", [f"API error: {response.status_code} - {response.text}"]
            
            result = response.json()
            code = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            code = self._extract_python_code(code)
            
            errors = self.validate_code(code, section_data)
            
            if not errors:
                return code, []
            
            section_data = section_data.copy()
            section_data["previous_errors"] = "\n".join(errors)
        
        return code if code else "", errors if errors else ["Max retries exceeded with no output"]
    
    def _extract_python_code(self, response: str) -> str:
        """Extract Python code from LLM response, removing markdown if present."""
        code = response.strip()
        
        if "```python" in code:
            match = re.search(r"```python\s*(.*?)\s*```", code, re.DOTALL)
            if match:
                code = match.group(1)
        elif "```" in code:
            match = re.search(r"```\s*(.*?)\s*```", code, re.DOTALL)
            if match:
                code = match.group(1)
        
        return code.strip()
    
    def validate_code(self, code: str, section_data: Dict[str, Any]) -> List[str]:
        """
        Validate generated Manim code.
        
        Checks:
        1. Syntax validity (compile test)
        2. No Dot() placeholders
        3. Timing matches segment durations (±0.5s tolerance)
        4. No variable overwrites (e.g., axes = axes.plot())
        """
        errors = []
        
        errors.extend(self._check_syntax(code))
        
        errors.extend(self._check_placeholders(code))
        
        errors.extend(self._check_timing(code, section_data))
        
        errors.extend(self._check_variable_overwrites(code))
        
        return errors
    
    def _check_syntax(self, code: str) -> List[str]:
        """Check Python syntax validity."""
        try:
            compile(code, "<string>", "exec")
            return []
        except SyntaxError as e:
            return [f"Syntax error at line {e.lineno}: {e.msg}"]
    
    def _check_placeholders(self, code: str) -> List[str]:
        """Check for Dot() placeholder usage."""
        errors = []
        
        dot_pattern = re.compile(r'\bDot\s*\(\s*\)')
        
        for i, line in enumerate(code.split("\n"), 1):
            if dot_pattern.search(line):
                errors.append(f"Line {i}: Dot() placeholder detected - use actual Manim objects instead")
        
        return errors
    
    def _check_timing(self, code: str, section_data: Dict[str, Any]) -> List[str]:
        """Check if animation timing matches narration segments."""
        errors = []
        
        segments = section_data.get("narration_segments", [])
        if not segments:
            return []
        
        total_expected = sum(seg.get("duration", 5.0) for seg in segments)
        
        run_times = re.findall(r'run_time\s*=\s*([\d.]+)', code)
        waits = re.findall(r'self\.wait\s*\(\s*([\d.]+)\s*\)', code)
        
        total_animation = sum(float(t) for t in run_times) + sum(float(w) for w in waits)
        
        tolerance = 0.5 * len(segments)
        
        if abs(total_animation - total_expected) > tolerance:
            errors.append(
                f"Timing mismatch: animation total {total_animation:.1f}s vs expected {total_expected:.1f}s "
                f"(tolerance ±{tolerance:.1f}s)"
            )
        
        return errors
    
    def _check_variable_overwrites(self, code: str) -> List[str]:
        """Check for problematic variable overwrites like 'axes = axes.plot()'."""
        errors = []
        
        overwrite_pattern = re.compile(r'^(\s*)(\w+)\s*=\s*\2\.', re.MULTILINE)
        
        for match in overwrite_pattern.finditer(code):
            var_name = match.group(2)
            if var_name not in ("self",):
                line_num = code[:match.start()].count("\n") + 1
                errors.append(
                    f"Line {line_num}: Variable '{var_name}' overwrites itself - "
                    f"use a different name like '{var_name}_new' or 'new_{var_name}'"
                )
        
        return errors


def build_manim_section_data(
    section: Dict[str, Any],
    narration_segments: List[Dict],
    visual_beats: List[Dict],
    segment_enrichments: List[Dict]
) -> Dict[str, Any]:
    """
    Build the input data structure for ManimCodeGenerator from V1.5 pipeline outputs.
    
    Args:
        section: Section plan from SectionPlanner
        narration_segments: Segments from NarrationWriter + TTS timing update
            Each segment has 'duration_seconds' (from TTS) - this is the authoritative timing
        visual_beats: Visual beats from VisualSpecArtist
        segment_enrichments: Enrichments from VisualSpecArtist
        
    Returns:
        Dict suitable for ManimCodeGenerator.generate()
        
    Note: This function maps 'duration_seconds' to 'duration' for the prompt template,
    as the ManimCodeGenerator expects 'duration' field in segments.
    """
    combined_segments = []
    
    for i, seg in enumerate(narration_segments):
        visual_desc = ""
        
        if i < len(visual_beats):
            visual_desc = visual_beats[i].get("description", "")
        
        if i < len(segment_enrichments):
            enrich = segment_enrichments[i]
            visual_content = enrich.get("visual_content", {})
        
        seg_duration = seg.get("duration_seconds") or seg.get("duration") or 5.0
        
        combined_segments.append({
            "text": seg.get("text", ""),
            "duration": float(seg_duration),
            "visual": visual_desc
        })
    
    all_formulas = []
    all_labels = []
    for enrich in segment_enrichments:
        vc = enrich.get("visual_content", {})
        if vc.get("formula"):
            all_formulas.append(vc["formula"])
        if vc.get("labels"):
            all_labels.extend(vc["labels"])
    
    return {
        "section_title": section.get("title", "Educational Topic"),
        "narration_segments": combined_segments,
        "visual_description": " ".join(vb.get("description", "") for vb in visual_beats),
        "formulas": list(set(filter(None, all_formulas))),
        "key_terms": list(set(all_labels)),
        "special_requirements": ""
    }


def integrate_manim_code_into_section(
    section: Dict[str, Any],
    manim_code: str
) -> Dict[str, Any]:
    """
    Add generated Manim code to a section's render_spec.
    
    This function is called after ManimCodeGenerator.generate() to integrate
    the Python code into the section structure for later rendering.
    
    Args:
        section: The section dictionary (with existing render_spec if any)
        manim_code: The generated Python code for construct() method
        
    Returns:
        Updated section with manim_code added to render_spec
    """
    if not section.get("render_spec"):
        section["render_spec"] = {}
    
    render_spec = section["render_spec"]
    
    if not render_spec.get("manim_scene_spec"):
        render_spec["manim_scene_spec"] = {}
    
    render_spec["manim_scene_spec"]["manim_code"] = manim_code
    render_spec["manim_scene_spec"]["code_type"] = "construct_body"
    
    return section
