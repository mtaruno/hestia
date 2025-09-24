# Hestia: Copilot for Parents

**NOTE : Hestia is currently under migration process. There is an internal code base and repo and currently am in the process of migration, here is a rough implementation plan for that**

| Task                                                                         |
| ---------------------------------------------------------------------------- |
| Set up all the OpenAI key and Neo4j keys in Firebase parameter store         |
| Rebuild the KG properly in the Neo4j database                                |
| Test the retrieval script locally; make sure retrieval algorithm makes sense |
| Run the firebase locally with emulator                                       |
| Deploy firebase locally with the front-end on my iPhone                      |
| Publish to TestFlight                                                        |

--- 


Premise for Hestia: I believe the way we are going to get advice (including parental advice) from digital products is evolving as AI gets more intelligent and we enable it in an accessible form via mobile application development. Hence, Hestia:

<img width="1972" height="2554" alt="CleanShot 2025-09-18 at 00 43 09@2x" src="https://github.com/user-attachments/assets/e27f59af-17c4-48b1-bfed-c75a29809f9d" />



Here's a brief technical walkthrough of Hestia:

### Data sources

It all starts from data. Knowledge is data. To simulate parental expert advice for how this idea would work, we created this [form](https://docs.google.com/forms/d/1cIy_gFtIcu9ViFmjQC2atbIepl9q_Ta0fpTr5oKKmGY/edit) where anyone could input a data source. 

This dataset is a curated collection of expert-backed parenting advice for ages **2–6** (and “Any”), contributed via a structured form. Each row captures **provenance**, **actionable guidance**, and **rich facets** (topic, age, style, temporal context, scenario), making it ideal for **GraphRAG** (graph-augmented retrieval) and **LLM grounding**. The following is a data dictionary, as long as how this maps to the semantic Knowledge Graph I store in Neo4J. 

| Field                                              | Purpose                    | Examples                                                                  | Graph Node           | Property      | Relationship          |
| -------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------- | -------------------- | ------------- | --------------------- |
| What type of source is this?                       | Provenance type            | Book, Website Article, Podcast, YouTube / Video, Expert Q&A / Forum       | **Source**           | type          | CITED_FROM            |
| Source Name                                        | Human-readable source      | HealthyChildren.org, CHOP, The Whole-Brain Child                          | **Source**           | name          | CITED_FROM            |
| Source URL                                         | Citation link              | https://childmind.org/...                                                 | **Source**           | url           | CITED_FROM            |
| Author                                             | Author(s)                  | Dr. Daniel J. Siegel                                                      | **Author**           | name          | WRITTEN_BY            |
| Credentials / Area of Expertise                    | Credibility signals        | Ph.D. in Clinical Psychology                                              | **Author**           | credentials   | WRITTEN_BY            |
| Title of Advice                                    | Entry title                | Connect Before You Redirect                                               | **Advice**           | title         | -                     |
| Paragraph or Advice Text                           | Actionable content         | One paragraph of guidance                                                 | **Advice**           | content, name | -                     |
| Main Topic Entities                                | Primary domain tags        | Tantrums, Sleep, Perfectionism, Screen Time                               | **Topic**            | name          | HAS_TOPIC             |
| Sub-entities                                       | Secondary tags (comma-sep) | Aggressive Behavior, Bedtime Routine                                      | **SubTopic**         | name          | HAS_SUBTOPIC          |
| Intervention Suggested (Actionable)                | Concrete actions           | “Offer two choices”, “Positive reinforcement”                             | **ActionableAdvice** | content, name | HAS_ACTIONABLE_ADVICE |
| Child Age Range                                    | Facet for filtering        | 2, 3, 4, 5, 6, Any                                                        | **AgeGroup**         | age_label     | RECOMMENDED_FOR       |
| Guidance Style                                     | Tone/stance (multi-select) | Empathic, Directive, Playful, Scientific, Adaptive, Reflective, Practical | **GuidanceStyle**    | style_name    | USES_STYLE            |
| Temporal Context                                   | Time-of-day/use window     | Morning, Mealtime, Bedtime                                                | **TemporalContext**  | context_label | SUGGESTED_AT          |
| What scenario would this be especially useful for? | Fit/edge cases             | “Public tantrums”, “Culturally sensitive bedtime rituals”                 | **ScenarioNote**     | summary, name | HAS_SCENARIO_NOTE     |

The knowledge graph represents key aspects of parenting, including information about parents, children, parenting styles, discipline methods, emotional bonds, and parenting practices. It also captures how these elements interact to influence child development.


### KG Builder

|               |                                                                                                                                      |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Nodes:        | Advice, Topic, SubTopic, AgeGroup, GuidanceStyle, TemporalContext, ScenarioNote, Author, Source, ActionableAdvice                    |
| Relationships | HAS_TOPIC, HAS_SUBTOPIC, RECOMMENDED_FOR, USES_STYLE, SUGGESTED_AT, HAS_SCENARIO_NOTE, WRITTEN_BY, CITED_FROM, HAS_ACTIONABLE_ADVICE |


| KG Builder Files  |                                                                                                                                                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `neo4j_builder_1` | - Processes research papers as raw text<br>- Uses academic parenting schema (Parent, Child, ParentingStyle, etc.)<br>- Designed for unstructured text extraction                                                                                  |
| `neo4j_builder_2` | - Processes structured JSONL data (from your CSV)<br>- Uses practical advice schema (Advice, Topic, AgeGroup, ActionableAdvice, etc.)<br>- Matches your brain.csv structure perfectly<br>- Handles the tags and metadata from your CSV conversion |

| Retriever Files               |                                                                                                                                                                                                                                                                                                                                                                          


### KG Retriever

| Pros                                     |                                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Multi-hop traversal**                  | - Retrieves connected entities (topics, age groups, actionable advice)<br>                                                                                                                                                                                                                                                           |
| **Hybrid Search: Semantic + structural** | - Combines Vector search finds semantically similar advice and graph traversal enriched with structured metadata                                                                                                                                                                                                                     |
| **Rich context**                         | - Captures parenting advice structure well<br>- Age groups, guidance styles enable precise filtering<br>- ActionableAdvice nodes provide concrete steps<br>- Returns comprehensive metadata for each advice piece<br>- Each advice piece comes with topics, age ranges, scenarios<br>- Metadata enables personalized recommendations |
| **Score boosting**                       | - Prioritizes advice with actionable content                                                                                                                                                                                                                                                                                         |
| **Flexible filtering**                   | - Can filter by age, guidance style, etc.                                                                                                                                                                                                                                                                                            |
| Scalable Design                          | - Can handle large advice datasets<br>- Vector index enables fast similarity search                                                                                                                                                                                                                                                  |

| Cons                            |                                              |
| ------------------------------- | -------------------------------------------- |
| **Limited graph reasoning**     | Mostly 1-hop relationships from Advice nodes |
| **No cross-advice connections** | Advice nodes aren't connected to each other  |
| Doesn't involve research papers |                                              |



                                                                     |

| Retriever Files               |                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `neo4j_graphrag-retriever.py` | 1. **Schema alignment** - Uses exact schema from neo4j_builder_2 (Advice, Topic, AgeGroup, ActionableAdvice)<br>2. **Rich retrieval** - Gets full context: topics, age groups, actionable advice, scenarios<br>3. **Semantic + structural** - Combines vector similarity with graph relationships<br>4. **Score boosting** - Prioritizes advice with actionable content<br>5. **Complete pipeline** - Retrieval → formatting → LLM generation |
