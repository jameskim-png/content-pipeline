# Phase: Download -- Instagram 다운로드 + 오디오 분리

## 1. 환경 체크

```bash
if [ ! -d ".venv" ]; then
    bash setup.sh
else
    source .venv/bin/activate
    python -c "import instaloader, demucs, fal_client, PIL" 2>/dev/null || bash setup.sh
fi
source .venv/bin/activate
python -c "
from dotenv import load_dotenv; import os
load_dotenv()
if not os.getenv('FAL_KEY'): print('MISSING_KEY: FAL_KEY')
else: print('ENV_OK')
"
```

## 2. 다운로드

```bash
source .venv/bin/activate
python -c "
from src.download import parse_instagram_url, download_post, download_account_videos
import json
url = '{URL}'
parsed = parse_instagram_url(url)
if parsed['type'] == 'post':
    results = [download_post(parsed['shortcode'])]
else:
    results = download_account_videos(parsed['username'], {COUNT})
print(json.dumps(results, indent=2, ensure_ascii=False))
"
```

## 3. 오디오 분리

```bash
source .venv/bin/activate
python -c "
from src.audio_separation import separate_audio
from pathlib import Path
import json
video_path = Path('{VIDEO_PATH}')
audio_dir = video_path.parent / 'audio'
result = separate_audio(video_path, audio_dir)
print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))
"
```

## Output
- data/{account}/{video_id}/original.mp4
- data/{account}/{video_id}/audio/vocals.wav, drums.wav, bass.wav, other.wav
