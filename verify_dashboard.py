import requests

try:
    response = requests.get('http://localhost:5005/dashboard')
    print("Status Code:", response.status_code)
    print("Cache-Control:", response.headers.get('Cache-Control'))
    print("Pragma:", response.headers.get('Pragma'))
    print("Expires:", response.headers.get('Expires'))
    
    if 'renderReviewSections' in response.text:
        print("✓ renderReviewSections found in response")
    else:
        print("✗ renderReviewSections NOT found")
        
    if 'content.flashcards' in response.text:
        print("✓ New code (flashcards) found in response")
    else:
        print("✗ New code (flashcards) NOT found")

except Exception as e:
    print(f"Error: {e}")
