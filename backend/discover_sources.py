import json
import urllib.request

def fetch_beans_youtube_videos():
    channel_url = "https://www.youtube.com/@beansroute3677/videos"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    req = urllib.request.Request(channel_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    idx = html.find('ytInitialData = ')
    if idx == -1:
        print("Could not find ytInitialData")
        return []

    start_json = idx + len('ytInitialData = ')
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(html[start_json:])
    
    videos = []
    seen = set()

    def search_videos(obj):
        if isinstance(obj, dict):
            # Check for videoRenderer or compactVideoRenderer or richItemRenderer
            if "videoRenderer" in obj:
                vr = obj["videoRenderer"]
                vid = vr.get("videoId")
                title_runs = vr.get("title", {}).get("runs", [])
                title = title_runs[0].get("text") if title_runs else "Untitled"
                length = vr.get("lengthText", {}).get("simpleText", "")
                if vid and vid not in seen:
                    seen.add(vid)
                    videos.append({
                        "video_id": vid,
                        "title": title,
                        "length": length,
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    })
            for v in obj.values():
                search_videos(v)
        elif isinstance(obj, list):
            for item in obj:
                search_videos(item)

    search_videos(data)
    print(f"Extracted {len(videos)} videos from channel!")
    return videos

if __name__ == "__main__":
    vids = fetch_beans_youtube_videos()
    with open("data/youtube_videos.json", "w", encoding="utf-8") as f:
        json.dump(vids, f, indent=2)
    for i, v in enumerate(vids, 1):
        print(f"{i}. [{v['video_id']}] {v['title']} ({v['length']}) -> {v['url']}")
