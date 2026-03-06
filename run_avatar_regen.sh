#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# run_avatar_regen.sh
#
# Auto-restart wrapper for regenerate_bad_avatars.py
# Agar script kisi bhi wajah se stop ho jaaye — error, crash, timeout —
# yeh wrapper use automatically restart karta hai jab tak kaam poora na ho.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="/nvme0n1-disk/nvme01/ai-document-presentation-v2"
PYTHON_SCRIPT="$SCRIPT_DIR/regenerate_bad_avatars.py"
LOG_FILE="/tmp/avatar_regen.log"

RESTART_DELAY=15        # seconds restart se pehle wait
MAX_RESTARTS=999        # effectively infinite
ATTEMPT=0

cd "$SCRIPT_DIR" || { echo "❌ Could not cd to $SCRIPT_DIR"; exit 1; }

echo "🚀 Auto-restart wrapper started at $(date)" | tee -a "$LOG_FILE"
echo "   Script: $PYTHON_SCRIPT" | tee -a "$LOG_FILE"
echo "   Log:    $LOG_FILE" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

while [ $ATTEMPT -lt $MAX_RESTARTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "" | tee -a "$LOG_FILE"
    echo "▶️  Attempt #$ATTEMPT — $(date)" | tee -a "$LOG_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

    # Run the script (auto-yes via echo, unbuffered output)
    echo "y" | sudo python3 -u "$PYTHON_SCRIPT" 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[1]}

    echo "" | tee -a "$LOG_FILE"
    echo "⚡ Script exited with code: $EXIT_CODE at $(date)" | tee -a "$LOG_FILE"

    # Agar "Nothing to do" print hua → kaam complete, exit
    if grep -q "Nothing to do" "$LOG_FILE" 2>/dev/null; then
        echo "✅ ALL DONE — koi bhi bad avatar bacha nahin!" | tee -a "$LOG_FILE"
        echo "   Total attempts: $ATTEMPT" | tee -a "$LOG_FILE"
        exit 0
    fi

    # Normal success exit (0) bhi check karo
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Script successfully completed!" | tee -a "$LOG_FILE"
        exit 0
    fi

    # Abhi bhi kaam baaki hai — restart karenge
    echo "🔄 Script stopped (exit code: $EXIT_CODE). ${RESTART_DELAY}s baad restart..." | tee -a "$LOG_FILE"
    sleep $RESTART_DELAY
done

echo "❌ Max restarts ($MAX_RESTARTS) reach ho gaye. Manual check karo." | tee -a "$LOG_FILE"
exit 1
