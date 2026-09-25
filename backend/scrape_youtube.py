import json
import os
import time
from youtube_transcript_api import YouTubeTranscriptApi

def format_timestamp(seconds: float) -> str:
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def chunk_transcript(snippets, video_id, video_title, window_seconds=40.0, min_words=20):
    chunks = []
    current_text = []
    current_start = None
    current_end = None

    for item in snippets:
        # Support both object attributes and dict
        if hasattr(item, "text"):
            text = str(item.text).replace("\n", " ").strip()
            start = float(item.start)
            duration = float(item.duration)
        else:
            text = str(item.get("text", "")).replace("\n", " ").strip()
            start = float(item.get("start", 0.0))
            duration = float(item.get("duration", 0.0))

        end = start + duration

        if current_start is None:
            current_start = start
            current_end = end

        current_text.append(text)
        current_end = max(current_end, end)

        elapsed = current_end - current_start
        word_count = len(" ".join(current_text).split())

        if elapsed >= window_seconds and word_count >= min_words:
            chunk_content = " ".join(current_text).strip()
            chunks.append({
                "chunk_id": f"yt_{video_id}_{int(current_start)}",
                "source_type": "youtube",
                "video_id": video_id,
                "title": video_title,
                "start_seconds": round(current_start, 1),
                "end_seconds": round(current_end, 1),
                "timestamp_str": format_timestamp(current_start),
                "deep_link": f"https://www.youtube.com/watch?v={video_id}&t={int(current_start)}s",
                "text": f"Video: '{video_title}' (at {format_timestamp(current_start)})\nSpoken Transcript:\n{chunk_content}"
            })
            current_text = []
            current_start = None
            current_end = None

    # Handle remaining tail of transcript
    if current_text and current_start is not None:
        chunk_content = " ".join(current_text).strip()
        if len(chunk_content.split()) >= 6:
            chunks.append({
                "chunk_id": f"yt_{video_id}_{int(current_start)}",
                "source_type": "youtube",
                "video_id": video_id,
                "title": video_title,
                "start_seconds": round(current_start, 1),
                "end_seconds": round(current_end, 1),
                "timestamp_str": format_timestamp(current_start),
                "deep_link": f"https://www.youtube.com/watch?v={video_id}&t={int(current_start)}s",
                "text": f"Video: '{video_title}' (at {format_timestamp(current_start)})\nSpoken Transcript:\n{chunk_content}"
            })

    return chunks

def process_youtube_videos(videos_file="data/youtube_videos.json"):
    if not os.path.exists(videos_file):
        print(f"Error: {videos_file} does not exist.")
        return []

    with open(videos_file, "r", encoding="utf-8") as f:
        videos = json.load(f)

    print(f"Processing transcripts for {len(videos)} Beans Route videos with exact second timestamps...")
    all_chunks = []
    success_count = 0
    fallback_count = 0
    yt_api = YouTubeTranscriptApi()

    for i, v in enumerate(videos, 1):
        vid = v["video_id"]
        title = v["title"]
        print(f"[{i:02d}/{len(videos)}] Processing: '{title}' ({vid})...")
        try:
            transcript = yt_api.fetch(vid)
            chunks = chunk_transcript(transcript, vid, title)
            if chunks:
                all_chunks.extend(chunks)
                success_count += 1
                print(f"       -> Successfully generated {len(chunks)} timestamped chunks.")
            else:
                # Video had transcript but too brief
                fallback_count += 1
                all_chunks.append({
                    "chunk_id": f"yt_{vid}_0",
                    "source_type": "youtube",
                    "video_id": vid,
                    "title": title,
                    "start_seconds": 0.0,
                    "end_seconds": 0.0,
                    "timestamp_str": "00:00",
                    "deep_link": f"https://www.youtube.com/watch?v={vid}",
                    "text": f"Video Guide: '{title}'. Features walkthrough and instructions for {title} on Beans Route."
                })
        except Exception as e:
            fallback_count += 1
            print(f"       -> Captions unavailable ({type(e).__name__}). Created summary metadata chunk.")
            all_chunks.append({
                "chunk_id": f"yt_{vid}_0",
                "source_type": "youtube",
                "video_id": vid,
                "title": title,
                "start_seconds": 0.0,
                "end_seconds": 0.0,
                "timestamp_str": "00:00",
                "deep_link": f"https://www.youtube.com/watch?v={vid}",
                "text": f"Video Tutorial: '{title}'. Covers Beans Route operations, mobile app navigation, and feature setup for {title}."
            })

    print(f"\nProcessing Complete!")
    print(f" - Videos with high-precision timestamp transcripts: {success_count}")
    print(f" - Videos with topic summary metadata:             {fallback_count}")
    print(f" - Total YouTube Knowledge Chunks:                 {len(all_chunks)}")
    return all_chunks

if __name__ == "__main__":
    chunks = process_youtube_videos()
    with open("data/youtube_chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print("Saved chunks to data/youtube_chunks.json")
