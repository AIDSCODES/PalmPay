import urllib.request
import json
import time
import io
from PIL import Image, ImageDraw
import numpy as np

base = 'http://127.0.0.1:8000'

ts = int(time.time())

import random

rand_gen = random.Random(time.time() * 1000)
base_color = (rand_gen.randint(10, 80), rand_gen.randint(40, 150), rand_gen.randint(30, 160))
inner_color = (rand_gen.randint(60, 200), rand_gen.randint(60, 200), rand_gen.randint(60, 200))

def make_distinct_palm_sample(variation):
    img = Image.new('RGB', (224, 224), color=base_color)
    d = ImageDraw.Draw(img)
    d.rectangle([25, 25, 195, 195], fill=inner_color, outline=(20, 20, 20), width=4)
    # Vein lines with slight perturbation
    for i in range(10):
        d.line([(25 + i * 17 + variation * 2, 25), (195 - i * 17 - variation * 2, 195)], fill=(10, 15, 10), width=4)
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

samples = [make_distinct_palm_sample(i) for i in range(3)]
boundary = '----WebKitFormBoundaryPalmPayUploadTest'

# 1. Test Quality Check with uploaded image file
body_q = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="image"; filename="palm_upload_sample.jpg"\r\n'
    f'Content-Type: image/jpeg\r\n\r\n'
).encode('utf-8') + samples[0] + f'\r\n--{boundary}--\r\n'.encode('utf-8')

req_q = urllib.request.Request(
    f'{base}/api/v1/biometric/quality',
    data=body_q,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
resp_q = urllib.request.urlopen(req_q)
q_res = json.loads(resp_q.read().decode('utf-8'))
print('Quality check response:', q_res)
assert resp_q.status == 200 and q_res['quality_score'] >= 0.5, f"Quality low: {q_res}"
print(f"  [OK] Quality Score: {q_res['quality_score']:.2f} (Acceptable: {q_res['is_acceptable']})")

# 2. Test Registration with 3 uploaded palm samples
ts = int(time.time())
reg_body = bytearray()
data = {'name': f'Uploaded Palm User {ts % 10000}', 'phone': f'+9198{ts % 100000000:08d}'}
for k, v in data.items():
    reg_body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode('utf-8'))

for i, s in enumerate(samples):
    reg_body.extend(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="samples"; filename="uploaded_palm_{i+1}.jpg"\r\n'
        f'Content-Type: image/jpeg\r\n\r\n'.encode('utf-8')
    )
    reg_body.extend(s)
    reg_body.extend(b'\r\n')
reg_body.extend(f'--{boundary}--\r\n'.encode('utf-8'))

req_reg = urllib.request.Request(
    f'{base}/api/v1/users/register',
    data=bytes(reg_body),
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
resp_reg = urllib.request.urlopen(req_reg)
reg_res = json.loads(resp_reg.read().decode('utf-8'))
print('Registration response:', reg_res)
assert resp_reg.status == 201
user_id = reg_res["user_id"]
print(f"\n[SUCCESS] Successfully enrolled customer via uploaded palm image files!")
print(f"  User ID: {user_id}")
print(f"  Message: {reg_res.get('message')}")
