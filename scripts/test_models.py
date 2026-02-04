
import os
import sys
# Ensure src is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import GeneDescriptionAgent

# Dummy "Gene" and simplified flow just to test model connection
# We will override _run_gemini or just catch errors 
MODELS_TO_TEST = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
]

def test_models():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Please set GOOGLE_API_KEY env var")
        return

    print("--- Testing Model Availability ---")
    for model in MODELS_TO_TEST:
        print(f"\nTesting: {model} ...", end=" ")
        try:
            # We initialize the agent with the specific model
            agent = GeneDescriptionAgent(api_key=api_key, model_name=model)
            # We send a tiny prompt directly to avoid the whole search pipeline overhead
            # We bypass the complex _summarize and call client.models.generate_content directly if possible
            # or we just use a simplified prompt
            response = agent.client.models.generate_content(
                model=model,
                contents="Hello, just testing connectivity. Reply with 'OK'.",
            )
            print(f"✅ Success! Response: {response.text.strip()}")
        except Exception as e:
            print(f"❌ Failed! Error: {e}")

if __name__ == "__main__":
    test_models()
