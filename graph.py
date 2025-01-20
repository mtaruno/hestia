import getpass
import os
from dotenv import load_dotenv
import openai
import neo4j
import re
from neo4j import GraphDatabase
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.embeddings import OpenAIEmbeddings

# https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html

load_dotenv('config.env', override=True)
openai.api_type = "azure" #I use Azure OpenAI. You might need to comment if you use the non-Azure instance
openai.api_base = os.getenv('OPENAI_API_BASE')
openai.api_version = os.getenv('OPENAI_API_VERSION')
openai.api_key = os.getenv('OPENAI_API_KEY')
model_name = os.getenv('MODEL_NAME')
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]


neo4j_driver = neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
# 1. Neo4j driver
AUTH = (NEO4J_USERNAME, NEO4J_PASSWORD)
INDEX_NAME = "index-name"
# Connect to Neo4j database
driver = GraphDatabase.driver(NEO4J_URI, auth=AUTH)
# 2. Retriever
# Create Embedder object, needed to convert the user question (text) to a vector
embedder = OpenAIEmbeddings(model="text-embedding-3-large")
# Initialize the retriever
retriever = VectorRetriever(driver, INDEX_NAME, embedder)
llm = OpenAILLM(model_name="gpt-4o", model_params={"temperature": 0})
rag = GraphRAG(retriever=retriever, llm=llm)
query_text = "My child "
response = rag.search(query_text=query_text, retriever_config={"top_k": 5})
print(response.answer)


# if __name_ "__main__":
    # import unittest

    # class TestSuite(unittest.TestCase):
    # pass