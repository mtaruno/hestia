# test_llm_connection.py

import pytest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from graphrag.config import Config
from neo4j_graphrag.llm import OpenAILLM

cfg = Config()

class LLMGenerator:
    def __init__(self):
        self.llm = OpenAILLM(
            model_name=cfg.model_name,
            model_params={
                # "response_format": {"type": "json_object"},
                "temperature": 0
            }
        )
    def generate_response(self, prompt):
        return self.llm.invoke(prompt)

@pytest.fixture(scope="module")
def llm_generator():
    return LLMGenerator()

def test_llm_connection_basic(llm_generator):
    prompt = "Say hello"
    response = llm_generator.generate_response(prompt)
    
    assert response is not None, "LLM did not return any response"

# def test_llm_json(llm_generator):
#     prompt = "Please respond with a JSON object containing: greeting: 'Hello World'"
#     response = llm_generator.generate_response(prompt)
    
#     assert isinstance(response, dict), f"Expected dict, got {type(response)}"
#     assert "greeting" in response, "Missing 'greeting' key in response"
#     assert response["greeting"] == "Hello World", f"Unexpected greeting: {response['greeting']}"