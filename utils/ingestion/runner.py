from chunk_contextualiser import ChunkContextualiser

if __name__=="__main__":
    print("shams")
    c = ChunkContextualiser()
    # document we want to test against - aefec269-5bb4-433b-84c0-74074951c757
    res = c.process_all_chunks_for_document("aefec269-5bb4-433b-84c0-74074951c757")
    print("rizvi")
