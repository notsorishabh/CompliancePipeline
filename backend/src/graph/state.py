import operator
from typing import Any,Dict,Annotated,Optional,TypedDict,List

class ComplianceIssue(TypedDict):
    category: str
    description: str
    severity: str
    timestamp: Optional[str]

class VideoAuditState(TypedDict):
    video_url: str
    video_id: str


    #ingestion and exraction data
    local_file_path : Optional[str]
    video_metadata: Dict[str, Any]
    transcript: Optional[str]
    ocr_text: List[str]

    #analysis results
    #stores the list of violations found during the compliance check by AI
    compliance_results : Annotated[List[ComplianceIssue],operator.add]

    #final deliverables
    final_status: str
    final_report: str

    #system observability
    #error logs: API timeout, system level errors
    errors : Annotated[List[str],operator.add]
