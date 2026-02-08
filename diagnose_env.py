import sys
import importlib.util

print(f"Python executable: {sys.executable}")
print(f"Path: {sys.path}")

try:
    import ecomm_prod_assistant
    print("Successfully imported ecomm_prod_assistant")
    print(f"Location: {ecomm_prod_assistant.__file__}")
except ImportError as e:
    print(f"Failed to import ecomm_prod_assistant: {e}")

try:
    spec = importlib.util.find_spec("ecomm_prod_assistant")
    if spec:
        print(f"Found spec: {spec}")
    else:
        print("Spec not found")
except Exception as e:
    print(f"Error finding spec: {e}")
