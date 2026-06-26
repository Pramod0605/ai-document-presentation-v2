"""
Visual Prompt Enhancer — Phase 2.5 of the V2 Pipeline

Calls GPT-4o (via OpenRouter) to improve image_prompt_start / image_prompt_end /
video_prompt fields for sections that use image-based renderers.

ONLY runs for: image_to_video, image, infographic
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Load system prompt from .txt file ─────────────────────────────────────────
_PROMPT_PATH = (
    Path(__file__).parent.parent / "prompts" / "visual_prompt_enhancer_prompt.txt"
)
try:
    ENHANCER_SYSTEM_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    logger.error(f"[Enhancer] Prompt file not found: {_PROMPT_PATH}")
    ENHANCER_SYSTEM_PROMPT_TEMPLATE = ""

# ── Config ─────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
ENHANCER_MODEL = os.environ.get("ENHANCER_MODEL", "openai/gpt-4o")

ELIGIBLE_RENDERERS = {"image_to_video", "image", "infographic", "video", "wan_video", "wan"}

# ── Cultural Detection ─────────────────────────────────────────────────────────
def detect_cultural_profile(presentation: dict) -> str:
    """Detect if the content is heavily Indian-focused or International."""
    text_corpus = []
    
    # Extract text from sections and narration
    for sec in presentation.get("sections", []):
        text_corpus.append(sec.get("script", ""))
        for seg in sec.get("narration", {}).get("segments", []):
            if isinstance(seg, str):
                text_corpus.append(seg)
            else:
                text_corpus.append(seg.get("text", ""))
    
    # Also check chunks if available
    for chunk in presentation.get("content_chunks", []):
        text_corpus.append(chunk.get("content", ""))
        
    full_text = " ".join(text_corpus).lower()
    
    indian_keywords = [
        "india", "indian", "kerala", "mumbai", "delhi", "bengaluru", "chennai",
        "kpsc", "karnataka", "upsc", "ssc", "bpsc", "uppsc", "ias", "ips", "rupees", "rs."
    ]
    
    hits = sum(1 for kw in indian_keywords if kw in full_text)
    
    if hits >= 2:
        logger.info(f"[Enhancer] Detected INDIAN cultural profile (Hits: {hits})")
        return """═══════════════════════════════════════════════════════════
CULTURAL PROFILE: INDIAN CONTEXT
═══════════════════════════════════════════════════════════
The Director may write recap or story narration with Indian cultural settings
(Kerala village, Hyderabad lab, Assam field, Indian student).

MANDATORY:
- Preserve the Indian cultural setting from narration exactly
- Characters, locations, atmosphere must remain Indian and specific
- DO NOT replace Indian settings with generic Western laboratories or classrooms.

IPS/VP CONSISTENCY:
- If IPS shows "Indian village courtyard" → VP must animate elements IN that courtyard.
- The VP SUBJECT line must name the same location or setting as the IPS.
- The VP MECHANISM must describe motion of objects WITHIN that cultural setting.
"""
    else:
        logger.info(f"[Enhancer] Detected GLOBAL cultural profile (Hits: {hits})")
        return """═══════════════════════════════════════════════════════════
CULTURAL PROFILE: GLOBAL / GENERIC CONTEXT
═══════════════════════════════════════════════════════════
The Director writes narration with a global or generic scientific context.

MANDATORY:
- Preserve the specific environments described in the narration (e.g. modern lab, university classroom, global city).
- Do not introduce unrelated regional cultural elements.
- Keep characters and environments universally recognizable and professional.

IPS/VP CONSISTENCY:
- If IPS shows a "modern biology lab" → VP must animate elements IN that lab.
- The VP SUBJECT line must name the same location or setting as the IPS.
- The VP MECHANISM must describe motion of objects WITHIN that setting.
"""

# ── Quality enforcement helpers ────────────────────────────────────────────────

BANNED_WORDS = [
    "cinematic", "beautiful", "dynamic", "abstract",
    "smooth animation", "flows gracefully", "elegantly",
    "stunning", "dramatic", "seamlessly", "breathtaking",
]
MIN_IMAGE_PROMPT = 100
MIN_VIDEO_PROMPT = 80
MAX_REPAIR_ATTEMPTS = 3

def _wc(text: str) -> int:
    return len(text.split()) if text else 0

def _banned_in(text: str) -> list:
    return [w for w in BANNED_WORDS if w.lower() in text.lower()]

def _strip_hex_from_vp(text: str) -> str:
    cleaned = re.sub(r"#[0-9a-fA-F]{6}\b", "", text)
    return re.sub(r"  +", " ", cleaned).strip()

def _beat_issues(b: dict) -> list:
    issues = []
    ips = b.get("image_prompt_start", "")
    ipe = b.get("image_prompt_end", "")
    vp = b.get("video_prompt", "")
    ip = b.get("image_prompt", "")
    
    if ip and not ips:
        if _wc(ip) < MIN_IMAGE_PROMPT:
            issues.append(f"image_prompt {_wc(ip)} words (need {MIN_IMAGE_PROMPT})")
        for field_name, text in [("IP", ip)]:
            found = _banned_in(text)
            if found:
                issues.append(f"banned words in {field_name}: {found}")
        if re.search(r"#[0-9a-fA-F]{6}", ip):
            issues.append("hex codes in image_prompt — check if appropriate")
    else:
        if _wc(ips) < MIN_IMAGE_PROMPT:
            issues.append(f"image_prompt_start {_wc(ips)} words (need {MIN_IMAGE_PROMPT})")
        if _wc(ipe) < MIN_IMAGE_PROMPT:
            issues.append(f"image_prompt_end {_wc(ipe)} words (need {MIN_IMAGE_PROMPT})")
        for field_name, text in [("IPS", ips), ("IPE", ipe), ("VP", vp)]:
            found = _banned_in(text)
            if found:
                issues.append(f"banned words in {field_name}: {found}")
                
    if _wc(vp) < MIN_VIDEO_PROMPT:
        issues.append(f"video_prompt {_wc(vp)} words (need {MIN_VIDEO_PROMPT})")
        
    if re.search(r"#[0-9a-fA-F]{6}", vp):
        issues.append("hex codes in VP — LTX-2.3 does not support hex")
        
    symbolic_phrases = ["representing ", "symbolizing ", "embodying ", "acting as a metaphor"]
    for phrase in symbolic_phrases:
        if phrase in vp.lower():
            issues.append(f"symbolic instruction in VP: '{phrase.strip()}'")
            break
            
    return issues


# ── Beat extraction ────────────────────────────────────────────────────────────

def extract_beats(section: dict) -> list:
    renderer = section.get("renderer", "")
    render_spec = section.get("render_spec", {})
    beats = []

    itv_beats = render_spec.get("image_to_video_beats", [])
    if itv_beats:
        segs = section.get("narration", {}).get("segments", [])
        seg_map = {}
        for idx, s in enumerate(segs):
            if isinstance(s, str):
                seg_map[f"seg_{idx + 1}"] = s
            else:
                seg_map[s.get("segment_id", f"seg_{idx + 1}")] = s.get("text", "")
        for b in itv_beats:
            narration_text = seg_map.get(b.get("segment_id"), "")
            beat_goal = b.get("beat_goal") or f"{b.get('purpose', '')} — {b.get('display_text', '')}".strip(" —")
            beats.append({
                "beat_id": b.get("beat_id", ""),
                "narration": narration_text,
                "beat_goal": beat_goal,
                "renderer": renderer,
                "image_prompt_start": b.get("image_prompt_start", ""),
                "image_prompt_end": b.get("image_prompt_end", ""),
                "video_prompt": b.get("video_prompt", ""),
            })
        return beats

    seg_specs = render_spec.get("segment_specs", [])
    for spec in seg_specs:
        if spec.get("renderer") in ELIGIBLE_RENDERERS:
            beats.append({
                "beat_id": spec.get("segment_id", ""),
                "narration": spec.get("narration", ""),
                "beat_goal": spec.get("beat_goal", ""),
                "renderer": spec.get("renderer", renderer),
                "image_prompt_start": spec.get("image_prompt_start", spec.get("image_prompt", "")),
                "image_prompt_end": spec.get("image_prompt_end", ""),
                "video_prompt": spec.get("video_prompt", ""),
            })

    info_beats = render_spec.get("infographic_beats", [])
    if info_beats:
        for b in info_beats:
            beats.append({
                "beat_id": b.get("beat_id", ""),
                "narration": "",
                "beat_goal": f"infographic — {b.get('concept', '')} ({b.get('style_name', '')})",
                "renderer": renderer,
                "image_prompt": b.get("image_prompt", ""),
                "image_prompt_start": "",
                "image_prompt_end": "",
                "video_prompt": "",
            })

    video_prompts = section.get("video_prompts", [])
    if video_prompts:
        segs = section.get("narration", {}).get("segments", [])
        seg_map = {}
        for idx, s in enumerate(segs):
            if isinstance(s, str):
                seg_map[f"seg_{idx + 1}"] = s
            else:
                seg_map[s.get("segment_id", f"seg_{idx + 1}")] = s.get("text", "")
        for b in video_prompts:
            narration_text = seg_map.get(b.get("segment_id"), "")
            beats.append({
                "beat_id": b.get("beat_id", ""),
                "narration": narration_text,
                "beat_goal": "video prompt enhancement",
                "renderer": renderer,
                "image_prompt_start": b.get("image_prompt", ""),
                "image_prompt_end": b.get("image_prompt_end", ""),
                "video_prompt": b.get("prompt", ""),
            })

    return beats


# ── Write-back ─────────────────────────────────────────────────────────────────

def _apply_by_position(orig_beats: list, enhanced_beats: list, id_key: str) -> None:
    for i, orig_beat in enumerate(orig_beats):
        if i >= len(enhanced_beats):
            logger.warning(f"[Enhancer] GPT-4o returned fewer beats than input — keeping original for beat {i + 1}+")
            break
        enh = enhanced_beats[i]
        if enh.get("image_prompt_start"): orig_beat["image_prompt_start"] = enh["image_prompt_start"]
        if enh.get("image_prompt_end"): orig_beat["image_prompt_end"] = enh["image_prompt_end"]
        if enh.get("video_prompt"): orig_beat["video_prompt"] = enh["video_prompt"]
        if enh.get("visual_reasoning"): orig_beat["visual_reasoning"] = enh["visual_reasoning"]
        if enh.get("image_prompt"): orig_beat["image_prompt"] = enh["image_prompt"]

def apply_enhanced_prompts(section: dict, enhanced_beats: list) -> None:
    render_spec = section.get("render_spec", {})
    itv_beats = render_spec.get("image_to_video_beats", [])
    seg_specs = render_spec.get("segment_specs", [])
    eligible_specs = [s for s in seg_specs if s.get("renderer") in ELIGIBLE_RENDERERS]
    info_beats = render_spec.get("infographic_beats", [])
    video_prompts = section.get("video_prompts", [])

    if itv_beats:
        _apply_by_position(itv_beats, enhanced_beats, id_key="beat_id")
    elif eligible_specs:
        _apply_by_position(eligible_specs, enhanced_beats, id_key="segment_id")
        for spec in eligible_specs:
            if spec.get("image_prompt_start") and not spec.get("image_prompt"):
                spec["image_prompt"] = spec["image_prompt_start"]
    elif info_beats:
        _apply_by_position(info_beats, enhanced_beats, id_key="beat_id")
    elif video_prompts:
        # For legacy video_prompts, we need to map back to prompt and image_prompt
        for i, orig_beat in enumerate(video_prompts):
            if i >= len(enhanced_beats):
                break
            enh = enhanced_beats[i]
            if enh.get("image_prompt_start"): orig_beat["image_prompt"] = enh["image_prompt_start"]
            if enh.get("image_prompt_end"): orig_beat["image_prompt_end"] = enh["image_prompt_end"]
            if enh.get("video_prompt"): orig_beat["prompt"] = enh["video_prompt"]
            if enh.get("visual_reasoning"): orig_beat["visual_reasoning"] = enh["visual_reasoning"]


def _enhance_quiz_explanation(section: dict, system_prompt: str, llm_routing: Optional[dict] = None) -> bool:
    quiz = section.get("understanding_quiz", {})
    ev = quiz.get("explanation_visual", {})
    if not ev: return False
    ev_renderer = ev.get("renderer", "")
    if ev_renderer not in ELIGIBLE_RENDERERS: return False
    ev_beats = ev.get("image_to_video_beats", [])
    if not ev_beats: return False

    synthetic = {
        "section_id": str(section.get("section_id", "?")) + "_quiz_expl",
        "section_type": "quiz_explanation",
        "renderer": ev_renderer,
        "render_spec": {"image_to_video_beats": ev_beats},
        "narration": {"segments": [{"text": quiz.get("explanation", "")}]},
    }
    enhanced = enhance_section(synthetic, system_prompt, llm_routing)
    if enhanced:
        enhanced = _enforce_quality(enhanced, synthetic["section_id"], llm_routing)
        _apply_by_position(ev_beats, enhanced, id_key="beat_id")
        return True
    return False


def _call_api(messages: list, temperature: float = 0.2, llm_routing: Optional[dict] = None) -> Optional[str]:
    from core.unified_content_generator import call_openrouter_llm, GeneratorConfig
    system_prompt = ""
    user_prompt = ""
    for m in messages:
        if m["role"] == "system":
            system_prompt += m["content"] + "\n"
        elif m["role"] == "user":
            user_prompt += m["content"] + "\n"

    config = GeneratorConfig(
        model=ENHANCER_MODEL,
        temperature=temperature,
        max_tokens=8192
    )

    try:
        content, _ = call_openrouter_llm(
            system_prompt=system_prompt.strip(),
            user_prompt=user_prompt.strip(),
            config=config
        )
        
        raw = content
        if raw.strip().startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines() if not line.strip().startswith("```")
            )
        return raw
    except Exception as e:
        logger.error(f"[Enhancer] API call failed: {e}")
        return None


def _repair_beat(beat: dict, issues: list, llm_routing: Optional[dict] = None) -> Optional[dict]:
    issue_text = "\n".join(f"- {i}" for i in issues)
    instructions = []

    ips = beat.get("image_prompt_start", "")
    ipe = beat.get("image_prompt_end", "")
    vp = beat.get("video_prompt", "")
    ip = beat.get("image_prompt", "")

    if ip and not ips:
        if _wc(ip) < MIN_IMAGE_PROMPT:
            deficit = MIN_IMAGE_PROMPT - _wc(ip)
            instructions.append(f"image_prompt is {_wc(ip)} words. Add {deficit} more words. "
                                f"Expand by adding: exact layout description, specific label text with quotes, "
                                f"color values (#hex allowed here), visual hierarchy details, style reference. "
                                f"Must be 100+ words for Gemini image generation.")
        for field_name, text in [("image_prompt", ip)]:
            found = _banned_in(text)
            if found:
                hints = "; ".join(f"remove '{w}'" for w in found)
                instructions.append(f"{field_name} contains banned words {found}. {hints}.")
    else:
        if _wc(ips) < MIN_IMAGE_PROMPT:
            deficit = MIN_IMAGE_PROMPT - _wc(ips)
            instructions.append(f"image_prompt_start is {_wc(ips)} words. Add {deficit} more words. "
                                f"Expand by adding: material texture detail, exact color values (#hex), "
                                f"rim lighting placement, spatial position of elements in frame.")
        if _wc(ipe) < MIN_IMAGE_PROMPT:
            deficit = MIN_IMAGE_PROMPT - _wc(ipe)
            instructions.append(f"image_prompt_end is {_wc(ipe)} words. Add {deficit} more words. "
                                f"Describe what visually changed vs the start frame in more specific detail.")
                                
    if _wc(vp) < MIN_VIDEO_PROMPT:
        deficit = MIN_VIDEO_PROMPT - _wc(vp)
        instructions.append(f"video_prompt is {_wc(vp)} words. Add {deficit} more words. "
                            f"Expand the MECHANISM section: describe step-by-step what moves, "
                            f"in which direction, at what rate, and what triggers each stage.")
                            
    for field_name, text in [("image_prompt_start", ips), ("image_prompt_end", ipe), ("video_prompt", vp)]:
        found = _banned_in(text)
        if found:
            replacements = {
                "dynamic": "replace with specific physical behavior",
                "cinematic": "replace with material and lighting description",
                "abstract": "replace with specific shape and color",
            }
            hints = "; ".join(replacements.get(w, f"remove '{w}'") for w in found)
            instructions.append(f"{field_name} contains banned words {found}. {hints}.")

    if re.search(r"#[0-9a-fA-F]{6}", vp):
        instructions.append("video_prompt contains hex codes (#RRGGBB). Replace ALL hex codes with descriptive color words.")

    symbolic_phrases = ["representing ", "symbolizing ", "embodying ", "acting as a metaphor"]
    for phrase in symbolic_phrases:
        if phrase in vp.lower():
            instructions.append(f"video_prompt contains symbolic phrase '{phrase.strip()}'. Replace it with a DIRECT PHYSICAL ACTION.")
            break

    repair_prompt = f"""You are repairing specific issues in a single visual prompt beat.

BEAT TO REPAIR:
{json.dumps(beat, indent=2)}

ISSUES TO FIX:
{issue_text}

SPECIFIC INSTRUCTIONS:
{chr(10).join(instructions)}

RULES:
- Fix ONLY the issues listed. Do not change fields that are already correct.
- Maintain the existing SUBJECT/INITIAL STATE/MECHANISM/RESULT/CAMERA structure in video_prompt.
- Keep beat_id unchanged.
- Background must remain #0d1117.
- Do not use banned words: {", ".join(BANNED_WORDS)}

OUTPUT: Return ONLY a valid JSON object for this single beat:
{{
  "beat_id": "...",
  "image_prompt_start": "...",
  "image_prompt_end": "...",
  "image_prompt": "...",
  "video_prompt": "...",
  "visual_reasoning": "..."
}}
No markdown. No explanation. JSON only."""

    raw = _call_api(
        messages=[{"role": "user", "content": repair_prompt}],
        temperature=0.3,
        llm_routing=llm_routing,
    )
    if not raw: return None
    try:
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[Enhancer] Repair parse error: {e}")
        return None

def _enforce_quality(enhanced_beats: list, section_id: str, llm_routing: Optional[dict] = None) -> list:
    for beat in enhanced_beats:
        issues = _beat_issues(beat)
        if not issues: continue

        bid = beat.get("beat_id", "?")
        logger.info(f"[Enhancer] Section {section_id} [{bid}]: {len(issues)} issue(s) — repairing...")

        for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
            repaired = _repair_beat(beat, issues, llm_routing)
            if not repaired:
                logger.warning(f"[Enhancer] [{bid}] Repair attempt {attempt} failed — keeping current.")
                break
            for field in ("image_prompt_start", "image_prompt_end", "video_prompt", "visual_reasoning"):
                if repaired.get(field): beat[field] = repaired[field]
            issues = _beat_issues(beat)
            if not issues:
                logger.info(f"[Enhancer] [{bid}] PASS after {attempt} repair(s).")
                break
            else:
                logger.warning(f"[Enhancer] [{bid}] Attempt {attempt} still failing: {issues}")

        if issues:
            logger.warning(f"[Enhancer] [{bid}] Could not fully repair after {MAX_REPAIR_ATTEMPTS} attempts.")

    for beat in enhanced_beats:
        vp = beat.get("video_prompt", "")
        if vp and re.search(r"#[0-9a-fA-F]{6}", vp):
            beat["video_prompt"] = _strip_hex_from_vp(vp)

    return enhanced_beats


# ── API call ───────────────────────────────────────────────────────────────────

def enhance_section(section: dict, system_prompt: str, llm_routing: Optional[dict] = None) -> Optional[list]:
    if not OPENROUTER_API_KEY and not (llm_routing and llm_routing.get("prompt_enhancer") == "local"):
        logger.warning("[Enhancer] OPENROUTER_API_KEY not set and no local routing — skipping.")
        return None

    beats = extract_beats(section)
    if not beats:
        logger.info(f"[Enhancer] Section {section.get('section_id')}: no beats to enhance, skipping.")
        return None

    user_payload = {
        "section_id": section.get("section_id"),
        "section_type": section.get("section_type", ""),
        "renderer": section.get("renderer"),
        "beats": beats,
    }

    try:
        raw = _call_api(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            temperature=0.2,
            llm_routing=llm_routing,
        )
        if not raw: return None
        data = json.loads(raw)
        return data.get("beats", [])

    except Exception as e:
        logger.error(f"[Enhancer] Section {section.get('section_id')} enhance failed: {e}")
        return None


# ── Main entry point ───────────────────────────────────────────────────────────

def run_prompt_enhancement(presentation: dict, log_fn=None, llm_routing: Optional[dict] = None) -> dict:
    def _log(msg: str):
        logger.info(f"[Enhancer] {msg}")
        if log_fn: log_fn("prompt_enhancer", msg)

    cultural_instruction = detect_cultural_profile(presentation)
    system_prompt = ENHANCER_SYSTEM_PROMPT_TEMPLATE.replace("{cultural_profile_instruction}", cultural_instruction)

    sections = presentation.get("sections", [])
    eligible = [s for s in sections if s.get("renderer") in ELIGIBLE_RENDERERS]

    provider_label = "Local Ollama" if (llm_routing and llm_routing.get("prompt_enhancer") == "local") else "OpenRouter"
    _log(f"Found {len(eligible)} eligible section(s) out of {len(sections)} total (provider={provider_label}).")

    enhanced_count = 0
    for section in eligible:
        sec_id = section.get("section_id", "?")
        renderer = section.get("renderer", "?")
        _log(f"  Enhancing section {sec_id} (renderer={renderer})...")

        try:
            enhanced_beats = enhance_section(section, system_prompt, llm_routing=llm_routing)
            if enhanced_beats:
                enhanced_beats = _enforce_quality(enhanced_beats, sec_id, llm_routing)
                apply_enhanced_prompts(section, enhanced_beats)
                _log(f"  ✅ Section {sec_id}: {len(enhanced_beats)} beat(s) enhanced.")
                enhanced_count += 1
            else:
                _log(f"  ⚠️ Section {sec_id}: no enhancement returned, keeping original prompts.")

        except Exception as e:
            _log(f"  ⚠️ Section {sec_id}: enhancement error (non-fatal): {e}")

    _log("Enhancing quiz explanation visuals...")
    quiz_enhanced = 0
    for section in sections:
        try:
            if _enhance_quiz_explanation(section, system_prompt, llm_routing):
                _log(f"  ✅ Section {section.get('section_id')} quiz explanation enhanced.")
                quiz_enhanced += 1
        except Exception as e:
            _log(f"  ⚠️ Section {section.get('section_id')} quiz explanation error (non-fatal): {e}")
    _log(f"Quiz explanations complete: {quiz_enhanced} enhanced.")

    _log(f"Enhancement complete: {enhanced_count}/{len(eligible)} section(s) improved.")

    return presentation
