

import pytest

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from neo4j import GraphDatabase
from config import Config

cfg = Config()
@pytest.fixture(scope="session")
def neo4j_session():
    driver = GraphDatabase.driver(cfg.URI, auth=cfg.AUTH)
    session =  driver.session()
    yield session
    session.close()
    driver.close()
    