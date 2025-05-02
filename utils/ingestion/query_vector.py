import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.schema.document import Document as LangchainDocument

load_dotenv()

# this is widely used to get the answer.
# now should I deepen the usage base.
def query_vector_store(query_text, top_k=5):
    """
    Query the Pinecone vector store with the given text.
    
    Args:
        query_text (str): The question or query text to search for
        top_k (int): Number of results to return
        
    Returns:
        list: List of documents most relevant to the query
    """
    # Initialize OpenAI embeddings
    embeddings_model = OpenAIEmbeddings(openai_api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    
    # Get index name from environment variables
    index_name = os.environ.get('PINECONE_INDEX_NAME')
    
    # If using the older version that used INDEX_NAME instead of PINECONE_INDEX_NAME
    if not index_name:
        index_name = os.environ.get('INDEX_NAME')
    
    # Create vector store
    vector_store = PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings_model
    )
    
    # Search for similar documents
    results = vector_store.similarity_search(
        query=query_text,
        k=top_k
    )
    
    return results

def format_results(results):
    """
    Format the results from vector store query for better readability.
    
    Args:
        results (list): List of documents returned from query_vector_store
        
    Returns:
        str: Formatted results as string
    """
    if not results:
        return "No results found."
    
    formatted_output = "Query Results:\n\n"
    
    for i, doc in enumerate(results):
        formatted_output += f"Result {i+1}:\n"
        formatted_output += f"Content: {doc.page_content}\n"
        formatted_output += "Metadata:\n"
        for key, value in doc.metadata_fields.items():
            formatted_output += f"  {key}: {value}\n"
        formatted_output += "\n" + "-"*50 + "\n\n"
    
    return formatted_output

def ask_question(question, top_k=5):
    """
    Ask a question and get formatted results.
    
    Args:
        question (str): The question to ask
        top_k (int): Number of results to return
        
    Returns:
        str: Formatted results
    """
    print(f"Querying: '{question}'")
    results = query_vector_store(question, top_k)
    return format_results(results)

if __name__ == "__main__":
    # Example usage
    sample_questions = [
        "How any operational beds does the company have?",
        "What is their ARPOB?",
        "What is the state of company affairs ?",
        "What are the company's growth strategies?",
        "What are the contingent liabilities that the company face ?"
    ]
    
    print("Sample Vector Store Query Application")
    print("====================================")
    
    # Allow user to choose a sample question or enter their own
    print("\nSample questions:")
    for i, question in enumerate(sample_questions):
        print(f"{i+1}. {question}")
    
    choice = input("\nEnter a number to choose a sample question, or type your own question: ")
    
    try:
        question_index = int(choice) - 1
        if 0 <= question_index < len(sample_questions):
            question = sample_questions[question_index]
        else:
            question = choice
    except ValueError:
        question = choice
    
    # Set how many results to return
    try:
        k = int(input("\nHow many results do you want to see? (default: 5): ") or "5")
    except ValueError:
        k = 5
    
    # Get and print results
    print("\nQuerying Pinecone index...\n")
    results = ask_question(question, k)
    print(results)
