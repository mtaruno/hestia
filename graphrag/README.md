

A lot of the high level framework and terminology came in this document came from [this survey paper](https://arxiv.org/pdf/2501.13958).

There are two stages:
1. [Knowledge Organization with Graphs](./kq_builder/README.md)
2. [Knowledge Graph Retrieval](./kg_query/README.md)

### Neo4j Server
Using the MacOS Neo4J Desktop App - Using AuraDB. 

### Vision for Graph RAG
Goal of the Graph RAG - To support parents in the following **scenarios**: (RQ: Are these the most important scenarios?)
1. Managing parental stress and burnout
2. Navigating marriage and co-parenting dynamics
3. Life as a stay at home parent - identity and isolation
4. Family dynamics and relationships
5. Balancing work, career, and purpose as a parent
6. Adjusting to a child's special needs and health condition
7. Developing advocacy skills for your child

It is not necessarily certain that Graph RAG would be enough to achieve this functionality. 


## Knowledge Graph Development (Parenting-Specific Dataset)

### Knowledge Organization

KG can be using NLP + Data Mining instead of LLM to make it more relevant.

To do this, crafting the correct knowledge base is important. We should include:
- Base 30 bodies of knowledge to extensively cover the top 10 prioritized scenarios above
- Web search (?): But I think parenting is relatively timeless. 

There are two types of knowledge organization: 
1. Graphs for knowledge indexing (GraphRetriever, GNN-ret, etc) 
2. Graphs as knowledge carriers both from corpus (LightRAG, GraphRAG, GraphReader) or existing knowledge graphs (RoG, KnowGPT). There are also hybrid approaches (e.g. CodexGraph).

Problems with RAG: Knowledge cutoff, hallucinations, implicit knowledge (failure to accurately attribute sources of info), lack of specific technical knowledge required for specialized fields

Can take from authorized APIs like SCOPUS, Semantic Scholar, Office of Scientific and Technical Information (or more parenting-specific corpus)
- Extract common bigrams
- Pruning strategies to take away irrelevant documents. Human in the Loop: Scalability through clustering
- Features from T-ELF and metadata are mapped ->  Neo4j KG (triplets of head, entity, tail relations)
- Unsupervised learning to get tags that are better than author chosen tags.
- We still need a **vector store** for highly relevant content (perhaps for the core documents)

1. Ontology: Give relevant subgraphs to improve QA accuracy that preserve information in a structured way.
2. Corpus building

We start with 30 research papers that we think are relevant. 

Metadata tagging. (Important for improving trust). 

Utilize both metadata and full texts. Human in the loop.


### Dataset Construction
Dataset construction is important (although rarely outlined in literature). Context search.

### Automated quality assurance frameworks
Cross validation, statistical analysis, ML to identify inconsistencies, remove redundancies, and validate factual accuracy. 

### Continuous Knowledge Expansion
Automated web crawling, API integrations, expert feedback loops.

### Knowledge Conflict 

How do we manage conflicting information and maintain knowledge consistency? 

Evaluate source reliability, identify contradictory statements, detemine most probable accurate information. 

Uncertainty modeling, probabilistic reasoning frameworks, confidence scores.


### Schema 
Defining a schema: https://neo4j.com/docs/getting-started/cypher-intro/schema/

Example schema: 
NODE TYPES
- Person: name, role, temperament, age (e.g. Father, Mother, Child)
- Family (Optional): Household as single entity or group. 
- Activities: name (building LEGO, soccer, etc.)
- Goals: goalDescription, timeFrame
- Challenges: description, category (emotional regulation, picky eating)

RELATIONSHIPS
- HAS_CHILD (connecting Parent node to Child node)
- PART_OF_HOUSEHOLD (Person -> Family)
- LIKES_ACTIVITY/ENJOYS_ACTIVITY/DISLIKES_ACTIVITY (Child -> Activity)
- HAS_CHALLENGE (Child -> Challenge)
- WORKING_ON_GOAL (Person/Family -> Goal)