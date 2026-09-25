import json
import re
import urllib.request
from html import unescape

def strip_html(html_str):
    if not html_str:
        return ""
    # Remove script and style tags
    clean = re.sub(r'<script.*?</script>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
    # Convert headings, list items, and paragraph tags to linebreaks
    clean = re.sub(r'</?(h[1-6]|p|div|li|br|tr)[^>]*>', '\n', clean, flags=re.IGNORECASE)
    # Remove all remaining HTML tags
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = unescape(clean)
    # Normalize multiple line breaks and spaces
    lines = [line.strip() for line in clean.split('\n')]
    clean = '\n'.join([line for line in lines if line])
    return clean

def fetch_all_zendesk_articles(category_id=6638135489175):
    articles = []
    page = 1
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    print(f"Fetching Zendesk articles for category {category_id}...")
    while True:
        url = f"https://beansai.zendesk.com/api/v2/help_center/en-us/categories/{category_id}/articles.json?page={page}&per_page=100"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                current_articles = data.get("articles", [])
                if not current_articles:
                    break
                
                for art in current_articles:
                    raw_body = art.get("body", "")
                    clean_body = strip_html(raw_body)
                    articles.append({
                        "id": str(art.get("id")),
                        "title": art.get("title", ""),
                        "url": art.get("html_url", ""),
                        "created_at": art.get("created_at"),
                        "updated_at": art.get("updated_at"),
                        "content": clean_body
                    })
                
                print(f"Page {page}: fetched {len(current_articles)} articles (Total so far: {len(articles)})")
                if not data.get("next_page"):
                    break
                page += 1
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

    print(f"Completed! Total Zendesk articles gathered: {len(articles)}")
    return articles

if __name__ == "__main__":
    arts = fetch_all_zendesk_articles()
    with open("data/beans_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(arts, f, indent=2, ensure_ascii=False)
    print("Saved articles to data/beans_knowledge.json")
