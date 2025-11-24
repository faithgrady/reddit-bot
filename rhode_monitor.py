import os
import time
import requests
import praw
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Keywords to monitor (adjust these for your use case)
KEYWORDS = [
    "DM to buy",
    "for sale",
    "to sell",
]

# Subreddits to monitor (you can change to "all" or add more with +)
SUBREDDITS = "rhodeskin"


def keyword_in_text(text: str) -> str | None:
    """
    Return the first keyword found in the text (case-insensitive),
    or None if no keyword is present.
    """
    lower = text.lower()
    for kw in KEYWORDS:
        if kw.lower() in lower:
            return kw
    return None


def send_discord_alert(
    kind: str,
    subreddit: str,
    author: str,
    text: str,
    permalink: str,
    keyword: str,
) -> None:
    """
    Send a simple alert message to a Discord channel via webhook.
    """
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL is not set; skipping Discord alert.")
        return

    # Keep the preview reasonable in length
    preview = text[:800]
    url = f"https://www.reddit.com{permalink}"

    content = (
        f"🚨 New Reddit {kind} mentioning **{keyword}** in r/{subreddit}\n"
        f"Author: u/{author}\n"
        f"Link: {url}\n\n"
        f"> {preview.replace('\n', ' ')[:500]}"
    )

    try:
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": content},
            timeout=10,
        )
        if resp.status_code != 204 and resp.status_code != 200:
            print(f"Discord webhook error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Failed to send Discord message: {e}")


def monitor_comments(reddit: praw.Reddit) -> None:
    """
    Stream new comments from the configured subreddits and
    send alerts when a keyword is found.
    """
    subreddit = reddit.subreddit(SUBREDDITS)
    print(f"Monitoring comments in r/{SUBREDDITS} for keywords: {KEYWORDS}")

    # skip_existing=True means "start from now", not historical comments
    for comment in subreddit.stream.comments(skip_existing=True):
        try:
            body = comment.body or ""
            hit = keyword_in_text(body)
            if hit:
                print(
                    f"Found '{hit}' in comment {comment.id} in r/{comment.subreddit.display_name}"
                )
                send_discord_alert(
                    kind="comment",
                    subreddit=str(comment.subreddit.display_name),
                    author=str(comment.author),
                    text=body,
                    permalink=comment.permalink,
                    keyword=hit,
                )
        except Exception as e:
            print(f"Error processing comment: {e}")
            time.sleep(5)


def main() -> None:
    # Create Reddit instance (read-only)
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

    print("Reddit read_only:", reddit.read_only)

    # Basic loop so if the stream crashes, it restarts after a short delay
    while True:
        try:
            monitor_comments(reddit)
        except Exception as e:
            print(f"Comment stream crashed: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
