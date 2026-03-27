"""Instagram video download via Instaloader."""

import re
import json
from datetime import datetime
from pathlib import Path

import instaloader

from .config import DATA_DIR, ensure_dirs


def parse_instagram_url(url: str) -> dict:
    """Parse an Instagram URL into account name and/or shortcode.

    Supports:
      - https://www.instagram.com/reel/ABC123/
      - https://www.instagram.com/p/ABC123/
      - https://www.instagram.com/username/
      - https://www.instagram.com/username/reels/
    """
    url = url.strip().rstrip("/")

    # Single post/reel: /reel/SHORTCODE or /p/SHORTCODE
    post_match = re.search(r"instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)", url)
    if post_match:
        return {"type": "post", "shortcode": post_match.group(1)}

    # Account URL: /username or /username/reels
    account_match = re.search(r"instagram\.com/([A-Za-z0-9_.]+)(?:/reels)?/?$", url)
    if account_match:
        username = account_match.group(1)
        if username not in ("p", "reel", "explore", "stories", "accounts"):
            return {"type": "account", "username": username}

    raise ValueError(f"Could not parse Instagram URL: {url}")


def download_post(shortcode: str) -> dict:
    """Download a single Instagram post/reel by shortcode.

    Returns dict with paths and metadata.
    """
    L = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="",
    )

    post = instaloader.Post.from_shortcode(L.context, shortcode)

    if not post.is_video:
        raise ValueError(f"Post {shortcode} is not a video.")

    account_name = post.owner_username
    video_id = shortcode
    video_dir = DATA_DIR / account_name / video_id
    ensure_dirs(video_dir)

    # Download to temp then rename
    L.dirname_pattern = str(video_dir)
    L.filename_pattern = "original"
    L.download_post(post, target=video_dir)

    # Find downloaded video file
    video_file = _find_video_file(video_dir)

    # Save metadata
    metadata = {
        "shortcode": shortcode,
        "account": account_name,
        "caption": post.caption or "",
        "timestamp": post.date_utc.isoformat(),
        "likes": post.likes,
        "comments": post.comments,
        "video_url": f"https://www.instagram.com/reel/{shortcode}/",
        "download_date": datetime.now().isoformat(),
    }
    metadata_path = video_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return {
        "account": account_name,
        "video_id": video_id,
        "video_path": str(video_file),
        "metadata_path": str(metadata_path),
        "video_dir": str(video_dir),
    }


def download_account_videos(username: str, count: int = 1) -> list[dict]:
    """Download latest N video posts from an account.

    Returns list of download result dicts.
    """
    L = instaloader.Instaloader(
        download_videos=False,  # We'll download individually
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
    )

    profile = instaloader.Profile.from_username(L.context, username)
    results = []

    video_count = 0
    for post in profile.get_posts():
        if video_count >= count:
            break
        if not post.is_video:
            continue

        try:
            result = download_post(post.shortcode)
            results.append(result)
            video_count += 1
        except Exception as e:
            print(f"Failed to download {post.shortcode}: {e}")
            continue

    return results


def _find_video_file(video_dir: Path) -> Path:
    """Find the downloaded video file in directory."""
    for ext in (".mp4", ".webm", ".mkv"):
        candidates = list(video_dir.glob(f"*{ext}"))
        if candidates:
            # Rename to original.mp4 if needed
            target = video_dir / f"original{ext}"
            if candidates[0] != target:
                candidates[0].rename(target)
            return target

    raise FileNotFoundError(f"No video file found in {video_dir}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.download <instagram_url> [count]")
        sys.exit(1)

    url = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    parsed = parse_instagram_url(url)

    if parsed["type"] == "post":
        result = download_post(parsed["shortcode"])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        results = download_account_videos(parsed["username"], count)
        print(json.dumps(results, indent=2, ensure_ascii=False))
