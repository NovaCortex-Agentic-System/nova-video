---
name: tool-video-upload
description: "Uploadează un fișier video local pe Zernio și returnează URL public partajabil. Compresie opțională via FFmpeg înainte de upload."
triggers:
  - "uploadează video"
  - "trimite pe zernio"
  - "url public video"
  - "partajează clipul"
  - "link video"
secrets_required:
  - ZERNIO_API_KEY
outputs:
  - URL public Zernio (string)
runtime_dependencies:
  - python3
  - requests (pip install requests)
  - ffmpeg (opțional, pentru compresie)
---

# Skill: Upload Video pe Zernio

## Pas 0: Verifică fișierul

Primești `input_video_path` din skill-ul anterior sau de la utilizator.

```bash
FILE_SIZE=$(du -m "${input_video_path}" 2>/dev/null | cut -f1)
echo "Dimensiune: ${FILE_SIZE}MB"
```

Dacă fișierul nu există sau e sub 100KB, raportează eroarea și oprește.

## Pas 1: Compresie opțională

Dacă fișierul e mai mare de 50MB, propune compresie:

> "Fișierul are [N]MB. Recomand compresie FFmpeg înainte de upload (reduce la ~[estimat]MB, pierdere vizuală minimă). Comprimi?"

Dacă confirmă:

```bash
COMPRESSED_PATH="${input_video_path%.mp4}-compressed.mp4"
ffmpeg -i "${input_video_path}" \
  -vcodec libx264 -crf 28 -preset fast \
  -acodec aac -b:a 128k \
  "${COMPRESSED_PATH}" -y
input_video_path="${COMPRESSED_PATH}"
```

## Pas 2: Upload pe Zernio

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a

python3 - <<'EOF'
import os, sys, json, requests
from pathlib import Path

api_key = os.environ.get("ZERNIO_API_KEY", "")
if not api_key:
    print(json.dumps({"error": "ZERNIO_API_KEY lipsă din environment"}))
    sys.exit(1)

file_path = Path("${input_video_path}")
file_size = file_path.stat().st_size

# Solicită presigned URL
resp = requests.post(
    "https://api.zernio.com/v1/upload/presign",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={"filename": file_path.name, "size": file_size, "content_type": "video/mp4"},
    timeout=15,
)
if resp.status_code != 200:
    print(json.dumps({"error": f"Presign eșuat: HTTP {resp.status_code}", "detail": resp.text}))
    sys.exit(1)

data = resp.json()
upload_url = data.get("upload_url") or data.get("url")
public_url = data.get("public_url") or data.get("file_url")

# Upload PUT
with open(file_path, "rb") as f:
    put_resp = requests.put(upload_url, data=f, headers={"Content-Type": "video/mp4"}, timeout=120)

if put_resp.status_code not in (200, 201, 204):
    print(json.dumps({"error": f"Upload PUT eșuat: HTTP {put_resp.status_code}"}))
    sys.exit(1)

print(json.dumps({"status": "ok", "public_url": public_url, "size_bytes": file_size}))
EOF
```

Parsează output-ul:
- `public_url` — URL-ul public al videoclipului pe Zernio
- `size_bytes` — dimensiunea uploadată

## Pas 3: Livrare

Raportează utilizatorului:
- URL public (copyable, gata de partajat)
- Dimensiunea fișierului uploadat
- Dacă s-a aplicat compresie: dimensiunea originală vs. comprimată

```
Video live la: [public_url]
Dimensiune: [N]MB
```

## Rules

- Nu uploada fără confirmare explicită din partea utilizatorului
- Dacă fișierul > 50MB, propune întotdeauna compresia înainte de upload
- URL-ul public trebuie raportat explicit în mesajul final
- Dacă upload-ul eșuează, raportează eroarea completă (nu ascunde detaliile)
