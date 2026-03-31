# test_vi.py
from dotenv import load_dotenv
load_dotenv()

from backend.src.services.video_indexer import VideoIndexerServices
import logging
logging.basicConfig(level=logging.INFO)

vi = VideoIndexerServices()

arm_token = vi.get_access_token()
print("✅ ARM token:", arm_token[:20], "...")

vi_token = vi.get_account_token(arm_token)
print("✅ VI token:", vi_token[:20], "...")

video_id = vi.upload_video("temp_audit_video.mp4", "test-video")
print("✅ Video ID:", video_id)

if video_id:
    print("🔄 Waiting for processing...")
    result = vi.wait_for_processing(video_id)
    print("✅ Processing result:", result)
else:
    print("❌ No video ID returned — check the logged response above")