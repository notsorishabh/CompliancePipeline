import uuid
import json
import logging
from pprint import pprint
from dotenv import load_dotenv

from backend.src.graph.workflow import app

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("brand-guardian-runner")

def run_cli_simulation():
    '''
    simulate the video compliance audit request
    '''
    #generate the session ID
    session_id = str(uuid.uuid4())
    logger.info(f"Starting Audit session: {session_id}")

    #define the initial state
    initial_inputs={
        "video_url":"https://youtu.be/dT7S75eYhcQ",
        "video_id":f"vid_{session_id[:8]}",
        "compliance_result":[],
        "erros":[]
    }

    print("n----initializing workflow----")
    print(f"Input payload:{json.dumps(initial_inputs, indent=2)}")

    try:
        final_state = app.invoke(initial_inputs)
        print("n----workflow completed----")
        print("\ncompliance Audit Report==")
        print(f"Video ID:{final_state.get('video_id')}")
        print(f"Status:{final_state.get('final_status')}")
        print("\n [VIOLATIONS DETECTED]")
        results = final_state.get('compliance_result',[])

        if results:
            for issue in results:
                print(f"-[{issue.get('severity')}] [{issue.get('category')}] [{issue.get('description')}]")
        else:
            print("No violation detected. Video is compliant.")
        print("\n[FINAL_SUMMARY]")
        print(final_state.get('final_report'))
    except Exception as e:
        logger.error(f"Error during workflow execution: {e}")
        raise e

if __name__ == "__main__":
    run_cli_simulation()
