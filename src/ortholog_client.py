import requests
from tenacity import retry, stop_after_attempt, wait_exponential

class OrthologClient:
    def __init__(self):
        self.api_url = "https://biit.cs.ut.ee/gprofiler/api/orth/orth/"
        # Map common names to gProfiler slugs
        self.slug_map = {
            "maize": "zmays",
            "zea mays": "zmays",
            "rice": "osativa",
            "oryza sativa": "osativa",
            "arabidopsis": "athaliana",
            "arabidopsis thaliana": "athaliana",
            "sorghum": "sbicolor",
            "sorghum bicolor": "sbicolor"
        }

    def get_slug(self, species_name):
        return self.slug_map.get(species_name.lower().strip(), species_name.lower().strip())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_orthologs(self, gene_id, source_organism, target_organism):
        """
        Get orthologs for a gene ID from source to target.
        """
        payload = {
            "organism": source_organism,
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
            print(f"Error fetching orthologs from g:Profiler for {gene_id} ({source_organism}->{target_organism}): {e}")
            return []

    def get_orthologs_for_gene(self, gene_id, gene_symbol=None, source_organism="maize"):
        """
        Get compatible orthologs based on source organism.
        Logic:
        - Maize (or others) -> arabidopsis + rice
        - Rice -> arabidopsis
        - Arabidopsis -> rice
        """
        source_slug = self.get_slug(source_organism)
        athaliana_slug = "athaliana"
        osativa_slug = "osativa"
        
        orths = {
            "arabidopsis": [],
            "rice": []
        }

        # 1. Determine which targets to fetch
        fetch_arabidopsis = True
        fetch_rice = True
        
        if source_slug == osativa_slug:
            fetch_rice = False # Don't fetch self
        elif source_slug == athaliana_slug:
            fetch_arabidopsis = False # Don't fetch self

        # 2. Fetch
        if fetch_arabidopsis:
            orths["arabidopsis"] = self.get_orthologs(gene_id, source_slug, athaliana_slug)
        
        if fetch_rice:
            orths["rice"] = self.get_orthologs(gene_id, source_slug, osativa_slug)

        # 3. Fallback to Symbol if ID yielded nothing
        # Only try if we expected results but got none for ALL enabled targets
        found_any = (len(orths["arabidopsis"]) > 0 if fetch_arabidopsis else False) or \
                    (len(orths["rice"]) > 0 if fetch_rice else False)
        
        if gene_symbol and not found_any:
             print(f"  [Ortholog Fallback] No results for ID {gene_id}. Trying Symbol {gene_symbol}...")
             if fetch_arabidopsis:
                orths["arabidopsis"] = self.get_orthologs(gene_symbol, source_slug, athaliana_slug)
             if fetch_rice:
                orths["rice"] = self.get_orthologs(gene_symbol, source_slug, osativa_slug)

        return orths

    def validate_species(self, species_name):
        """
        Runtime check to see if we can query this species.
        Returns (is_valid, slug_or_error_msg)
        """
        slug = self.get_slug(species_name)
        # We'll try a dummy query (using a made-up gene ID) just to see if the API rejects the organism slug
        # invalid organism usually returns 400 or 500
        payload = {
            "organism": slug,
            "target": "athaliana",
            "query": ["DUMMY_GENE_CHECK"]
        }
        try:
            response = requests.post(self.api_url, json=payload)
            # If 200, it accepted the organism (just found 0 results)
            if response.status_code == 200:
                return True, slug
            else:
                 return False, f"API Error: {response.status_code}"
        except Exception as e:
            return False, str(e)

