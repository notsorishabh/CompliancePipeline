import os 
import time 
import logging
import requests
import yt_dlp
import urllib3
from azure.identity import DefaultAzureCredential

logger = logging.getLogger("VideoIndexer")

class VideoIndexerServices:
    def __init__(self):
        self.account_id = os.getenv("AZURE_VI_ACCOUNT_ID")
        self.location = os.getenv("AZURE_VI_LOCATION")
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        self.resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        self.vi_name = os.getenv("AZURE_VI_NAME","my-project-VI")
        self.credential = DefaultAzureCredential()

    def get_access_token(self):
        '''
        generate ARM access token
        '''
        try:
            token_object = self.credential.get_token("https://management.azure.com/.default")
            return token_object.token
        except Exception as e:
            logger.error(f"Error obtaining access token: {e}")
            raise

    def get_account_token(self,arm_access_token):
        '''
        Exchange ARM token for Video Indexer account token
        '''
        url=(
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.vi_name}"
            f"/generateAccessToken?api-version=2025-01-01"
        )
        headers = {"Authorization": f"Bearer {arm_access_token}"}
        payload = {"permissionType":"Contributor","scope": "Account"}
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = requests.Session()
        response = session.post(url, headers=headers, json=payload, timeout=30, verify=False)
        if response.status_code != 200:
            raise Exception(f"Failed to get account token: {response.status_code} - {response.text}")
        return response.json().get("accessToken")
    
    def download_youtube_video(self,url,output_path="temp_video.mp4"):
        '''
        Download youtube video using yt-dlp to a local file
        '''
        logger.info(f"Downloading video from URL: {url}")
        
        ydl_opts ={
            "format":"best[ext=mp4]",
            "outtmpl": output_path,
            "quiet": False,
            "no_warnings": True,
            "extractor_args":{"youtube":{"player_client":["android","web"]}},
            "http_headers":{
                "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            logger.info(f"Video downloaded successfully ")
            return output_path
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            raise

    #upload the video to Azure Video Indexer for processing
    def upload_video(self,video_path,video_name):
        arm_token = self.get_access_token()
        vi_token = self.get_account_token(arm_token)

        api_url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos"

        params = {
            "accessToken": vi_token,
            "name": video_name,
            "privacy": "Private",
            "indexingPreset": "Default",
        }

        logger.info(f"Uploading video to Azure Video Indexer: {video_name}")

        #open the file in binary and stream it in Azure
        try:
            with open(video_path, "rb") as video_file:
                files = {"file": (video_name, video_file, "video/mp4")}
                response = requests.post(
                    api_url,
                    params=params,
                    files=files,
                    timeout=300,  # 5 min timeout
                    stream=False
                )
        except ConnectionError as e:
            logger.info("Connection error during video upload, retrying with URL directly...")
            params["videoUrl"] = "https://youtu.be/dT7S75eYhcQ"

        if response.status_code != 200:
            raise Exception(f"Failed to upload video:{response.text}")
        response_data = response.json()
        video_id = response_data.get("id") or response_data.get("videoId") or response_data.get("externalId")
        logger.info(f"Video ID: {video_id}")
        return video_id
        
    def wait_for_processing(self, video_id):
        logger.info(f"Waiting for processing: {video_id}")
        while True:
            try:
                arm_token = self.get_access_token()
                vi_token = self.get_account_token(arm_token)
                
                url = (
                    f"https://api.videoindexer.ai/{self.location}"
                    f"/Accounts/{self.account_id}/Videos/{video_id}/Index"
                )
                
                # Fresh session, no keep-alive
                session = requests.Session()
                session.headers.update({"Connection": "close"})
                response = session.get(
                    url,
                    params={"accessToken": vi_token},
                    timeout=30
                )
                session.close()

                if response.status_code != 200:
                    logger.warning(f"Poll error {response.status_code}: {response.text[:200]}")
                    time.sleep(30)
                    continue

                data = response.json()
                logger.info(f"Poll keys: {list(data.keys())}")
                logger.info(f"Full response: {str(data)[:500]}")

                state = data.get("state")
                logger.info(f"Current state: {state}")

                if state == "Processed":
                    logger.info("Processing completed")
                    return data
                elif state == "Failed":
                    raise Exception(f"Video processing failed: {data}")
                elif state is None:
                    logger.warning(f"State is None — check poll keys above")

            except ConnectionResetError as e:
                logger.warning(f"Connection reset during poll, retrying in 30s: {e}")
            except Exception as e:
                logger.warning(f"Poll error, retrying in 30s: {type(e).__name__}: {e}")

            logger.info("Retrying in 30 seconds...")
            time.sleep(30)


    def extract_data(self,vi_json):
        '''
        parses the json into state format
        '''
        transcript_lines =[]
        for v in vi_json.get("videos",[]):
            for insight in v.get("insights",[]).get("transcript",[]):
                transcript_lines.append(insight.get("text"))

        ocr_texts = []
        for v in vi_json.get("videos",[]):
            for insight in v.get("insights",[]).get("ocr",[]):
                ocr_texts.append(insight.get("text"))

        return{
            "transcript": " ".join(transcript_lines),
            "ocr_text": ocr_texts,
            "video_metadata":{
                "duration": vi_json.get("summarizedInsights",{}).get("duration"),
                "platform":"youtube"
            }
        }