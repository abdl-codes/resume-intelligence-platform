import urllib.request
import urllib.parse
import uuid
import sys
import json

URL = "http://localhost:8081/api/analyze"

jd_text = "Looking for a software engineer with Python, Java, and SQL experience. Must have 3 years of experience."

resumes = [
    ("alice.txt", "Alice Engineer. Experienced in Python and SQL for 4 years."),
    ("bob.txt", "Bob Developer. I know Java. Very hard worker. Hard worker hard worker."),
    ("charlie.txt", "Charlie Programmer. Python and Java expert. 3 years experience.")
]

boundary = uuid.uuid4().hex
body = bytearray()

# Add JD
body.extend(f"--{boundary}\r\n".encode('utf-8'))
body.extend(b'Content-Disposition: form-data; name="jd_text"\r\n\r\n')
body.extend(jd_text.encode('utf-8'))
body.extend(b'\r\n')

# Add resumes
for filename, text in resumes:
    body.extend(f"--{boundary}\r\n".encode('utf-8'))
    body.extend(f'Content-Disposition: form-data; name="resumes"; filename="{filename}"\r\n\r\n'.encode('utf-8'))
    body.extend(text.encode('utf-8'))
    body.extend(b'\r\n')

body.extend(f"--{boundary}--\r\n".encode('utf-8'))

req = urllib.request.Request(
    URL,
    data=bytes(body),
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Total candidates: {data['summary']['total_candidates']}")
        for c in data['candidates']:
            print(f"Candidate: {c['filename']}, Rank: {c['rank']}, Score: {c['qualification_match']['overall_match_score']}")
        sys.exit(0)
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read().decode())
    sys.exit(1)
