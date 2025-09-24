import json
import neo4j
from dotenv import load_dotenv
from openai import AzureOpenAI
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional,Union
import asyncio
from pathlib import Path

from neo4j_graphrag.llm import AzureOpenAILLM, OpenAILLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.generation.prompts import ERExtractionTemplate
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from graphrag.config import Config
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline

@dataclass
class GraphSchema:
    """Represents the knowledge graph schema"""
    nodes: List[str]
    relationships: List[str]

    def to_dict(self) -> Dict:
        return {
            "nodes": self.nodes,
            "relationships": self.relationships
        }

class PromptTemplate:
    """Manages prompt templates for knowledge graph construction using ERExtractionTemplate"""

    def __init__(self, schema: GraphSchema):
        self.schema = schema
        self.template = ERExtractionTemplate()

    def format_prompt(self, text: str, examples: str) -> str:
        """Format the prompt template with the given text and examples"""
        # Convert our schema to the format expected by ERExtractionTemplate
        schema_dict = {
            "nodes": [{"label": node, "description": f"A {node} node"} for node in self.schema.nodes],
            "relationships": [
                {
                    "label": rel,
                    "description": f"A {rel} relationship",
                    "source": "Advice",  # All relationships start from Advice
                    "target": rel.split("_")[-1] if "_" in rel else "Topic"  # Target is based on relationship name
                }
                for rel in self.schema.relationships
            ]
        }

        return self.template.format(schema=schema_dict, examples=examples, text=text)

    def load_jsonl(self, file_path):
        resources = []
        with open(file_path, encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                try:
                    # Skip empty lines
                    if not line.strip():
                        continue
                    resource = json.loads(line)
                    resources.append(resource)
                    # Debug the first few resources
                    if i <= 3:
                        logging.debug(f"Resource {i} structure: {json.dumps(resource, indent=2)}")
                except json.JSONDecodeError as e:
                    logging.error(f"Error parsing line {i}: {e}")
        logging.info(f"Loaded {len(resources)} resources from {file_path}")
        return resources

class KnowledgeGraphBuilder:
    """Manages the construction of the knowledge graph"""

    def __init__(self, config: Config):
        self.config = config
        self.schema = GraphSchema(
            nodes=[
                "Advice", "Topic", "SubTopic", "AgeGroup", "GuidanceStyle",
                "TemporalContext", "ScenarioNote", "Author", "Source", "ActionableAdvice"
            ],
            relationships=[
                "HAS_TOPIC", "HAS_SUBTOPIC", "RECOMMENDED_FOR", "USES_STYLE",
                "SUGGESTED_AT", "HAS_SCENARIO_NOTE", "WRITTEN_BY", "CITED_FROM",
                "HAS_ACTIONABLE_ADVICE"
            ]
        )
        self.prompt_template = PromptTemplate(self.schema)
        self.neo4j_driver = neo4j.GraphDatabase.driver(config.URI, auth=config.AUTH)
        self.llm = self._initialize_llm()
        self.embedder = OpenAIEmbeddings()

    def _initialize_llm(self) -> Union[AzureOpenAILLM, OpenAILLM]:
        """Initialize the language model based on configuration"""
        return OpenAILLM(
            model_name=self.config.model_name,
            model_params={"temperature": 0.0}  # Use 0 temperature for more deterministic outputs
        )

    def _create_pipeline(self) -> SimpleKGPipeline:
        """Create a new pipeline instance with the ERExtractionTemplate"""
        # Create a pipeline with text_splitter=None to completely disable text splitting
        # This ensures the full text content is preserved in the knowledge graph
        logging.info("Creating pipeline with text_splitter=None to preserve full text content")
        return SimpleKGPipeline(
            llm=self.llm,
            driver=self.neo4j_driver,
            # Completely disable text splitting to preserve the full text content
            text_splitter=None,
            embedder=self.embedder,
            entities=self.schema.nodes,
            relations=self.schema.relationships,
            prompt_template=self.prompt_template.template,  # Pass the ERExtractionTemplate object
            from_pdf=False
        )

    def _extract_entities_from_tags(self, resource: Dict) -> Dict:
        """Extract entities from the tags field of a resource"""
        entities = []
        relationships = []

        # Create the Advice node as the central node with full text content
        advice_id = "0"
        advice_properties = {
            "title": resource.get('title', 'Unknown Advice')
        }

        # Add full text content if available - store in both name and content properties
        # to ensure compatibility with retrievers that might use either property
        if 'full_text' in resource and isinstance(resource['full_text'], dict) and 'content' in resource['full_text']:
            full_text = resource['full_text']['content']
            advice_properties["content"] = full_text
            advice_properties["name"] = full_text
            logging.info(f"Added full text content ({len(full_text)} chars) to Advice node")
        else:
            # If no full text is available, use the title as the name
            advice_properties["name"] = advice_properties["title"]
            logging.warning(f"No full text content available for {advice_properties['title']}")

        advice_node = {
            "id": advice_id,
            "label": "Advice",
            "properties": advice_properties
        }
        entities.append(advice_node)

        # Create a dedicated ActionableAdvice node if available
        if 'actionable_advice' in resource and resource['actionable_advice']:
            actionable_id = str(len(entities))
            actionable_content = resource['actionable_advice']
            actionable_node = {
                "id": actionable_id,
                "label": "ActionableAdvice",
                "properties": {
                    "content": actionable_content,
                    "name": actionable_content  # Store in both properties for compatibility
                }
            }
            entities.append(actionable_node)
            logging.info(f"Added ActionableAdvice node with content ({len(actionable_content)} chars)")

            # Create relationship from Advice to ActionableAdvice
            relationships.append({
                "type": "HAS_ACTIONABLE_ADVICE",
                "start_node_id": advice_id,
                "end_node_id": actionable_id,
                "properties": {}
            })

        # Extract tags if available
        if 'tags' in resource and isinstance(resource['tags'], dict):
            tags = resource['tags']

            # Process Main Topic Entities
            if 'Main Topic Entities' in tags and tags['Main Topic Entities']:
                for i, topic in enumerate(tags['Main Topic Entities']):
                    topic_id = str(len(entities))
                    topic_node = {
                        "id": topic_id,
                        "label": "Topic",
                        "properties": {"name": topic}
                    }
                    entities.append(topic_node)

                    # Create relationship from Advice to Topic
                    relationships.append({
                        "type": "HAS_TOPIC",
                        "start_node_id": advice_id,
                        "end_node_id": topic_id,
                        "properties": {}
                    })

            # Process Sub-entities as SubTopics
            if 'Sub-entities' in tags and tags['Sub-entities']:
                for i, subtopic in enumerate(tags['Sub-entities']):
                    subtopic_id = str(len(entities))
                    subtopic_node = {
                        "id": subtopic_id,
                        "label": "SubTopic",
                        "properties": {"name": subtopic}
                    }
                    entities.append(subtopic_node)

                    # Create relationship from Advice to SubTopic
                    relationships.append({
                        "type": "HAS_SUBTOPIC",
                        "start_node_id": advice_id,
                        "end_node_id": subtopic_id,
                        "properties": {}
                    })

            # Process Age Range
            if 'Age Range' in tags and tags['Age Range']:
                for i, age in enumerate(tags['Age Range']):
                    age_id = str(len(entities))
                    age_node = {
                        "id": age_id,
                        "label": "AgeGroup",
                        "properties": {"age_label": age}
                    }
                    entities.append(age_node)

                    # Create relationship from Advice to AgeGroup
                    relationships.append({
                        "type": "RECOMMENDED_FOR",
                        "start_node_id": advice_id,
                        "end_node_id": age_id,
                        "properties": {}
                    })

            # Process Guidance Style
            if 'Guidance Style' in tags and tags['Guidance Style']:
                for i, style in enumerate(tags['Guidance Style']):
                    style_id = str(len(entities))
                    style_node = {
                        "id": style_id,
                        "label": "GuidanceStyle",
                        "properties": {"style_name": style}
                    }
                    entities.append(style_node)

                    # Create relationship from Advice to GuidanceStyle
                    relationships.append({
                        "type": "USES_STYLE",
                        "start_node_id": advice_id,
                        "end_node_id": style_id,
                        "properties": {}
                    })

        # Process author information
        if 'author' in resource and resource['author']:
            author_id = str(len(entities))
            author_node = {
                "id": author_id,
                "label": "Author",
                "properties": {
                    "name": resource['author'],
                    "credentials": resource.get('credentials', '')
                }
            }
            entities.append(author_node)

            # Create relationship from Advice to Author
            relationships.append({
                "type": "WRITTEN_BY",
                "start_node_id": advice_id,
                "end_node_id": author_id,
                "properties": {}
            })

        # Process source information
        if 'source' in resource and isinstance(resource['source'], dict):
            source = resource['source']
            source_id = str(len(entities))
            source_node = {
                "id": source_id,
                "label": "Source",
                "properties": {
                    "name": source.get('name', 'Unknown Source'),
                    "type": source.get('type', ''),
                    "url": source.get('url', '')
                }
            }
            entities.append(source_node)

            # Create relationship from Advice to Source
            relationships.append({
                "type": "CITED_FROM",
                "start_node_id": advice_id,
                "end_node_id": source_id,
                "properties": {}
            })

        # Process temporal context
        if 'temporal_context' in resource and resource['temporal_context']:
            context_id = str(len(entities))
            context_node = {
                "id": context_id,
                "label": "TemporalContext",
                "properties": {"context_label": resource['temporal_context']}
            }
            entities.append(context_node)

            # Create relationship from Advice to TemporalContext
            relationships.append({
                "type": "SUGGESTED_AT",
                "start_node_id": advice_id,
                "end_node_id": context_id,
                "properties": {}
            })

        # Process scenario notes
        if 'scenario_notes' in resource and resource['scenario_notes']:
            notes_id = str(len(entities))
            notes_content = resource['scenario_notes']
            notes_node = {
                "id": notes_id,
                "label": "ScenarioNote",
                "properties": {
                    "summary": notes_content,
                    "name": notes_content  # Store in both properties for compatibility
                }
            }
            entities.append(notes_node)
            logging.info("Added ScenarioNote node with content")

            # Create relationship from Advice to ScenarioNote
            relationships.append({
                "type": "HAS_SCENARIO_NOTE",
                "start_node_id": advice_id,
                "end_node_id": notes_id,
                "properties": {}
            })

        return {
            "nodes": entities,
            "relationships": relationships
        }

    async def process_resource(self, resource: Dict) -> Optional[Dict]:
        """Process a single resource and add it to the knowledge graph"""
        # Extract text from the resource - using the correct nested structure
        resource_text = ""
        if 'full_text' in resource and isinstance(resource['full_text'], dict) and 'content' in resource['full_text']:
            resource_text = resource['full_text']['content']

        resource_title = resource.get('title', 'Unknown Title')

        if not resource_text:
            logging.warning(f"Skipping resource with no text content: {resource_title}")
            logging.warning(f"Available fields: {list(resource.keys())}")
            if 'full_text' in resource:
                logging.warning(f"full_text fields: {list(resource['full_text'].keys()) if isinstance(resource['full_text'], dict) else 'not a dict'}")
            return None

        # Log resource details
        logging.info(f"Processing resource: {resource_title}")
        logging.info(f"Text length: {len(resource_text)} characters")

        # Extract entities from tags
        tag_entities = self._extract_entities_from_tags(resource)
        logging.info(f"Extracted {len(tag_entities['nodes'])} nodes and {len(tag_entities['relationships'])} relationships from tags")

        # Decide whether to use LLM extraction or just tag extraction
        # Set to False to use only tag extraction which preserves the full text content better
        use_llm_extraction = False  # Using tag extraction to preserve full text content

        if use_llm_extraction:
            # Set up the example annotations for the template
            examples = self._get_example_annotations()
            self.prompt_template.template.examples = examples  # Set the examples on the template

            # Create the pipeline with the template
            pipeline = self._create_pipeline()

            try:
                logging.info(f"Starting pipeline for resource: {resource_title}")
                result = await pipeline.run_async(text=resource_text)

                # Log success details
                if result:
                    logging.info(f"Successfully processed resource: {resource_title}")
                    if hasattr(result, 'nodes') and hasattr(result, 'relationships'):
                        logging.info(f"Extracted {len(result.nodes)} nodes and {len(result.relationships)} relationships")
                    return result
                else:
                    logging.warning(f"Pipeline returned empty result for resource: {resource_title}")
                    return tag_entities  # Return tag entities if LLM extraction fails
            except Exception as e:
                logging.error(f"Error processing resource {resource_title}: {str(e)}")
                # Try to extract useful information from the error
                if hasattr(e, 'response') and hasattr(e.response, 'content'):
                    logging.error(f"Response content: {e.response.content}")
                elif hasattr(e, '__dict__'):
                    logging.error(f"Error details: {e.__dict__}")
                return tag_entities  # Return tag entities if LLM extraction fails
        else:
            # If not using LLM extraction, just return the tag entities
            return tag_entities

    def _get_example_annotations(self) -> str:
        """Return example annotations for the prompt"""
        return """
Example 1:
Input: "Offer toddlers limited choices such as 'Do you want apple or orange juice?' to reduce tantrums by giving a sense of control. Actionable Advice: When facing resistance during daily routines, offer your child a choice between two acceptable options to foster a sense of autonomy."

Output:
{{
    "nodes": [
        {{"id": "0", "label": "Advice", "properties": {{"title": "Offering Limited Choices"}}}},
        {{"id": "1", "label": "Topic", "properties": {{"name": "Tantrums"}}}},
        {{"id": "2", "label": "SubTopic", "properties": {{"name": "Autonomy"}}}},
        {{"id": "3", "label": "AgeGroup", "properties": {{"age_label": "2 years old"}}}},
        {{"id": "4", "label": "GuidanceStyle", "properties": {{"style_name": "Authoritative"}}}},
        {{"id": "5", "label": "TemporalContext", "properties": {{"context_label": "Mealtime"}}}},
        {{"id": "6", "label": "ScenarioNote", "properties": {{"summary": "Useful for defusing power struggles in toddlers asserting independence."}}}},
        {{"id": "7", "label": "Author", "properties": {{"name": "Dr. Jane Doe", "credentials": "Ph.D. in Child Psychology"}}}},
        {{"id": "8", "label": "Source", "properties": {{"name": "Parenting Today", "type": "Website Article", "url": "https://parentingtoday.org/choices"}}}},
        {{"id": "9", "label": "ActionableAdvice", "properties": {{"content": "When facing resistance during daily routines, offer your child a choice between two acceptable options to foster a sense of autonomy."}}}}
    ],
    "relationships": [
        {{"type": "HAS_TOPIC", "start_node_id": "0", "end_node_id": "1", "properties": {{}}}},
        {{"type": "HAS_SUBTOPIC", "start_node_id": "0", "end_node_id": "2", "properties": {{}}}},
        {{"type": "RECOMMENDED_FOR", "start_node_id": "0", "end_node_id": "3", "properties": {{}}}},
        {{"type": "USES_STYLE", "start_node_id": "0", "end_node_id": "4", "properties": {{}}}},
        {{"type": "SUGGESTED_AT", "start_node_id": "0", "end_node_id": "5", "properties": {{}}}},
        {{"type": "HAS_SCENARIO_NOTE", "start_node_id": "0", "end_node_id": "6", "properties": {{}}}},
        {{"type": "WRITTEN_BY", "start_node_id": "0", "end_node_id": "7", "properties": {{}}}},
        {{"type": "CITED_FROM", "start_node_id": "0", "end_node_id": "8", "properties": {{}}}},
        {{"type": "HAS_ACTIONABLE_ADVICE", "start_node_id": "0", "end_node_id": "9", "properties": {{}}}}
    ]
}}
"""

    async def build_knowledge_graph(self, resources_path: Path, limit: int = None):
        """Build the complete knowledge graph from all resources

        Args:
            resources_path: Path to the JSONL file containing resources
            limit: Optional limit on number of resources to process (for testing)
        """
        resources = self.prompt_template.load_jsonl(resources_path)

        # Limit the number of resources if specified
        if limit is not None:
            logging.info(f"Processing limited set of {limit} resources (out of {len(resources)} total)")
            resources = resources[:limit]
        else:
            logging.info(f"Processing all {len(resources)} resources")

        results = []
        for i, resource in enumerate(resources, 1):
            logging.info(f"Processing resource {i}/{len(resources)}: {resource.get('title', 'Unknown Title')}")
            result = await self.process_resource(resource)
            if result:
                results.append(result)
                logging.info(f"Successfully added resource {i} to knowledge graph")
            else:
                logging.warning(f"Failed to process resource {i}")

        logging.info(f"Processed {len(results)}/{len(resources)} resources successfully")
        
        # Actually create the nodes and relationships in Neo4j
        await self._create_graph_entities(results)
        
        return results
    
    async def _create_graph_entities(self, results):
        """Create the extracted entities and relationships in Neo4j"""
        with self.neo4j_driver.session() as session:
            for result in results:
                if isinstance(result, dict) and 'nodes' in result:
                    # Create nodes
                    for node in result['nodes']:
                        query = f"""
                        CREATE (n:{node['label']} $properties)
                        """
                        session.run(query, properties=node['properties'])
                    
                    # Create relationships
                    for rel in result['relationships']:
                        query = f"""
                        MATCH (a), (b)
                        WHERE id(a) = $start_id AND id(b) = $end_id
                        CREATE (a)-[:{rel['type']}]->(b)
                        """
                        session.run(query, 
                                  start_id=int(rel['start_node_id']), 
                                  end_id=int(rel['end_node_id']))
        
        logging.info("Successfully created all entities in Neo4j")

async def main():
    # Set up logging with more details
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('kg_builder.log')
        ]
    )

    config = Config()
    resources_path = Path("/Users/matthewtaruno/dev/hestia/data/brain.jsonl")

    # Process only 5 resources first to test
    limit = None  # Set to None to process all resources

    builder = KnowledgeGraphBuilder(config)
    logging.info(f"Starting knowledge graph building process with limit={limit}")
    results = await builder.build_knowledge_graph(resources_path, limit=limit)

    logging.info(f"Processed {len(results)} resources successfully")

    # Log some statistics about the knowledge graph
    if results:
        total_nodes = sum(len(result.nodes) if hasattr(result, 'nodes') else 0 for result in results)
        total_relationships = sum(len(result.relationships) if hasattr(result, 'relationships') else 0 for result in results)
        logging.info(f"Total nodes created: {total_nodes}")
        logging.info(f"Total relationships created: {total_relationships}")

if __name__ == "__main__":
    asyncio.run(main())
