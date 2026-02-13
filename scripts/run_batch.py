import os
import sys
import pandas as pd
import argparse
import re
import time
from tqdm import tqdm
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.agent import GeneDescriptionAgent

load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser(description="Batch generate gene descriptions.")
    parser.add_argument("--input", required=True, help="Path to input TSV file (must have GeneID and Species columns)")
    parser.add_argument("--output", required=True, help="Path to output TSV file")
    parser.add_argument("--api_key", help="Gemini API Key (optional, can use env)")
    parser.add_argument("--email", help="NCBI Email (optional, can use env)")
    parser.add_argument("--model", default="gemini-2.0-flash-exp", help="Gemini model to use (default: gemini-2.0-flash-exp)")
    return parser.parse_args()

def parse_markdown_output(text):
    """
    Extracts Function Summary, Keywords, and Key References from the Agent's Markdown output.
    Returns: summary (str), keywords (list), references (list)
    """
    summary = ""
    keywords_list = []
    references_list = []
    
    # helper to clean headers
    # matches **Header**: or ### Header or **Header**
    
    # 1. Extract Function Summary
    # Look for "Function Summary" header, then capture until "Keywords" header
    summary_match = re.search(r'(?:\*\*|###\s?|##\s?)Function Summary(?:[\*\s:]*)?\s*(.*?)\s*(?=(?:\*\*|###\s?|##\s?)Keywords)', text, re.DOTALL | re.IGNORECASE)
    if summary_match:
        summary = summary_match.group(1).strip()
    else:
        # Fallback
        summary_match_simple = re.search(r'(?:\*\*|###\s?|##\s?)Summary(?:[\*\s:]*)?\s*(.*?)\s*(?=(?:\*\*|###\s?|##\s?)Keywords)', text, re.DOTALL | re.IGNORECASE)
        if summary_match_simple:
            summary = summary_match_simple.group(1).strip()
            
    # Clean Summary
    summary = re.sub(r'\s+', ' ', summary).lstrip(' :*')

    # 2. Extract Keywords
    # Look for "Keywords" header, capture until "Key References" or "References"
    keywords_match = re.search(r'(?:\*\*|###\s?|##\s?)Keywords(?:[\*\s:]*)?\s*(.*?)\s*(?=(?:\*\*|###\s?|##\s?)Key References|(?:\*\*|###\s?|##\s?)References|$)', text, re.DOTALL | re.IGNORECASE)
    if keywords_match:
        raw_keywords = keywords_match.group(1).strip().lstrip(' :*')
        # Clean up if it starts with a list char
        if raw_keywords.startswith('- ') or raw_keywords.startswith('* '):
             # it's a list
             keywords_list = [k.strip().lstrip('-*').strip() for k in re.split(r'\n', raw_keywords) if k.strip()]
        else:
             # comma separated
             keywords_list = [k.strip() for k in re.split(r'[,\n]+', raw_keywords) if k.strip()]
        
    # 3. Extract References
    # Look for "Key References" or "References"
    references_match = re.search(r'(?:\*\*|###\s?|##\s?)(?:Key )?References(?:[\*\s:]*)?\s*(.*)', text, re.DOTALL | re.IGNORECASE)
    if references_match:
        raw_refs = references_match.group(1).strip().lstrip(' :*')
        # Split by newlines that start with - or * or number
        lines = raw_refs.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith('-') or line.startswith('*') or line[0].isdigit():
                # Remove leading bullets/numbers
                clean_ref = re.sub(r'^[-*0-9\.]+\s+', '', line).strip()
                references_list.append(clean_ref)

    return summary, keywords_list, references_list

def main():
    args = parse_args()
    
    # Load Input
    try:
        if args.input.endswith('.tsv'):
            df = pd.read_csv(args.input, sep='\t')
        elif args.input.endswith('.csv'):
             df = pd.read_csv(args.input)
        else:
             # Fallback: assume tab
             df = pd.read_csv(args.input, sep='\t')
             
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    # Normalize columns (case insensitive lookup)
    cols = {c.lower(): c for c in df.columns}
    
    if 'geneid' in cols:
        id_col = cols['geneid']
    else:
        # Fallback to first column
        id_col = df.columns[0]
        print(f"Warning: 'GeneID' column not found. Using '{id_col}' as ID column.")
        
    if 'species' in cols:
        species_col = cols['species']
    else:
         # Fallback to second column if exists, else default to Maize?
         if len(df.columns) > 1:
             species_col = df.columns[1]
             print(f"Warning: 'Species' column not found. Using '{species_col}' as Species column.")
         else:
             print("Error: Input file must have a Species column or at least 2 columns.")
             return

    # Initialize Agent
    api_key = args.api_key or os.getenv("GOOGLE_API_KEY")
    email = args.email or os.getenv("NCBI_EMAIL")
    
    if not api_key or not email:
        print("Error: GOOGLE_API_KEY and NCBI_EMAIL are required.")
        return
        
    print(f"Initializing Agent with model: {args.model}...")
    agent = GeneDescriptionAgent(api_key=api_key, email=email, model_name=args.model)
    
    # Define column structure
    base_cols = ["GeneID", "Species", "Summary"]
    kw_cols = [f"Keyword {i+1}" for i in range(5)]
    ref_cols = [f"Reference {i+1}" for i in range(5)]
    status_col = ["Status"]
    final_cols = base_cols + kw_cols + ref_cols + status_col
    
    # Determine output mode
    is_html_output = args.output.endswith('.html')
    
    # For HTML output, set up reports directory
    if is_html_output:
        output_dir = os.path.dirname(os.path.abspath(args.output))
        output_basename = os.path.splitext(os.path.basename(args.output))[0]
        reports_dir_name = f"{output_basename}_reports"
        reports_dir = os.path.join(output_dir, reports_dir_name)
        os.makedirs(reports_dir, exist_ok=True)
        print(f"Created reports directory: {reports_dir}")
    
    # Initialize output file with header
    if not is_html_output:
        # Create TSV with header
        header_df = pd.DataFrame(columns=final_cols)
        header_df.to_csv(args.output, sep='\t', index=False)
    
    results = []  # Keep results in memory for HTML table generation
    
    # Process genes with progress bar
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing genes", unit="gene"):
        gene_id = str(row[id_col]).strip()
        species = str(row[species_col]).strip()
        
        try:
            # Generate Description
            description_md = agent.generate_description(gene_id, organism=species)
            
            # Parse Output
            summary, keywords, references = parse_markdown_output(description_md)
            
            row_data = {
                "GeneID": gene_id,
                "Species": species,
                "Summary": summary
            }
            
            # Populate Keywords Columns (1-5)
            for i in range(5):
                key = f"Keyword {i+1}"
                row_data[key] = keywords[i] if i < len(keywords) else ""
            
            # Populate References Columns (1-5)
            for i in range(5):
                key = f"Reference {i+1}"
                row_data[key] = references[i] if i < len(references) else ""
            
            # Store full markdown for HTML report generation
            row_data["FullReport"] = description_md
            row_data["Status"] = "Success"
            
        except Exception as e:
            print(f"  Error: {e}")
            row_data = {
                "GeneID": gene_id,
                "Species": species,
                "Summary": f"Error: {e}",
                "Status": "Error",
                "FullReport": f"# Error Processing {gene_id}\n\n{e}"
            }
            # Fill empty columns
            for i in range(5):
                row_data[f"Keyword {i+1}"] = ""
                row_data[f"Reference {i+1}"] = ""
        
        # Write to disk immediately
        if is_html_output:
            # For HTML: save individual report and keep in memory for final table
            safe_id = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', gene_id)
            report_filename = f"{safe_id}.html"
            report_path = os.path.join(reports_dir, report_filename)
            
            def simple_md_to_html(md_text):
                html = md_text
                html = re.sub(r'^# (.*)', r'<h1>\1</h1>', html, flags=re.MULTILINE)
                html = re.sub(r'^## (.*)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
                html = re.sub(r'^### (.*)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
                html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
                html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)
                html = re.sub(r'^\- (.*)', r'<li>\1</li>', html, flags=re.MULTILINE)
                html = html.replace('\n', '<br>')
                return html
            
            report_content = row_data.get('FullReport', '')
            report_html_body = simple_md_to_html(report_content)
            
            report_html = f"""
            <html>
            <head>
                <title>{gene_id} Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
                    h1, h2, h3 {{ color: #2c3e50; }}
                    a {{ color: #1a73e8; }}
                </style>
            </head>
            <body>
                <a href="../{os.path.basename(args.output)}">&larr; Back to Main Table</a>
                <hr>
                {report_html_body}
            </body>
            </html>
            """
            
            with open(report_path, 'w') as f:
                f.write(report_html)
            
            # Update Summary with link for HTML table
            link = f'<a href="./{reports_dir_name}/{report_filename}" target="_blank">View Full Report</a>'
            row_data["Summary"] = link
            results.append(row_data)
            
            # Update main HTML table after each gene
            result_df = pd.DataFrame(results)
            
            def _make_html_links(text):
                if not isinstance(text, str): return text
                text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
                url_pattern = r'(?<!href=")(?<!">)(https?://[^\s<"]+)'
                text = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', text)
                return text
            
            for col in ref_cols:
                if col in result_df.columns:
                    result_df[col] = result_df[col].apply(_make_html_links)
            
            result_df = result_df[final_cols]
            
            html_style = """
            <style>
                table { border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
                tr:nth-child(even) { background-color: #f2f2f2; }
                th { background-color: #4CAF50; color: white; }
                a { color: #1a73e8; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
            """
            
            html_table = result_df.to_html(index=False, escape=False)
            
            with open(args.output, 'w') as f:
                f.write(html_style + html_table)
        else:
            # For TSV: append row immediately
            row_df = pd.DataFrame([row_data])[final_cols]
            row_df.to_csv(args.output, sep='\t', index=False, mode='a', header=False)
    
    if is_html_output:
        print(f"Done! Results saved to HTML file: {args.output}")
        print(f"Individual reports saved to: {reports_dir}")
    else:
        print(f"Done! Results saved to TSV file: {args.output}")

if __name__ == "__main__":
    main()
