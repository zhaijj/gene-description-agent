import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from .ncbi_client import NCBIClient
from .ortholog_client import OrthologClient

load_dotenv()

class GeneDescriptionAgent:
    def __init__(self, model_name="gemini-2.5-pro"):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            print("Warning: GOOGLE_API_KEY not found in environment variables.")
        else:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = model_name
        
        self.ncbi_client = NCBIClient()
        self.ortholog_client = OrthologClient()

    def generate_description(self, gene_id):
        """
        Generates a description for a maize gene ID.
        """
        print(f"--- Starting Analysis for {gene_id} ---")
        
        # 1. Fetch Maize Metadata (NCBI)
        print("Fetching Maize Metadata...")
        maize_meta = self.ncbi_client.get_gene_metadata(gene_id)
        if not maize_meta:
            # Fallback if ID is not found directly, maybe structure partial metadata
            maize_meta = {"uid": "", "symbol": gene_id, "description": "", "synonyms": [], "organism": "Zea mays"}
        
        print(f"Found Metadata: {maize_meta['symbol']} ({maize_meta['description']})")

        # 2. Fetch Orthologs
        print("Fetching Orthologs...")
        orthologs = self.ortholog_client.get_orthologs_for_gene(gene_id, gene_symbol=maize_meta.get('symbol'))
        
        # 3. Enrich Orthologs with Metadata (Synonyms from NCBI)
        # We need synonyms to search PubMed effectively
        def enrich_orthologs(orth_list, organism):
            enriched = []
            for o in orth_list:
                print(f"  Enriching {organism} ortholog: {o['id']}")
                meta = self.ncbi_client.get_gene_metadata(o['id'], organism)
                if meta:
                    o['synonyms'] = meta.get('synonyms', [])
                    o['description'] = meta.get('description', '')
                else:
                    o['synonyms'] = []
                enriched.append(o)
            return enriched

        print("Enriching Arabidopsis Orthologs...")
        orthologs['arabidopsis'] = enrich_orthologs(orthologs['arabidopsis'], "Arabidopsis thaliana")
        print("Enriching Rice Orthologs...")
        orthologs['rice'] = enrich_orthologs(orthologs['rice'], "Oryza sativa")

        # 4. Search PubMed
        print("Searching PubMed...")
        documents = []
        
        # 4a. Maize Search
        # Query: (GeneID OR Symbol OR Synonyms) AND (Zea mays OR Maize)
        maize_terms = [gene_id]
        if maize_meta['symbol'] and maize_meta['symbol'] != gene_id: maize_terms.append(maize_meta['symbol'])
        maize_terms.extend(maize_meta['synonyms'])
        # Filter empty and duplicates
        maize_terms = list(set([t for t in maize_terms if t]))
        
        
        maize_query_group = " OR ".join([f"({t})" for t in maize_terms])
        maize_query = f"({maize_query_group}) AND (Zea mays OR Maize)"
        print(f"  [PubMed Query - Maize] {maize_query}")
        
        docs = self.ncbi_client.search_pubmed(maize_query, max_results=5)
        for d in docs: d['source'] = 'Maize Search'
        documents.extend(docs)

        # 4b. Arabidopsis Search
        for o in orthologs['arabidopsis']:
            terms = [o['id']]
            if o['name'] and o['name'] != o['id']: terms.append(o['name'])
            terms.extend(o.get('synonyms', []))
            terms = list(set([t for t in terms if t]))
            
            q_group = " OR ".join([f"({t})" for t in terms])
            query = f"({q_group}) AND (Arabidopsis OR thaliana)"
            print(f"  [PubMed Query - Ara] {query}")
            docs = self.ncbi_client.search_pubmed(query, max_results=3)
            for d in docs: d['source'] = f"Arabidopsis ({o['name']})"
            documents.extend(docs)

        # 4c. Rice Search
        for o in orthologs['rice']:
            terms = [o['id']]
            if o['name'] and o['name'] != o['id']: terms.append(o['name'])
            terms.extend(o.get('synonyms', []))
            terms = list(set([t for t in terms if t]))
            
            q_group = " OR ".join([f"({t})" for t in terms])
            query = f"({q_group}) AND (Oryza sativa OR rice)"
            print(f"  [PubMed Query - Rice] {query}")
            docs = self.ncbi_client.search_pubmed(query, max_results=3)
            for d in docs: d['source'] = f"Rice ({o['name']})"
            documents.extend(docs)

        # Deduplicate documents
        unique_docs = {}
        for d in documents:
            if d['pmid'] not in unique_docs:
                unique_docs[d['pmid']] = d
        documents = list(unique_docs.values())
        
        print(f"Found {len(documents)} unique articles.")

        # 5. Generate Summary with Gemini
        return self._summarize(gene_id, maize_meta, orthologs, documents)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
    def _run_gemini(self, prompt):
        return self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

    def _summarize(self, gene_id, maize_meta, orthologs, documents):
        if not self.api_key:
            return "Error: Gemini API Key not found."

        # Format Context
        orth_text = ""
        for sp, o_list in orthologs.items():
            names = [f"{o['name']} ({o['id']})" for o in o_list]
            orth_text += f"- {sp.title()}: {', '.join(names)}\n"

        doc_text = ""
        for i, d in enumerate(documents):
            doc_text += f"[{i+1}] Title: {d['title']}\n"
            doc_text += f"    Source: {d['source']} | PMID: {d['pmid']}\n"
            doc_text += f"    Abstract: {d['abstract'][:1500]}\n\n" # Truncate long abstracts

        prompt = f"""
        You are an expert plant biologist. Identify the function of Maize Gene {gene_id}.
        
        ### Gene Information
        - ID: {gene_id}
        - Symbol: {maize_meta['symbol']}
        - Synonyms: {', '.join(maize_meta['synonyms'])}
        - Description: {maize_meta['description']}
        
        ### Orthologs
        {orth_text}
        
        ### Literature Abstracts
        {doc_text}
        
        ### Task
        You are an expert plant biologist. Your goal is to generate a deep, specific, and up-to-date summary of the maize gene {gene_id}, matching the quality of a "Google AI Overview".

        1. **Deep Search & Synthesis**:
           - Use **Google Search** aggressively to find the most recent information (especially papers from 2023-2025).
           - **Crucial**: Search for and identify any **Aliases/Common Names** (e.g., is it called DSD1? ZmICEb? etc.). If found, prominently mention them.
           - Look for **Specific Mechanisms**: Don't just say "stomatal development". Say *how* (e.g., "controls GMC maturation", "arrests at Stage III").
           - Look for **Phenotypes**: What happens if it's mutated? (e.g., drought tolerance, stomatal density changes).
        
        2. **Summarize** (5 Sentences):
           - Integrate the NCBI metadata, Orthologs, PubMed abstracts, and **Google Search findings**.
           - Start with the identities/aliases.
           - Explain the specific molecular and physiological function.
           - Mention abiotic stress roles (Drought, Cold, etc.).
        
        3. **Keywords**: 5 specific terms.
        
        4. **References**: List papers/URLs.
        
        ### Output Format
        Return Markdown.
        **Function Summary**:
        [5 sentences...]
        
        **Keywords**:
        [Keyword 1], [Keyword 2], ...
        
        **Key References**:
        - [Title](https://pubmed.ncbi.nlm.nih.gov/PMID/)
        """

        try:
            response = self._run_gemini(prompt)
            return response.text
        except Exception as e:
            return f"Error generating summary: {e}"
