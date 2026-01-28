// Add this JavaScript code to show/hide the user feedback textarea
// based on the selected phase in the Retry Phase modal

document.getElementById('retryPhaseSelect').addEventListener('change', function() {
    const phase = this.value;
    const feedbackGroup = document.getElementById('userFeedbackGroup');
    
    // Show feedback box only for Manim phases
    if (phase === 'manim_codegen' || phase === 'manim_render') {
        feedbackGroup.style.display = 'block';
    } else {
        feedbackGroup.style.display = 'none';
        document.getElementById('userFeedbackText').value = ''; // Clear feedback when hidden
    }
});

// Initialize visibility on modal open
function showRetryPhaseModal(jobId) {
    currentRetryJobId = jobId;
    document.getElementById('retryPhaseJobId').textContent = jobId;
    document.getElementById('retrySectionIds').value = '';
    document.getElementById('userFeedbackText').value = '';
    
    // Check initial phase and set visibility
    const phase = document.getElementById('retryPhaseSelect').value;
    const feedbackGroup = document.getElementById('userFeedbackGroup');
    if (phase === 'manim_codegen' || phase === 'manim_render') {
        feedbackGroup.style.display = 'block';
    } else {
        feedbackGroup.style.display = 'none';
    }
    
    document.getElementById('retryPhaseModal').style.display = 'flex';
}
