import os
import sys
import logging
import yaml
import os
import logging 
import openai
import neo4j


# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the necessary modules
from get_auto_response.retriever_community import run_graphrag_retrieval_with_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)

def getAutoResponse(postTitle, postContent):
    """
    Generate an auto-response for a community post using the knowledge graph.

    Args:
        postTitle (str): The title of the post
        postContent (str): The content of the post

    Returns:
        str: The generated response
    """
    # logging.info(f"Generating auto-response for post: {postTitle}")
    print(f"Generating auto-response for post: {postTitle}")
    # Combine the title and content for the query
    query = f"{postTitle} {postContent}"

    # Run the retrieval and generate a response
    response = run_graphrag_retrieval_with_prompt(
        query=query,
        post_title=postTitle,
        post_content=postContent
    )

    print("Generated auto-response")
    return response