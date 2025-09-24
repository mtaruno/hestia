import os
import logging 
from dotenv import load_dotenv

# Load environment variables from config.env
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
config_path = os.path.join(root_dir, 'config.env')
load_dotenv(config_path)

class Config:
    def __init__(self): 
        logging.basicConfig()
        logging.getLogger("neo4j_graphrag").setLevel(logging.DEBUG)
        
        self.URI = os.getenv('NEO4J_URI', 'neo4j+s://e8834497.databases.neo4j.io')
        self.AUTH = (os.getenv('NEO4J_USERNAME', 'neo4j'), os.getenv('NEO4J_PASSWORD'))
        self.DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')
        self.JSONL_PATH = "data/papers/scholar_parenting_styles_child_development.jsonl"
        self.openai_api_type = "azure" 
        self.openai_api_base = "https://api.openai.com/v1"
        self.openai_api_version = "2024-08-01-preview"
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_embedding_version = "2023-05-15"
        self.embedding_model_name = "text-embedding-ada-002"
        self.model_name = "gpt-4o-mini"

        assert self.URI, "NEO4J_URI is not set"
        assert self.AUTH[1], "NEO4J_PASSWORD is not set"
        assert self.DATABASE, "DATABASE is not set"
        assert self.openai_api_key, "OPENAI_API_KEY is not set"

