from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline

kg_builder = SimpleKGPipeline(
    llm=llm, # an LLMInterface for Entity and Relation extraction
    driver=neo4j_driver,  # a neo4j driver to write results to graph
    embedder=embedder,  # an Embedder for chunks
    from_pdf=True,   # set to False if parsing an already extracted text
)
await kg_builder.run_async(file_path=str(file_path))
# await kg_builder.run_async(text="my text")  # if using from_pdf=False