import subprocess

endpoints = [
    ('/api/v1/auth/me', 'GET'),
    ('/api/v1/intelligence/status', 'GET'),
    ('/api/v1/intelligence/conversations', 'GET'),
    ('/api/v1/memory/stats', 'GET'),
    ('/api/v1/work/tasks', 'GET'),
    ('/api/v1/devices', 'GET'),
    ('/api/v1/sync/status', 'GET'),
    ('/api/v1/voice/transcribe', 'POST')
]

print("=== Unauthenticated Endpoint Security Verification from Physical Phone ===")
for ep, method in endpoints:
    cmd = [
        'adb', '-s', '10BE910T3Y000PF', 'shell',
        f'curl -s -o /dev/null -w "%{{http_code}}" -X {method} http://192.168.0.176:8000{ep}'
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    code = res.stdout.strip()
    status = "REJECTED (SECURE)" if code in ("401", "403") else f"UNEXPECTED ({code})"
    print(f"{method:4} {ep:35} -> HTTP {code} : {status}")
