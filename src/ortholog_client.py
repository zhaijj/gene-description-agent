import requests
from tenacity import retry, stop_after_attempt, wait_exponential

class OrthologClient:
    def __init__(self):
        self.api_url = "https://biit.cs.ut.ee/gprofiler/api/orth/orth/"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_orthologs(self, gene_id, target_organism):
        """
        Get orthologs for a gene ID in a specific target organism.
        target_organism: 'athaliana' or 'osativa'
        Returns list of dicts: [{'id': '...', 'name': '...'}]
        """
        payload = {
            "organism": "zmays",
            "target": target_organism,
            "query": [gene_id]
        }
        
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            orthologs = []
            if 'result' in data:
                for item in data['result']:
                    orth_id = item.get('ortholog_ensg')
                    orth_name = item.get('name')
                    
                    if orth_id and orth_id != "N/A":
                        entry = {'id': orth_id, 'name': orth_name if orth_name != "N/A" else orth_id}
                        orthologs.append(entry)
            
            # Deduplicate by ID
            unique_orthologs = {v['id']: v for v in orthologs}.values()
            return list(unique_orthologs)
        except Exception as e:
            print(f"Error fetching orthologs from g:Profiler for {gene_id} -> {target_organism}: {e}")
            return []

    def get_orthologs_for_gene(self, gene_id, gene_symbol=None):
        """
        Get Arabidopsis and Rice orthologs for a maize gene.
        Tries ID first, then Symbol if provided.
        """
        orths = {
            "arabidopsis": self.get_orthologs(gene_id, "athaliana"),
            "rice": self.get_orthologs(gene_id, "osativa")
        }

        # Fallback to Symbol if ID yielded nothing and Symbol is available
        if gene_symbol and not orths['arabidopsis'] and not orths['rice']:
             print(f"  [Ortholog Fallback] No results for ID {gene_id}. Trying Symbol {gene_symbol}...")
             orths = {
                "arabidopsis": self.get_orthologs(gene_symbol, "athaliana"),
                "rice": self.get_orthologs(gene_symbol, "osativa")
             }

        return orths
