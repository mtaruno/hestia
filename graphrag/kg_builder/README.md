
Right now, we are not making user specific graphs. We are starting with main graphs that don't personalize to the user. I think user specific information can be implemented as a simple memory module. GraphRAG is similar to building our own customized search engine for AI to use and get related information about. RQ: Why doesn't Google have this available? 

1. Get the raw data (research papers) Semantic scholar scraper -> JSONL entries
2. Do some analysis on the raw data -> 
   1. (NLP work) Add metadata in the JSON
3. JSONL entries -> Populate Neo4J Aura Instance with nodes, relationships
4. Sample queries from Cypher
5. Index Database

Most basic index Database

Entities:
- Lexical: Paper , Chunks (outgoing nodes from Paper)
- Domain: :Parent (stay at home mom, working father), :Scenario, :Tag, :Age

Relationships:
- (:Paper) - [:HAS_CHUNK] -> (:Chunk)
- (:Parent) - [:HAS_TAG] -> (:Tag)
- (:Chunk) - [:MENTIONS_SCENARIO] -> (:Scenario)
- (:Chunk) - [:MENTIONS_PARENT] -> (:Parent)
- (:Scenario) - [:RELATED_TO] -> (:Tag)
- (:Parent) - [:RELATED_TO] ->(:Scenario)

Examples
```json
{"title": "The influence of parenting and temperament on empathy development in toddlers.", "year": 2019, "abstract": "Empathy is a critical ability in developing relationships, ...", "authors": ["K. Wagers", "..."], "paperId": "8b2dd024755800a9bfb86029f56389cc8e81b327"}
```

1. Additional metadata

Paper node, alongside its **properties**. 
```json
{
    "title": "Social withdrawal in children moderates...",
    "year": 2014,
    "abstract": "Empathy is a critical ability in developing relationships,...",
    "authors": ["M. Zarra-Nezhad", "N. Kiuru"...],
    "paperId": "1580330cfd231f5f0a107e2e3bfd0f1c117dceea",
    // additional fields: 
    "metadata": {
        // "study_type": "longitudinal",
        // "sample_size": 314,
        // "population": "children_grades_1_3",
        // "measures": ["prosocial_skills", "internalizing_behaviors", "externalizing_behaviors"]
    },,
  ,
        "source": "manual_pdf_extraction",
        "extraction_date": "2024-03-20",
    "label": "Article",
    "tags" : [...] // Can generate tags using NER perhaps 
}

// excluded: 
  "full_text": {
        "content": "complete paper text",
        "sections": {
            "introduction": "...",
            "methods": "...",
            "results": "...",
            "discussion": "...",
            ...
        }
    }
```

Perform semantic chunking to get relevant chunks that are outgoing from paper for the papers that are available

```json
{
    "title": "Social withdrawal in children moderates...",
    "chunk" : "..."
}
```

