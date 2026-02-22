import os
import tempfile
import requests
import librosa
import random
import ffmpeg
import torch
from supabase import create_client
from transformers import ClapModel, ClapProcessor
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Failed to initialize Supabase in process: {e}")

# Load model globally so it stays in memory across background tasks
model_id = "laion/clap-htsat-unfused"
try:
    processor = ClapProcessor.from_pretrained(model_id)
    model = ClapModel.from_pretrained(model_id)
except Exception as e:
    print(f"Failed to load CLAP model globally: {e}")
    processor = None
    model = None

def make_preview(track_id: str, audio_url: str):
    print(f"make_preview background task started for {track_id}")
    r = requests.get(audio_url)
    if r.status_code != 200:
        print("Failed to download audio for preview")
        return
        
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_in, \
         tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f_out:
        f_in.write(r.content)
        f_in.flush()
        
        try:
            (
                ffmpeg.input(f_in.name, ss=30)
                .output(f_out.name, t=10, format='mp3')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error:
            try:
                (
                    ffmpeg.input(f_in.name)
                    .output(f_out.name, t=10, format='mp3')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except ffmpeg.Error:
                print("FFmpeg slicing failed")
                os.remove(f_in.name)
                os.remove(f_out.name)
                return
        
        if supabase:
            with open(f_out.name, "rb") as po:
                preview_path = f"previews/{track_id}.mp3"
                supabase.storage.from_("audio").upload(
                    path=preview_path, 
                    file=po.read(), 
                    file_options={"content-type": "audio/mpeg"}
                )
            preview_url = f"{SUPABASE_URL}/storage/v1/object/public/audio/{preview_path}"
            supabase.table("tracks").update({"preview_file_url": preview_url, "status": "PREVIEW_READY"}).eq("id", track_id).execute()
            
    os.remove(f_in.name)
    os.remove(f_out.name)


def make_embedding(track_id: str, audio_url: str):
    print(f"make_embedding background task started for {track_id}")
    if not supabase or not model or not processor:
        print("Missing deps for embedding")
        return
        
    r = requests.get(audio_url)
    if r.status_code != 200:
        print("Failed to download audio for embedding")
        return
        
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_in:
        f_in.write(r.content)
        f_in.flush()
        
        try:
            audio_data, sr = librosa.load(f_in.name, sr=48000, duration=10.0)
            inputs = processor(audios=audio_data, return_tensors="pt", sampling_rate=48000)
            with torch.no_grad():
                audio_embed = model.get_audio_features(**inputs)
                
            embedding_list = audio_embed[0].tolist()
        except Exception as e:
            print(f"Embedding extraction failed: {str(e)}")
            os.remove(f_in.name)
            return
            
    os.remove(f_in.name)
    
    vec_str = "[" + ",".join(map(str, embedding_list)) + "]"
    
    map_x = random.uniform(0, 100)
    map_y = random.uniform(0, 100)

    update_data = {
        "embedding_vector": vec_str,
        "map_x": map_x,
        "map_y": map_y,
        "status": "LIVE"
    }
    
    try:
        supabase.table("tracks").update(update_data).eq("id", track_id).execute()
        print(f"Successfully embedded and mapped {track_id}")
    except Exception as e:
        print(f"DB update failed: {str(e)}")
