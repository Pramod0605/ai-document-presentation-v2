
import sys
import os

# Add the current directory to sys.path so we can import api.app
sys.path.append(os.getcwd())

try:
    from api.app import app
    with open("routes.txt", "w", encoding="utf-8") as f:
        print("Map of rules:", file=f)
        for rule in app.url_map.iter_rules():
            print(f"{rule}: {rule.endpoint}", file=f)
except ImportError as e:
    print(f"ImportError: {e}")
    # Try adjusting path if needed, or maybe api/app.py has side effects (it does run app.run if main)
    # Since we import it, main won't run.
except Exception as e:
    print(f"Error: {e}")
