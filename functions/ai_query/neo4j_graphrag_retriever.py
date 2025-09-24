import os
import sys
import logging
import time
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)

# Import Neo4j and OpenAI dependencies
import neo4j
from openai import OpenAI

# Import the Config class from the parent directory
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ai_query.config import Config

# Import the retriever and embeddings classes
from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.embeddings import OpenAIEmbeddings

# Configuration
cfg = Config()

def index_exists(driver, index_name: str) -> bool:
    """Check if a vector index exists in the Neo4j database."""
    with driver.session() as session:
        result = session.run(f"SHOW INDEXES YIELD name RETURN name")
        return any(row["name"] == index_name for row in result)

def retrieve_from_knowledge_graph(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve relevant information from the knowledge graph based on the query.

    Args:
        query (str): The user's query
        limit (int): Maximum number of results to return

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the retrieved information
    """
    logging.info(f"Retrieving from knowledge graph for query: {query}")

    # Connect to Neo4j
    with neo4j.GraphDatabase.driver(cfg.URI, auth=cfg.AUTH) as driver:
        # Initialize the embeddings model
        # TODO: Add the OpenAI key here
        embedder = OpenAIEmbeddings(api_key="")
        
        # Check if the vector index exists
        index_name = "advice_embedding"
        if not index_exists(driver, index_name):
            logging.error(f"Vector index '{index_name}' does not exist")
            return []

        # Create the retriever
        graph_retriever = VectorCypherRetriever(
            driver,
            index_name=index_name,
            embedder=embedder,
            retrieval_query=f"""
            // Match advice nodes that are relevant to the query
            MATCH (a:Advice)
            WHERE a.name IS NOT NULL OR a.content IS NOT NULL

            // Find related topics, subtopics, and age groups
            OPTIONAL MATCH (a)-[:HAS_TOPIC]->(topic:Topic)
            OPTIONAL MATCH (a)-[:HAS_SUBTOPIC]->(subtopic:SubTopic)
            OPTIONAL MATCH (a)-[:RECOMMENDED_FOR]->(age:AgeGroup)
            OPTIONAL MATCH (a)-[:USES_STYLE]->(style:GuidanceStyle)

            // Get actionable advice if available
            OPTIONAL MATCH (a)-[:HAS_ACTIONABLE_ADVICE]->(actionable:ActionableAdvice)

            // Get scenario notes if available
            OPTIONAL MATCH (a)-[:HAS_SCENARIO_NOTE]->(scenario:ScenarioNote)

            // Get author information
            OPTIONAL MATCH (a)-[:WRITTEN_BY]->(author:Author)

            // Collect all the related information
            WITH a,
                 collect(DISTINCT topic) AS topics,
                 collect(DISTINCT subtopic) AS subtopics,
                 collect(DISTINCT age) AS age_groups,
                 collect(DISTINCT style) AS guidance_styles,
                 collect(DISTINCT actionable) AS actionable_advice,
                 collect(DISTINCT scenario) AS scenario_notes,
                 collect(DISTINCT author) AS authors,
                 score

            // Calculate relevance score with additional factors
            WITH a, topics, subtopics, age_groups, guidance_styles,
                 actionable_advice, scenario_notes, authors, score,
                 // Boost score if actionable advice is available
                 CASE WHEN size(actionable_advice) > 0 THEN 0.2 ELSE 0 END AS actionable_boost,
                 // Boost score based on scenario notes relevance
                 CASE WHEN size(scenario_notes) > 0 THEN 0.1 ELSE 0 END AS scenario_boost

            // Calculate final score with boosts
            WITH a, topics, subtopics, age_groups, guidance_styles,
                 actionable_advice, scenario_notes, authors,
                 score + actionable_boost + scenario_boost AS final_score

            // Return comprehensive information about the advice
            RETURN
                a.id AS id,
                // Use content property if available, otherwise fall back to name
                CASE WHEN a.content IS NOT NULL THEN a.content ELSE a.name END AS text,
                [topic IN topics | topic.name] AS topics,
                [subtopic IN subtopics | subtopic.name] AS subtopics,
                [age IN age_groups | age.name] AS age_groups,
                [style IN guidance_styles | style.name] AS guidance_styles,
                [advice IN actionable_advice | CASE WHEN advice.content IS NOT NULL THEN advice.content ELSE advice.name END] AS actionable_advice,
                [note IN scenario_notes | CASE WHEN note.name IS NOT NULL THEN note.name ELSE '' END] AS scenario_notes,
                [author IN authors | author.name] AS authors,
                final_score AS score
            ORDER BY score DESC
            LIMIT {limit}
            """
        )

        # Retrieve results
        results = graph_retriever.get_search_results(query_text=query)

        # Convert results to a list of dictionaries
        result_list = []
        for record in results.records:
            result_dict = {
                'id': record.get('id', 'Unknown'),
                'text': record.get('text', ''),
                'topics': record.get('topics', []),
                'subtopics': record.get('subtopics', []),
                'age_groups': record.get('age_groups', []),
                'guidance_styles': record.get('guidance_styles', []),
                'actionable_advice': record.get('actionable_advice', []),
                'scenario_notes': record.get('scenario_notes', []),
                'authors': record.get('authors', []),
                'score': record.get('score', 0)
            }
            result_list.append(result_dict)

        logging.info(f"Retrieved {len(result_list)} results from knowledge graph")
        return result_list

def format_results_for_llm(results: List[Dict[str, Any]]) -> str:
    """
    Format the retrieved results into a string that can be used as context for the LLM.

    Args:
        results (List[Dict[str, Any]]): The retrieved results

    Returns:
        str: A formatted string containing the retrieved information
    """
    if not results:
        return "No relevant information found in the knowledge graph."

    formatted_passages = []

    for i, result in enumerate(results):
        passage = f"Passage {i+1}: {result['text']}\n\n"

        # Add actionable advice if available
        if result['actionable_advice']:
            # Remove duplicates while preserving order
            unique_advice = []
            seen = set()
            for advice in result['actionable_advice']:
                if advice not in seen:
                    seen.add(advice)
                    unique_advice.append(advice)

            passage += f"Actionable Advice: {', '.join(unique_advice)}\n\n"

        # Add topics and subtopics
        if result['topics']:
            passage += f"Topics: {', '.join(result['topics'])}\n"
        if result['subtopics']:
            passage += f"Subtopics: {', '.join(result['subtopics'])}\n"

        # Add age groups
        if result['age_groups']:
            passage += f"Age Groups: {', '.join(result['age_groups'])}\n"

        formatted_passages.append(passage)

    return "\n\n".join(formatted_passages)

def generate_response_with_openai(query: str, context: str) -> str:
    """
    Generate a response using the OpenAI API.

    Args:
        query (str): The user's query
        context (str): The context from the knowledge graph

    Returns:
        str: The generated response
    """
    client = OpenAI(api_key=cfg.openai_api_key)
    
    prompt = f"""You are a warm, emotionally attuned parenting expert assistant named Hestia.
Your role is to help caregivers of young children (ages 0–6) navigate parenting challenges with gentle guidance grounded in research-backed advice.

You are replying to a parent's question. Use a tone that feels like a supportive, well-read friend who understands what raising a young child is really like.

Use these principles:
- Validate the parent's emotional experience before offering any suggestions.
- Make your language gentle, encouraging, and non-judgmental.
- Offer practical, specific strategies that are easy to try—even for tired or overwhelmed caregivers.
- Keep your reply focused: one helpful, clear, and affirming response is better than a list of options.
- If useful, briefly share a developmental insight (e.g., "It's normal at this age for kids to…")

Use the following expert advice from our structured knowledge base as input. Do not quote it directly. Instead, synthesize relevant concepts and present them naturally in your own words:

{context}

Here is the parent's question:
{query}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )

    return response.choices[0].message.content

def run_retrieval_and_generate(query: str) -> str:
    """
    Run the full retrieval and response generation pipeline.

    Args:
        query (str): The user's query

    Returns:
        str: The generated response
    """
    # Retrieve information from the knowledge graph
    results = retrieve_from_knowledge_graph(query)

    # Format the results for the LLM
    context = format_results_for_llm(results)

    # Generate a response using the OpenAI API
    response = generate_response_with_openai(query, context)

    return response
