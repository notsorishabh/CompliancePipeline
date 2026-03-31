import json
import os
from typing import Dict, Any,List
import logging 
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.messages import HumanMessage, SystemMessage

from backend.src.graph.state import VideoAuditState, ComplianceIssue

from backend.src.services.video_indexer import VideoIndexerServices

logger = logging.getLogger("brand-guardian")
logging.basicConfig(level=logging.INFO)

def index_video_node(state: VideoAuditState) -> Dict[str,any]:
    '''
    Download the youtube video from url.
    Upload it to Azure video Indexer.
    extract the insights
    '''
    video_url = state.get("video_url")
    video_id_input = state.get("video_id","vid.demo")

    logger.info(f"---[Node:Indexer] processing :{video_url}")
    local_file_name = "temp_audit_video.mp4"

    try:
        vi_service = VideoIndexerServices()

        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_path = vi_service.download_youtube_video(video_url, output_path=local_file_name)
        else:
            raise ValueError("Please Provide with a valid youtube url")
        
        azure_video_id = vi_service.upload_video(local_path,video_name = video_id_input)
        logger.info(f"Upload successful, Azure video id: {azure_video_id}")

        if os.path.exists(local_path):
            os.remove(local_path)

        raw_insights = vi_service.wait_for_processing(azure_video_id)

        clean_data = vi_service.extract_data(raw_insights)
        logger.info(f"Data extraction successful")
        return clean_data
    
    except Exception as e:
        logger.error(f"Error in video indexing: {e}")
        return {
            "errors": [str(e)],
            "final_status": "error",
            "transcript": "",
            "ocr_text": []
        }
    
def audio_content_node(state:VideoAuditState)-> Dict[str,any]:
    '''
    perform retrieval augmented generation to audit the content -brand video
    '''
    logger.info("---[Node:Auditor]query knowledge base and llm")
    transcript = state.get("transcript","")
    if not transcript:
        logger.warning("No transcript available for auditing")
        return {
            "final_status": "FAIL",
            "final_report": "No transcript available for auditing"
        }
    
    llm = AzureChatOpenAI(
        azure_deployment= os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT'),
        openai_api_version = os.getenv('AZURE_OPENAI_API_VERSION'),
        temperature=0.0,
    )
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment = 'text-embedding-3-small',
        openai_api_version = os.getenv('AZURE_OPENAI_API_VERSION'),
    )

    vectorstore = AzureSearch(
        azure_search_endpoint= os.getenv('AZURE_SEARCH_ENDPOINT'),
        azure_search_key = os.getenv('AZURE_SEARCH_API_KEY'),
        index_name = os.getenv('AZURE_SEARCH_INDEX_NAME'),
        embedding_function= embeddings.embed_query,
    )

    #RAG retrieval
    ocr_text = state.get("ocr_text",[])
    query_text = f"{transcript}{' '.join(ocr_text)}"
    docs = vectorstore.similarity_search(query_text, k=3)
    retrieved_rules = "\n\n".join([doc.page_content for doc in docs])

    system_prompt=f"""you are a senior brand compliance auditor:
    OFFICIAL REGULATORY RULES:
    {retrieved_rules}
    INSTRUCTIONS:
    1. Analyze the transcript and ocr text
    2.Identify any violations of the rules
    3.Return strictly JSON in the following format:
    {{
    "Compliance Result"[
        {
            "Category": "Name of the rule that was violated",
            "Severity": "High/Medium/Low",
            "Description": "Explanation of Voilation..."
        }
    ],
    "Status":"FAIL",
    "Final Report":"Summary of Findings..."
    }}
    if no voilations are found return "Staus" to "PASS" and "compliance_results" to [].

    """

    user_message = f"""
    VIDEO_METADATA: {state.get("video_metadata",{})}
    TRANSCRIPT: {transcript}
    OCR_TEXT: {ocr_text}
    """
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        content = response.content
        if"```" in content:
            content = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL).group(1)
        audit_data = json.loads(content.strip())

        return{
            "final_status": audit_data.get("Status","FAIL"),
            "compliance_results": audit_data.get("Compliance Result",[]),
            "final_report": audit_data.get("Final Report","No report generated")
        }

    except Exception as e:
        logger.error(f"Error in content auditing: {e}")
        return {
            "final_status": "FAIL",
            "errors": f"Error{str(e)}"
        }
