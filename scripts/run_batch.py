import os
import sys
import pandas as pd
import argparse
import re
import time
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
        
    print("Initializing Agent...")
    agent = GeneDescriptionAgent(api_key=api_key, email=email)
    
    results = []
    
    print(f"Processing {len(df)} genes...")
    
    for index, row in df.iterrows():
        gene_id = str(row[id_col]).strip()
        species = str(row[species_col]).strip()
        
        print(f"[{index+1}/{len(df)}] Processing {gene_id} ({species})...")
        
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
            results.append(row_data)
            
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
            results.append(row_data)
        
        # Rate limit friendly status update
        # time.sleep(1) 

    # Save Output
    result_df = pd.DataFrame(results)
    # Reorder columns to be nice
    base_cols = ["GeneID", "Species", "Summary"]
    kw_cols = [f"Keyword {i+1}" for i in range(5)]
    ref_cols = [f"Reference {i+1}" for i in range(5)]
    status_col = ["Status"]
    
    # We don't filter columns yet if we need FullReport for HTML
    
    if args.output.endswith('.html'):
        # Linked Summaries Logic
        
        # 1. Create reports folder
        output_dir = os.path.dirname(os.path.abspath(args.output))
        output_basename = os.path.splitext(os.path.basename(args.output))[0]
        reports_dir_name = f"{output_basename}_reports"
        reports_dir = os.path.join(output_dir, reports_dir_name)
        
        os.makedirs(reports_dir, exist_ok=True)
        print(f"Created reports directory: {reports_dir}")
        
        # 2. Iterate through rows to save reports and update Summary link
        for index, row in result_df.iterrows():
            gene_id = str(row['GeneID']).strip()
            # Sanitize filename
            safe_id = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', gene_id)
            report_filename = f"{safe_id}.html"
            report_path = os.path.join(reports_dir, report_filename)
            
            # Simple HTML wrapper for the report
            # Convert simple markdown to HTML (very basic)
            # Or just wrap the markdown in <pre> or use a simple converter if desired.
            # Using a simple <pre> style for now or basic replacement for headers/bold/links.
            
            def simple_md_to_html(md_text):
                # Basic conversion
                html = md_text
                # Headers
                html = re.sub(r'^# (.*)', r'<h1>\1</h1>', html, flags=re.MULTILINE)
                html = re.sub(r'^## (.*)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
                html = re.sub(r'^### (.*)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
                # Bold
                html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
                # Links
                html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)
                # Lists
                html = re.sub(r'^\- (.*)', r'<li>\1</li>', html, flags=re.MULTILINE)
                # Newlines to <br> (except near tags)
                html = html.replace('\n', '<br>')
                return html

            report_content = row.get('FullReport', '')
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
                
            # Update Summary column with link
            # Use relative path suitable for browser
            link = f'<a href="./{reports_dir_name}/{report_filename}" target="_blank">View Full Report</a>'
            result_df.at[index, 'Summary'] = link

        # 3. Finalize Main Table
        # Convert hyperlinks in Reference columns to HTML anchors
        def _make_html_links(text):
            if not isinstance(text, str): return text
            # 1. Replace [Title](URL) with <a href="URL" target="_blank">Title</a>
            text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
            # 2. auto-link bare URLs that are NOT inside an href attribute (simple heuristic)
            # Find http/https that is NOT preceded by 'href="' or '>'. 
            # This is tricky with regex. 
            # Safer approach: matching non-linked URLs. 
            # Negative lookbehind is good: (?<!href=")
            url_pattern = r'(?<!href=")(?<!">)(https?://[^\s<"]+)'
            text = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', text)
            return text
            
        for col in ref_cols:
            if col in result_df.columns:
                result_df[col] = result_df[col].apply(_make_html_links)
        
        # Filter columns now
        final_cols = base_cols + kw_cols + ref_cols + status_col
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
            
        print(f"Done! Results saved to HTML file: {args.output}")
        print(f"Individual reports saved to: {reports_dir}")
        
    else:
        # Default TSV
        # Filter colums
        final_cols = base_cols + kw_cols + ref_cols + status_col
        result_df = result_df[final_cols]
        result_df.to_csv(args.output, sep='\t', index=False)
        print(f"Done! Results saved to TSV file: {args.output}")

if __name__ == "__main__":
    main()
