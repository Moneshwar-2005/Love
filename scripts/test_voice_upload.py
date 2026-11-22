import io
import json
import ssl
import struct
import urllib.request
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ca_path = PROJECT_ROOT / "secrets" / "certs" / "love_dev_ca.crt"
ctx = ssl.create_default_context(cafile=str(ca_path))

# 1. Login
login_data = json.dumps({
    "email_or_username": "work_persist_1795095542",
    "password": "SecurePassword123!"
}).encode()
req = urllib.request.Request(
    "https://192.168.0.176:8000/api/v1/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, context=ctx) as r:
    token = json.loads(r.read().decode())["access_token"]
print("1. Authentication: 200 OK")

# 2. Generate 1 second of 16kHz PCM WAV audio
wav_buf = io.BytesIO()
with wave.open(wav_buf, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(struct.pack("<" + ("h" * 16000), *([0] * 16000)))
wav_bytes = wav_buf.getvalue()
print(f"2. Audio generation: {len(wav_bytes)} bytes WAV (16kHz 16-bit mono)")

# 3. Build multipart payload with field 'file'
boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
body = bytearray()
body.extend(f"--{boundary}\r\n".encode())
body.extend(b'Content-Disposition: form-data; name="file"; filename="speech.wav"\r\n')
body.extend(b"Content-Type: audio/wav\r\n\r\n")
body.extend(wav_bytes)
body.extend(f"\r\n--{boundary}\r\n".encode())
body.extend(b'Content-Disposition: form-data; name="provider_id"\r\n\r\n')
body.extend(b"mock\r\n")
body.extend(f"--{boundary}--\r\n".encode())

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": f"multipart/form-data; boundary={boundary}",
    "Content-Length": str(len(body)),
}

# 4. Upload to /api/v1/voice/transcribe with mock provider fallback
req = urllib.request.Request(
    "https://192.168.0.176:8000/api/v1/voice/transcribe",
    data=bytes(body),
    headers=headers,
)
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        res = json.loads(r.read().decode())
        print(f"3. STT Multipart Upload Status: {r.status} OK")
        print(f"   Transcription Result: {res}")
except urllib.error.HTTPError as e:
    print(f"3. STT Multipart Upload HTTP Error: {e.code} {e.read().decode()}")

# 5. Test TTS synthesis
tts_payload = json.dumps({"text": "Hello from LOVE personal assistant.", "provider_id": "mock"}).encode()
req = urllib.request.Request(
    "https://192.168.0.176:8000/api/v1/voice/synthesize",
    data=tts_payload,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        res = json.loads(r.read().decode())
        print(f"4. TTS Synthesis Status: {r.status} OK")
        print(f"   Format: {res.get('audio_format')}, Sample Rate: {res.get('sample_rate')}, Base64 Length: {len(res.get('audio_base64', ''))}")
except urllib.error.HTTPError as e:
    print(f"4. TTS Synthesis HTTP Error: {e.code} {e.read().decode()}")
