import os
import logging
import glob
from dotenv import load_dotenv
load_dotenv(override=True)

#document loader and splitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

#azure components import 
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

#setting up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s -  %(levelname)s - %(message)s"
)
logger = logging.getLogger("Indexer")

def index_docs():
    '''
    Reads the pdfs, chunk them, and upload them to Azure AI search
    '''


    #define paths and look for data folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(current_dir,"../../backend/data")

    #check the environment variables
    logger.infor("="*60)
    logger.info("Checking environment variables...")
    logger.info(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    logger.info(f"AZURE_OPENAI_API_VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
    logger.info(f"EMBEDDING DEPLOYMENT: {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT',"text-embedding-3-small")}")
    logger.info(f"AZURE_SEARCH_ENDPOINT: {os.getenv('AZURE_SEARCH_ENDPOINT')}")
    logger.info(f"AZURE_SEARCH_INDEX_NAME: {os.getenv('AZURE_SEARCH_INDEX_NAME')}")
    logger.infor("="*60)

    #validate the required environment variables
    required_vars=[
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_VERSION',
        'AZURE_OPENAI_EMBEDDING_DEPLOYMENT',
        'AZURE_SEARCH_ENDPOINT',
        'AZURE_SEARCH_API_KEY',
        'AZURE_SEARCH_INDEX_NAME'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set the missing environment variables and try again.")
        return
    
    #initialize the embedding model
    try:
        logger.info("Initializing Azure OpenAI Embeddings...")
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT","text-embedding-3-small"),
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key = os.getenv("AZURE_OPENAI_API_KEY"),
            openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION","2024-02-01"),
        )
        logger.info("Embeddings initialized successfully.")
    
    except Exception as e:
        logger.error(f"Error initializing embeddings: {e}")
        logger.error("Please check your Azure OpenAI configuration and try again.")
        return
    
    #initialize the Azure Search vector store
    try:
        logger.info("Initializing Azure AI Search vector store...")
        vectorstore = AzureOpenAIEmbeddings(
            azure_search_deployment = os.getenv("AZURE_SEARCH_ENDPOINT"),
            azure_search_key = os.getenv("AZURE_SEARCH_API_KEY"),
            index_name = index_name,
            embedding_function = embeddings.embed_query,
        )
        logger.info(f"Vector Store initialized for index: {index_name}")
    
    except Exception as e:
        logger.error(f"Error initializing Azure Search: {e}")
        logger.error("Please check your Azure Search endpoints and try again.")
        return
    
    #Find PDF files
    pdf_files = glob.glob(os.path.join(data_folder,"*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {data_folder}. Please add PDF documents to index.")
    logger.info(f"Found {len(pdf_files)} PDF files to process:{[os.path.basename(f) for f in pdf_files]}")

    all_splits = []

    # process each pdf
    for pdf_path in pdf_files:
        try:
            logger.info(f"loading{os.path.basename(pdf_path)}....")
            loader = PyPDFLoader(pdf_path)
            raw_docs = loader.load()

            #Chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(raw_docs)
            for split in splits:
                split.metadata["source"] = os.path.basename(pdf_path)

            all_splits.extend(splits)
            logger.info(f"Split into{len(splits)} chunks")

        except Exception as e:
            logger.error(f"Failed to process{pdf_path}: {e}")

    #upload the chunks to Azure Search
    if all_splits:
        logger.info(f"Uploading {len(all_splits)} chunks to Azure Search index: {index_name}...")
        try:
            #azure search accepts batches automatically from this method
            vectorstore.add_documents(all_splits)
            logger.info("="*60)
            logger.info("Document indexing completed successfully!")
            logger.info(f"Total chunks indexed: {len(all_splits)}")
            logger.info("="*60)
        except Exception as e:
            logger.error(f"Error uploading documents to Azure Search: {e}")
            logger.error("Please check your Azure Search configuration and try again.")
    else:
        logger.warning("No document chunks to upload. Please check the input documents and try again.")

if __name__ == "__main__":
    index_docs()