#!/bin/bash
#
# TEST-003: End-to-End Pipeline Test
# Runs the V1.5 pipeline via API and validates the output.
#
# Usage:
#   ./tests/test_e2e_pipeline.sh [pdf_path]
#
# If no pdf_path provided, uses a test PDF if available.
#

set -e

GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BLUE='\033[94m'
RESET='\033[0m'

API_HOST="${API_HOST:-http://localhost:5000}"

print_result() {
    local test_name="$1"
    local passed="$2"
    local message="$3"
    
    if [ "$passed" = "true" ]; then
        echo -e "${GREEN}[PASS]${RESET} $test_name"
    else
        echo -e "${RED}[FAIL]${RESET} $test_name"
    fi
    
    if [ -n "$message" ]; then
        echo "       $message"
    fi
}

echo -e "\n${BLUE}======================================================${RESET}"
echo -e "${BLUE}TEST-003: End-to-End Pipeline Test${RESET}"
echo -e "${BLUE}======================================================${RESET}"

echo -e "\n${BLUE}=== API Health Check ===${RESET}"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_HOST/api/health" 2>/dev/null || echo "000")

if [ "$HEALTH_RESPONSE" = "200" ]; then
    print_result "API is healthy" "true"
else
    print_result "API is healthy" "false" "HTTP $HEALTH_RESPONSE (is the server running?)"
    echo -e "\n${YELLOW}Start the server with: python api/app.py${RESET}"
    exit 1
fi

echo -e "\n${BLUE}=== V1.5 Pipeline Info ===${RESET}"
PIPELINE_INFO=$(curl -s "$API_HOST/api/v15/pipeline-info" 2>/dev/null || echo "{}")
echo "$PIPELINE_INFO" | python3 -m json.tool 2>/dev/null || echo "$PIPELINE_INFO"

has_agents=$(echo "$PIPELINE_INFO" | grep -c "agents" || echo "0")
if [ "$has_agents" -gt "0" ]; then
    print_result "Pipeline info available" "true"
else
    print_result "Pipeline info available" "false"
fi

PDF_PATH="$1"
if [ -z "$PDF_PATH" ]; then
    if [ -f "test_docs/sample.pdf" ]; then
        PDF_PATH="test_docs/sample.pdf"
    elif [ -f "attached_assets/test_input.pdf" ]; then
        PDF_PATH="attached_assets/test_input.pdf"
    fi
fi

if [ -n "$PDF_PATH" ] && [ -f "$PDF_PATH" ]; then
    echo -e "\n${BLUE}=== Starting V1.5 Pipeline ===${RESET}"
    echo "PDF: $PDF_PATH"
    
    GENERATE_RESPONSE=$(curl -s -X POST "$API_HOST/api/v15/generate" \
        -F "pdf=@$PDF_PATH" \
        -F "tts_provider=edge" \
        2>/dev/null || echo '{"error": "Request failed"}')
    
    echo "$GENERATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$GENERATE_RESPONSE"
    
    JOB_ID=$(echo "$GENERATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)
    
    if [ -n "$JOB_ID" ]; then
        print_result "Job started" "true" "Job ID: $JOB_ID"
        
        echo -e "\n${BLUE}=== Monitoring Job Status ===${RESET}"
        
        MAX_WAIT=900  # 15 minutes
        WAIT_INTERVAL=10
        ELAPSED=0
        
        while [ $ELAPSED -lt $MAX_WAIT ]; do
            STATUS_RESPONSE=$(curl -s "$API_HOST/api/job/$JOB_ID/status" 2>/dev/null || echo '{}')
            STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)
            PHASE=$(echo "$STATUS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('current_phase',''))" 2>/dev/null)
            
            echo "  [$ELAPSED s] Status: $STATUS, Phase: $PHASE"
            
            if [ "$STATUS" = "completed" ]; then
                print_result "Job completed" "true"
                break
            elif [ "$STATUS" = "failed" ] || [ "$STATUS" = "error" ]; then
                ERROR=$(echo "$STATUS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error','Unknown error'))" 2>/dev/null)
                print_result "Job completed" "false" "$ERROR"
                exit 1
            fi
            
            sleep $WAIT_INTERVAL
            ELAPSED=$((ELAPSED + WAIT_INTERVAL))
        done
        
        if [ $ELAPSED -ge $MAX_WAIT ]; then
            print_result "Job completed within timeout" "false" "Exceeded $MAX_WAIT seconds"
            exit 1
        fi
        
        echo -e "\n${BLUE}=== Validating Output ===${RESET}"
        
        OUTPUT_DIR="output/$JOB_ID"
        PRESENTATION_FILE="$OUTPUT_DIR/presentation.json"
        
        if [ -f "$PRESENTATION_FILE" ]; then
            print_result "presentation.json exists" "true"
            
            python3 tests/test_display_avatar.py "$PRESENTATION_FILE"
            
            SECTION_COUNT=$(python3 -c "import json; print(len(json.load(open('$PRESENTATION_FILE')).get('sections',[])))" 2>/dev/null || echo "0")
            print_result "Has sections" "$([ $SECTION_COUNT -gt 0 ] && echo true || echo false)" "Found $SECTION_COUNT sections"
            
            HAS_INTRO=$(python3 -c "import json; sections=json.load(open('$PRESENTATION_FILE')).get('sections',[]); print('true' if any(s.get('section_type')=='intro' for s in sections) else 'false')" 2>/dev/null)
            print_result "Has intro section" "$HAS_INTRO"
            
            HAS_SUMMARY=$(python3 -c "import json; sections=json.load(open('$PRESENTATION_FILE')).get('sections',[]); print('true' if any(s.get('section_type')=='summary' for s in sections) else 'false')" 2>/dev/null)
            print_result "Has summary section" "$HAS_SUMMARY"
            
        else
            print_result "presentation.json exists" "false" "File not found: $PRESENTATION_FILE"
        fi
        
    else
        print_result "Job started" "false" "No job_id in response"
    fi
else
    echo -e "\n${YELLOW}=== Skipping Full Pipeline Test ===${RESET}"
    echo "No PDF file provided or found."
    echo ""
    echo "To run full E2E test:"
    echo "  ./tests/test_e2e_pipeline.sh path/to/test.pdf"
fi

echo -e "\n${BLUE}======================================================${RESET}"
echo -e "${BLUE}TEST-003 COMPLETE${RESET}"
echo -e "${BLUE}======================================================${RESET}"
