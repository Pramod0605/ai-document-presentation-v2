#!/usr/bin/env python3
"""
LTX-Video API Endpoint Testing Script
Tests all API endpoints and validates responses
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

# Configuration
BASE_URL = "http://69.197.176.2:8000"
TEST_IMAGE = "test_image.jpg"  # Optional: path to test image

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_test(name, status, details=""):
    symbol = f"{Colors.GREEN}✓{Colors.RESET}" if status else f"{Colors.RED}✗{Colors.RESET}"
    print(f"{symbol} {name}")
    if details:
        print(f"  {Colors.YELLOW}{details}{Colors.RESET}")

def test_endpoint(method, endpoint, data=None, files=None, expected_status=200):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            if files:
                response = requests.post(url, data=data, files=files, timeout=10)
            else:
                response = requests.post(url, json=data, timeout=10)
        else:
            return False, f"Unsupported method: {method}"
        
        success = response.status_code == expected_status
        
        if success:
            try:
                json_data = response.json()
                return True, json_data
            except:
                return True, response.text[:200]
        else:
            return False, f"Status {response.status_code}: {response.text[:200]}"
            
    except Exception as e:
        return False, str(e)

def main():
    print_header("LTX-Video API Endpoint Testing")
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # ========================================================================
    # 1. Health Check
    # ========================================================================
    print_header("1. Health & Status Endpoints")
    
    # Health check
    success, data = test_endpoint("GET", "/health")
    results["total"] += 1
    if success:
        results["passed"] += 1
        print_test("GET /health", True, f"Status: {data.get('status', 'N/A')}")
    else:
        results["failed"] += 1
        print_test("GET /health", False, data)
    results["tests"].append({"endpoint": "/health", "success": success})
    
    # Queue status
    success, data = test_endpoint("GET", "/api/queue/status")
    results["total"] += 1
    if success:
        results["passed"] += 1
        gpus = data.get("gpus", [])
        print_test("GET /api/queue/status", True, 
                  f"GPUs: {len(gpus)}, Queue: {data.get('queue_length', 0)}")
    else:
        results["failed"] += 1
        print_test("GET /api/queue/status", False, data)
    results["tests"].append({"endpoint": "/api/queue/status", "success": success})
    
    # ========================================================================
    # 2. Video Generation Endpoints
    # ========================================================================
    print_header("2. Video Generation Endpoints")
    
    # Text-to-Video
    text_to_video_data = {
        "prompt": "API test: a cat playing with a ball",
        "width": 704,
        "height": 480,
        "num_frames": 25,  # Short for testing
        "frame_rate": 25,
        "steps": 10,  # Minimal steps for testing
        "guidance_scale": 3.0,
        "seed": 42
    }
    
    success, data = test_endpoint("POST", "/api/generate/text-to-video", 
                                 data=text_to_video_data)
    results["total"] += 1
    job_id = None
    if success:
        results["passed"] += 1
        job_id = data.get("job_id")
        print_test("POST /api/generate/text-to-video", True, 
                  f"Job ID: {job_id[:8] if job_id else 'N/A'}")
    else:
        results["failed"] += 1
        print_test("POST /api/generate/text-to-video", False, data)
    results["tests"].append({"endpoint": "/api/generate/text-to-video", "success": success})
    
    # ========================================================================
    # 3. Job Management Endpoints
    # ========================================================================
    print_header("3. Job Management Endpoints")
    
    if job_id:
        # Get job status
        success, data = test_endpoint("GET", f"/api/job/{job_id}")
        results["total"] += 1
        if success:
            results["passed"] += 1
            print_test(f"GET /api/job/{job_id[:8]}", True, 
                      f"Status: {data.get('status', 'N/A')}, GPU: {data.get('gpu_id', 'N/A')}")
        else:
            results["failed"] += 1
            print_test(f"GET /api/job/{job_id[:8]}", False, data)
        results["tests"].append({"endpoint": f"/api/job/{job_id}", "success": success})
        
        # Wait a bit for job to process
        print(f"\n{Colors.YELLOW}Waiting 5 seconds for job to process...{Colors.RESET}")
        time.sleep(5)
        
        # Check job status again
        success, data = test_endpoint("GET", f"/api/job/{job_id}")
        if success:
            print_test(f"GET /api/job/{job_id[:8]} (after wait)", True, 
                      f"Status: {data.get('status', 'N/A')}")
    
    # Job history
    success, data = test_endpoint("GET", "/api/jobs/history")
    results["total"] += 1
    if success:
        results["passed"] += 1
        jobs = data if isinstance(data, list) else []
        print_test("GET /api/jobs/history", True, f"Jobs: {len(jobs)}")
    else:
        results["failed"] += 1
        print_test("GET /api/jobs/history", False, data)
    results["tests"].append({"endpoint": "/api/jobs/history", "success": success})
    
    # ========================================================================
    # 4. Gallery Endpoints
    # ========================================================================
    print_header("4. Gallery Endpoints")
    
    # List videos
    success, data = test_endpoint("GET", "/api/videos/list")
    results["total"] += 1
    if success:
        results["passed"] += 1
        videos = data.get("videos", [])
        total = data.get("total", 0)
        print_test("GET /api/videos/list", True, f"Videos: {total}")
        if videos:
            print(f"  {Colors.YELLOW}Latest: {videos[0].get('prompt', 'N/A')[:50]}...{Colors.RESET}")
    else:
        results["failed"] += 1
        print_test("GET /api/videos/list", False, data)
    results["tests"].append({"endpoint": "/api/videos/list", "success": success})
    
    # Gallery page
    success, data = test_endpoint("GET", "/gallery")
    results["total"] += 1
    if success:
        results["passed"] += 1
        print_test("GET /gallery", True, "HTML page loaded")
    else:
        results["failed"] += 1
        print_test("GET /gallery", False, data)
    results["tests"].append({"endpoint": "/gallery", "success": success})
    
    # ========================================================================
    # 5. Frontend Pages
    # ========================================================================
    print_header("5. Frontend Pages")
    
    pages = [
        ("/", "Home page"),
        ("/text-to-video", "Text-to-Video page"),
        ("/image-to-video", "Image-to-Video page"),
    ]
    
    for endpoint, name in pages:
        success, data = test_endpoint("GET", endpoint)
        results["total"] += 1
        if success:
            results["passed"] += 1
            print_test(f"GET {endpoint}", True, name)
        else:
            results["failed"] += 1
            print_test(f"GET {endpoint}", False, data)
        results["tests"].append({"endpoint": endpoint, "success": success})
    
    # ========================================================================
    # 6. API Documentation
    # ========================================================================
    print_header("6. API Documentation")
    
    docs = [
        ("/docs", "Swagger UI"),
        ("/redoc", "ReDoc"),
    ]
    
    for endpoint, name in docs:
        success, data = test_endpoint("GET", endpoint)
        results["total"] += 1
        if success:
            results["passed"] += 1
            print_test(f"GET {endpoint}", True, name)
        else:
            results["failed"] += 1
            print_test(f"GET {endpoint}", False, data)
        results["tests"].append({"endpoint": endpoint, "success": success})
    
    # ========================================================================
    # Summary
    # ========================================================================
    print_header("Test Summary")
    
    pass_rate = (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
    
    print(f"Total Tests:  {results['total']}")
    print(f"{Colors.GREEN}Passed:       {results['passed']}{Colors.RESET}")
    print(f"{Colors.RED}Failed:       {results['failed']}{Colors.RESET}")
    print(f"Pass Rate:    {pass_rate:.1f}%\n")
    
    if results["failed"] > 0:
        print(f"{Colors.RED}Some tests failed. Check the output above for details.{Colors.RESET}")
        return 1
    else:
        print(f"{Colors.GREEN}All tests passed! ✓{Colors.RESET}")
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Testing interrupted by user{Colors.RESET}")
        exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        exit(1)

