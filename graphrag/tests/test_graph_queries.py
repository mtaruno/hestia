import pytest
import json
# No need to import config or get_neo4j_driver directly — pytest handles fixtures automatically

def test_query_paper_and_entities(neo4j_session):
    result = neo4j_session.run("MATCH (n) RETURN DISTINCT labels(n), properties(n) LIMIT 5")
    res = neo4j_session.run("CALL apoc.meta.graph() YIELD nodes, relationships RETURN nodes, relationships")
    records = res.data()

    # Pretty print the structure to a file
    with open("res.txt", "w") as f:
        json.dump(records, f, indent=2)
    records = result.data()
    print("\nSample nodes:", records)
    assert records, "No nodes in the DB"


@pytest.mark.neo4j
def test_paper_nodes_exist(neo4j_session):
    result = neo4j_session.run("MATCH (p:Paper) RETURN count(p) AS count")
    count = result.single()["count"]
    assert count > 0, "No Paper nodes found in the knowledge graph"

@pytest.mark.neo4j
def test_entities_have_related_nodes(neo4j_session):
    result = neo4j_session.run("""
    MATCH (e:Entity)
    WHERE NOT (e)-[*1..2]-(related)
    RETURN count(e) AS unconnected_count
    """)
    unconnected_count = result.single()["unconnected_count"]
    assert unconnected_count == 0, f"There are {unconnected_count} Entity nodes with no related connections"