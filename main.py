import argparse
import sys
from src.agent import GeneDescriptionAgent

def main():
    parser = argparse.ArgumentParser(description="Maize Gene Description Agent")
    parser.add_argument("gene_id", help="Maize Gene ID (e.g., Zm00001eb126570)")
    
    args = parser.parse_args()
    
    # Initialize Agent
    agent = GeneDescriptionAgent()
    
    # Run
    try:
        result = agent.generate_description(args.gene_id)
        print("\n" + "="*50)
        print(f"REPORT FOR {args.gene_id}")
        print("="*50 + "\n")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
