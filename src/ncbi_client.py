import os
from Bio import Entrez
from tenacity import retry, stop_after_attempt, wait_exponential

class NCBIClient:
    def __init__(self, email="jz963@cornell.edu"):
        Entrez.email = email
        self.max_retries = 3

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_gene_metadata(self, gene_query, organism="Zea mays"):
        """
        Search NCBI Gene DB for a gene (by ID or name) and return metadata.
        Returns: {'id': '...', 'symbol': '...', 'synonyms': [...], 'description': '...'}
        """
        # 1. Search for Gene ID
        try:
            # Query format: "Zm00001eb126570[All Fields] AND Zea mays[Organism]"
            term = f"{gene_query}[All Fields] AND {organism}[Organism]"
            print(f"Searching NCBI Gene for: {term}")
            handle = Entrez.esearch(db="gene", term=term, retmax=5)
            record = Entrez.read(handle)
            handle.close()

            if not record["IdList"]:
                print(f"No gene found for {gene_query}")
                return None
            
            # Use the first hit
            gene_uid = record["IdList"][0]

            # 2. Fetch Details
            handle = Entrez.esummary(db="gene", id=gene_uid)
            summary_record = Entrez.read(handle)
            handle.close()

            if 'DocumentSummarySet' in summary_record and 'DocumentSummary' in summary_record['DocumentSummarySet']:
                doc = summary_record['DocumentSummarySet']['DocumentSummary'][0]
                
                # Parse Synonyms (Usually string separated by semicolon or list)
                # Structure checks needed as Biopython returns dicts
                synonyms_raw = doc.get("OtherAliases", "")
                synonyms = [s.strip() for s in synonyms_raw.split(',')] if synonyms_raw else []
                # Also check 'OtherDesignations' sometimes?

                return {
                    "uid": gene_uid,
                    "symbol": doc.get("Name", ""),
                    "description": doc.get("Description", ""),
                    "synonyms": synonyms,
                    "organism": doc.get("Organism", {}).get("ScientificName", organism)
                }

            return None

        except Exception as e:
            print(f"Error fetching gene metadata from NCBI: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_pubmed(self, query, max_results=5):
        """
        Search PubMed for query string and return abstracts.
        """
        # print(f"Searching PubMed for: {query}")
        try:
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="relevance")
            record = Entrez.read(handle)
            handle.close()
            
            ids = record["IdList"]
            if not ids:
                return []

            handle = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="abstract", retmode="xml")
            records = Entrez.read(handle)
            handle.close()

            documents = []
            if 'PubmedArticle' in records:
                for article in records['PubmedArticle']:
                    citation = article['MedlineCitation']
                    pmid = str(citation['PMID'])
                    article_data = citation['Article']
                    title = article_data.get('ArticleTitle', 'No Title')
                    
                    abstract_list = article_data.get('Abstract', {}).get('AbstractText', [])
                    abstract = " ".join(abstract_list) if abstract_list else "No Abstract Available."

                    doi = ""
                    if 'ELocationID' in article_data:
                        for eloc in article_data['ELocationID']:
                            if eloc.attributes.get('EIdType') == 'doi':
                                doi = str(eloc)
                                break
                    
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    if doi:
                        url = f"https://doi.org/{doi}"

                    documents.append({
                        'title': title,
                        'url': url,
                        'abstract': abstract,
                        'pmid': pmid,
                        'doi': doi
                    })
            
            return documents

        except Exception as e:
            print(f"Error searching PubMed: {e}")
            return []
