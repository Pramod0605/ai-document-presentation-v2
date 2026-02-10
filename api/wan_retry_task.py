
def run_wan_rerender_task(job_id, presentation, section_ids, tracker, pres_path):
    """Background task for WAN rerendering."""
    from core.llm_client_v12 import rerender_sections_wan
    import json
    
    # STATUS UPDATE: Start
    try:
        from core.job_manager import job_manager
        if job_manager:
            job_manager.update_job(job_id, {
                "status": "processing",
                "current_step_name": f"Rerendering {len(section_ids)} WAN video(s)...",
                "current_phase_key": "video_generation"
            }, persist=True)
    except: pass
    
    try:
        print(f"[WAN-TASK] Re-rendering sections {section_ids} for job {job_id}")
        updated = rerender_sections_wan(presentation, section_ids, tracker)
        
        with open(pres_path, "w") as f:
            json.dump(updated, f, indent=2)
            
        # Completion Status
        if job_manager:
            job_manager.complete_job(job_id, status="completed_with_errors") # Keep as with errors to allow more retries? Or completed?
            # Actually, if this was a *retry*, finishing it means we are back to "Completed" or "Completed with Errors" depending on result.
            # Let's check results.
            failed = [s for s in updated.get("sections", []) if s.get("section_id") in section_ids and s.get("renderer_error")]
            final_status = "completed_with_errors" if failed else "completed"
            job_manager.complete_job(job_id, status=final_status)

    except Exception as e:
        print(f"[WAN-TASK] Error during rerender: {e}")
        if job_manager:
            job_manager.fail_job(job_id, str(e))
