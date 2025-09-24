# Add parent directory to sys.path to allow importing config
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
# Run the GraphRAG Search

import logging
logging.basicConfig(level=logging.INFO)

from neo4j_graphrag.indexes import create_vector_index

import neo4j
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from openai import AzureOpenAI
# from neo4j_graphrag.llms import AzureOpenAILLM
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.retrievers import VectorCypherRetriever
from dataclasses import dataclass
from typing import List, Dict, Any
import yaml

from langchain.schema import SystemMessage
from langchain_core.messages import HumanMessage
from langchain.chat_models import ChatOpenAI

import time


# Import shared config
from get_auto_response.config import Config

cfg = Config()

@dataclass
class GraphSchema:
    """Represents the knowledge graph schema"""
    nodes: List[str]
    relationships: List[str]

    def to_dict(self) -> dict:
        return {
            "nodes": self.nodes,
            "relationships": self.relationships
        }

# Define the schema for the knowledge graph
schema = GraphSchema(
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


def index_exists(driver, index_name: str) -> bool:
    with driver.session() as session:
        result = session.run(f"SHOW INDEXES YIELD name RETURN name")
        return any(row["name"] == index_name for row in result)

def run_graphrag_retrieval(
    query="How do I avoid passing on my insecurities to my child through my words?",
    index_name="advice_embedding",
    limit=5,
    age_filter=None,
    temporal_context=None,
    source_type=None,
    guidance_style=None,
    return_results=False
):
    """
    Run a GraphRAG retrieval query against the knowledge graph with optional filters.

    This function performs semantic search on the knowledge graph using the provided query
    and returns relevant advice nodes along with their connected information.

    Args:
        query (str): The user's query about parenting advice
        index_name (str): Name of the vector index to use for semantic search
        limit (int): Maximum number of results to return
        age_filter (str, optional): Filter results by specific age group
        temporal_context (str, optional): Filter by time of day context (e.g., "Morning", "Evening")
        source_type (str, optional): Filter by source type (e.g., "Book", "Podcast")
        guidance_style (str, optional): Filter by parenting guidance style

    Returns:
        None: Results are printed to console and a final answer is generated
    """
    with neo4j.GraphDatabase.driver(cfg.URI, auth=cfg.AUTH) as driver:
        embedder = OpenAIEmbeddings(api_key=cfg.openai_api_key)

        # Log the schema being used
        logging.info("Using schema with nodes: %s", schema.nodes)
        logging.info("Using schema with relationships: %s", schema.relationships)

        if not index_exists(driver, index_name):
            # Create vector index on Advice nodes instead of Chunk nodes
            create_vector_index(
                driver,
                name=index_name,
                label="Advice",
                embedding_property="embedding",
                dimensions=1536,
                similarity_fn="cosine"
            )

        # Prepare filter conditions
        filter_conditions = []
        if age_filter:
            logging.info("Filtering by age: %s", age_filter)
            filter_conditions.append(
                f"ANY(age_name IN [age IN age_groups | age.name] "
                f"WHERE age_name CONTAINS '{age_filter}' OR age_name = 'Any')"
            )

        if guidance_style:
            logging.info("Filtering by guidance style: %s", guidance_style)
            filter_conditions.append(
                f"ANY(style IN guidance_styles "
                f"WHERE style.name CONTAINS '{guidance_style}')"
            )

        # Combine filter conditions
        filter_clause = ""
        if filter_conditions:
            filter_clause = "WHERE " + " AND ".join(filter_conditions)

        # Use the schema to construct the retriever
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

            // Apply filters if specified
            {filter_clause}

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

        def retrieve_context(question: str):
            results = graph_retriever.get_search_results(query_text=question)
            # Return full result objects for pretty-printing
            return list(results.records)

        results = retrieve_context(query)

        # Print a summary of results
        print(f"\n{'='*40}")
        print(f"Found {len(results)} relevant advice entries")
        print(f"{'='*40}\n")

        for i, result in enumerate(results):
            # Calculate relevance score percentage for display
            score = result.get('score', 0)
            relevance = min(int(score * 100), 100)  # Cap at 100%

            advice_id = result.get('id', 'Unknown')
            print(f"📝 Advice {i+1}: (ID: {advice_id}) (Relevance: {relevance}%)\n")

            # Print actionable advice first if available (prioritize actionable content)
            actionable_advice = result.get('actionable_advice', [])
            if actionable_advice:
                print("✅ Actionable Advice:")
                for advice in actionable_advice:
                    print(f"  • {advice}")
                print()

            # Print content
            content = result.get('text', '')
            # Truncate if too long for display
            if len(content) > 500:
                content = content[:500] + "... [content truncated]"
            print(f"Content:\n{content}\n")

            # Print topics and subtopics
            topics = result.get('topics', [])
            subtopics = result.get('subtopics', [])
            print(f"🏷️ Topics: {', '.join(topics) if topics else 'None'}")
            print(f"  Subtopics: {', '.join(subtopics) if subtopics else 'None'}")

            # Print age groups and guidance styles
            age_groups = result.get('age_groups', [])
            guidance_styles = result.get('guidance_styles', [])
            print(f"👶 Age Groups: {', '.join(age_groups) if age_groups else 'Any'}")
            print(f"🧠 Guidance Styles: {', '.join(guidance_styles) if guidance_styles else 'None'}")

            # Print scenario notes
            scenario_notes = result.get('scenario_notes', [])
            if scenario_notes:
                print("\n📋 Scenario Notes:")
                for note in scenario_notes:
                    # Truncate if too long
                    if len(note) > 200:
                        note = note[:200] + "... [truncated]"
                    print(f"  • {note}")

            # Print author information
            authors = result.get('authors', [])
            if authors:
                print(f"\n👤 Authors: {', '.join(authors)}")

            print("\n" + "-"*80 + "\n")

        # If return_results is True, return the results instead of generating an answer
        if return_results:
            return results

        final_answer = generate_answer_from_chunks(results, query)
        print("\nFinal Answer:\n" + "=" * 40 + f"\n{final_answer}")



def run_graphrag_retrieval_with_prompt(
    query="How do I avoid passing on my insecurities to my child through my words?",
    limit=5,
    age_filter=None,
    temporal_context=None,
    source_type=None,
    guidance_style=None,
    post_title=None,
    post_content=None
):
    """
    Run GraphRAG retrieval with prompt formatting for community posts.

    Args:
        query (str): The user's query
        limit (int): Maximum number of results to return
        age_filter (str, optional): Filter by age group
        temporal_context (str, optional): Filter by temporal context
        source_type (str, optional): Filter by source type
        guidance_style (str, optional): Filter by guidance style
        post_title (str, optional): The title of the post
        post_content (str, optional): The content of the post

    Returns:
        str: The generated response
    """
    # Get results from the knowledge graph
    results = run_graphrag_retrieval(
        query=query,
        limit=limit,
        age_filter=age_filter,
        temporal_context=temporal_context,
        source_type=source_type,
        guidance_style=guidance_style,
        return_results=True
    )

    # Generate the answer using the retrieved chunks
    if post_title and post_content:
        # If post title and content are provided, use them
        print("Generating answer from chunks with post")
        return generate_answer_from_chunks_with_post(results, query, post_title, post_content)
    else:
        # Fallback to using the query directly
        print("Generating answer from chunks without post")
        return generate_answer_from_chunks(results, query)


def generate_answer_from_chunks_with_post(chunks: list, _user_query: str, post_title: str, post_content: str) -> str:
    """
    Generate a comprehensive answer from retrieved knowledge graph chunks for a community post.

    Args:
        chunks: List of retrieved chunks from the knowledge graph
        _user_query: The original user query (not used in this function)
        post_title: The title of the post
        post_content: The content of the post

    Returns:
        str: A synthesized response that addresses the user's post
    """
    # Load prompts from YAML file
    file_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(file_dir)
    kg_retrieval_dir = os.path.dirname(parent_dir)
    graphrag_dir = os.path.dirname(kg_retrieval_dir)
    prompts_path = os.path.join(graphrag_dir, 'data', 'prompts', 'prompts.yaml')

    print("Loading prompts from: %s", prompts_path)

    try:
        with open(prompts_path, 'r', encoding='utf-8') as file:
            prompts = yaml.safe_load(file)
            community_prompt_template = prompts.get('community_prompt', '')
            print("Successfully loaded community prompt template")
    except Exception as e:
        print("Error loading prompts: %s", str(e))
        # Fallback prompt in case of error
        community_prompt_template = """
        You are a warm, emotionally attuned parenting expert assistant responding publicly in a community forum for Hestia AI.

        Your role is to help caregivers of young children (ages 0–6) navigate parenting challenges with gentle guidance grounded in research-backed advice.

        You are replying to a public post from a parent. Use a tone that feels like a supportive, well-read friend who understands what raising a young child is really like.

        Use these principles:
        - Validate the parent's emotional experience before offering any suggestions.
        - Make your language gentle, encouraging, and non-judgmental.
        - Offer practical, specific strategies that are easy to try—even for tired or overwhelmed caregivers.
        - Keep your reply focused: one helpful, clear, and affirming response is better than a list of options.
        - If useful, briefly share a developmental insight (e.g., "It's normal at this age for kids to…")
        - Do not include or assume any personal user details.
        - End your response with a gentle invitation for other parents to share their experiences or tips on this topic, fostering a supportive community discussion.

        Use the following expert advice from our structured knowledge base as input. Do not quote it directly. Instead, synthesize relevant concepts and present them naturally in your own words:

        {context_combined}

        Here is the parent's post:

        Title: {post_title}
        Content: {post_content}
        """
        print("Using fallback prompt template")

    # Construct the context
    context_texts = []
    for i, chunk in enumerate(chunks):
        # Get the text content
        text = chunk['text']

        # Get actionable advice without duplicates
        actionable_advice = chunk['actionable_advice']
        # Remove duplicates while preserving order
        unique_advice = []
        seen = set()
        for advice in actionable_advice:
            if advice not in seen:
                seen.add(advice)
                unique_advice.append(advice)

        # Format the passage
        passage = f"Passage {i+1}: {text}"
        if unique_advice:
            passage += f"\n\nActionable Advice: {', '.join(unique_advice)}"

        context_texts.append(passage)

    context_combined = "\n\n".join(context_texts)

    # Format the prompt with the context and post details
    formatted_prompt = community_prompt_template.format(
        context_combined=context_combined,
        post_title=post_title,
        post_content=post_content
    )

    print("Prompt:\n", formatted_prompt)

    system_prompt = SystemMessage(content=formatted_prompt)

    # Empty user prompt since we've included the query in the system prompt
    user_prompt = HumanMessage(content="")

    # Use OpenAI Chat Model
    chat = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=cfg.openai_api_key)

    start_time = time.time()
    response = chat([system_prompt, user_prompt])
    end_time = time.time()
    latency = end_time - start_time
    print(f"⏱️ LLM response latency: {latency:.2f} seconds")

    return response.content


def generate_answer_from_chunks(chunks: list, user_query: str) -> str:
    """
    Generate a comprehensive answer from retrieved knowledge graph chunks.

    Args:
        chunks: List of retrieved chunks from the knowledge graph
        user_query: The original user query

    Returns:
        str: A synthesized response that addresses the user's query
    """
    # Load prompts from YAML file
    # The file is in the project root directory under data/prompts
    file_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(file_dir)
    kg_retrieval_dir = os.path.dirname(parent_dir)
    graphrag_dir = os.path.dirname(kg_retrieval_dir)
    prompts_path = os.path.join(graphrag_dir, 'data', 'prompts', 'prompts.yaml')

    logging.info("Loading prompts from: %s", prompts_path)

    try:
        with open(prompts_path, 'r', encoding='utf-8') as file:
            prompts = yaml.safe_load(file)
            community_prompt_template = prompts.get('community_prompt', '')
            logging.info("Successfully loaded community prompt template")
    except FileNotFoundError as e:
        logging.error("Prompt file not found: %s", str(e))
        # Fallback prompt in case the file can't be loaded
        community_prompt_template = """
        You are a warm, emotionally attuned parenting expert assistant designed to help caregivers
        navigate challenges with young children. Synthesize the following information to provide a
        thoughtful response:

        {context_combined}

        User Question: {user_query}
        """
        logging.warning("Using fallback prompt template due to file not found")
    except yaml.YAMLError as e:
        logging.error("Error parsing YAML file: %s", str(e))
        # Fallback prompt in case of YAML parsing error
        community_prompt_template = """
        You are a warm, emotionally attuned parenting expert assistant designed to help caregivers
        navigate challenges with young children. Synthesize the following information to provide a
        thoughtful response:

        {context_combined}

        User Question: {user_query}
        """
        logging.warning("Using fallback prompt template due to YAML parsing error")
    except IOError as e:
        logging.error("IO error reading prompt file: %s", str(e))
        # Fallback prompt in case of IO error
        community_prompt_template = """
        You are a warm, emotionally attuned parenting expert assistant designed to help caregivers
        navigate challenges with young children. Synthesize the following information to provide a
        thoughtful response:

        {context_combined}

        User Question: {user_query}
        """
        logging.warning("Using fallback prompt template due to IO error")

    # Construct the context
    context_texts = []
    for i, chunk in enumerate(chunks):
        # Get the text content
        text = chunk['text']

        # Get actionable advice without duplicates
        actionable_advice = chunk.get('actionable_advice', [])
        # Remove duplicates while preserving order
        unique_advice = []
        seen = set()
        for advice in actionable_advice:
            if advice not in seen:
                seen.add(advice)
                unique_advice.append(advice)

        # Format the passage
        passage = f"Passage {i+1}: {text}"
        if unique_advice:
            passage += f"\n\nActionable Advice: {', '.join(unique_advice)}"

        context_texts.append(passage)

    context_combined = "\n\n".join(context_texts)

    # Format the prompt with the context and query
    # Check if the prompt template expects post_title and post_content
    has_post_fields = ('{post_title}' in community_prompt_template and
                      '{post_content}' in community_prompt_template)

    if has_post_fields:
        # Use the query as both title and content if post details aren't provided
        formatted_prompt = community_prompt_template.format(
            context_combined=context_combined,
            post_title="User Query",
            post_content=user_query
        )
    else:
        # Use the fallback format with user_query
        formatted_prompt = f"""
        You are a warm, emotionally attuned parenting expert assistant designed to help caregivers
        navigate challenges with young children. Synthesize the following information to provide a
        thoughtful response:

        {context_combined}

        User Question: {user_query}
        """

    print("Prompt:\n", formatted_prompt)

    system_prompt = SystemMessage(content=formatted_prompt)

    # Empty user prompt since we've included the query in the system prompt
    user_prompt = HumanMessage(content="")

    # Use OpenAI Chat Model
    chat = ChatOpenAI(model="gpt-4o", temperature=0.7)

    start_time = time.time()
    response = chat([system_prompt, user_prompt])
    end_time = time.time()
    latency = end_time - start_time
    print(f"⏱️ LLM response latency: {latency:.2f} seconds")

    return response.content



# Run default query
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run GraphRAG retrieval with various filters')
    parser.add_argument(
        '--query',
        type=str,
        default="How do I avoid passing on my insecurities to my child through my words?",
        help='The query to search for'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=5,
        help='Maximum number of results to return'
    )
    parser.add_argument(
        '--age',
        type=str,
        help='Filter by age group (e.g., "2 years old", "Any")'
    )
    parser.add_argument(
        '--context',
        type=str,
        help='Filter by temporal context (e.g., "Morning", "Evening")'
    )
    parser.add_argument(
        '--source',
        type=str,
        help='Filter by source type (e.g., "Book", "Podcast")'
    )
    parser.add_argument(
        '--style',
        type=str,
        help='Filter by guidance style (e.g., "Empathic / Supportive")'
    )

    args = parser.parse_args()

    print(f"Running query: '{args.query}'")
    if args.age:
        print(f"Filtering by age: {args.age}")
    if args.context:
        print(f"Filtering by temporal context: {args.context}")
    if args.source:
        print(f"Filtering by source type: {args.source}")
    if args.style:
        print(f"Filtering by guidance style: {args.style}")

    # Example queries to try:
    # python retriever1.py --query "How do I handle tantrums?" --age "2 years old"
    # python retriever1.py --query "Setting boundaries" --style "Empathic / Supportive"
    # python retriever1.py --query "Emotional regulation" --source "Book"

    run_graphrag_retrieval(
        query=args.query,
        limit=args.limit,
        age_filter=args.age,
        temporal_context=args.context,
        source_type=args.source,
        guidance_style=args.style
    )
