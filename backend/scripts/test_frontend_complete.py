"""Test frontend integration and API flows"""
import urllib.request
import json
import uuid
import io
from PIL import Image, ImageDraw
import numpy as np

base = 'http://127.0.0.1:8000'

def run_tests():
    print('=== 1. Testing Frontend Static Delivery ===')
    with urllib.request.urlopen(f'{base}/app/') as r:
        html = r.read().decode('utf-8')
        assert '<title>PalmPay' in html
        assert 'id="view-checkout"' in html
        assert 'id="view-enrollment"' in html
        assert 'id="view-wallets"' in html
        assert 'id="view-transactions"' in html
        assert 'id="view-admin"' in html
        print('  [OK] index.html loaded, all views present')

    with urllib.request.urlopen(f'{base}/app/style.css') as r:
        css = r.read().decode('utf-8')
        assert '--cyan-primary' in css
        assert 'laserScan' in css
        print('  [OK] style.css loaded with full design system')

    with urllib.request.urlopen(f'{base}/app/app.js') as r:
        js = r.read().decode('utf-8')
        assert 'drawSyntheticPalmVein' in js
        assert 'handleScanAndIdentify' in js
        assert 'handleConfirmPayment' in js
        print('  [OK] app.js loaded with complete client logic')

    print('\n=== 2. Testing Biometric Scanner & POS Checkout Flow ===')

    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'

    # Generate synthetic palm vein matching pattern
    def make_palm_jpeg(seed_offset):
        arr = np.random.RandomState(42 + seed_offset).randint(60, 180, (224, 224, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        draw = ImageDraw.Draw(img)
        draw.ellipse([30, 30, 194, 194], fill=(130, 80, 50), outline=(30, 15, 10), width=3)
        draw.line([112, 190, 80, 100], fill=(20, 10, 5), width=4)
        draw.line([112, 190, 140, 90], fill=(20, 10, 5), width=4)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        return buf.getvalue()

    scan_sample = make_palm_jpeg(0)

    # 1. Test Quality Check API
    body_quality = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="image"; filename="palm_test.jpg"\r\n'
        f'Content-Type: image/jpeg\r\n\r\n'
    ).encode() + scan_sample + f'\r\n--{boundary}--\r\n'.encode()

    req_q = urllib.request.Request(f'{base}/api/v1/biometric/quality', data=body_quality, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req_q) as r:
        q_data = json.loads(r.read())
        assert q_data['is_acceptable'] is True
        print(f'  [OK] Biometric Quality check: score={round(q_data["quality_score"], 2)}, acceptable={q_data["is_acceptable"]}')

    # 2. Test Biometric Identify API
    body_id = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="scan.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
    ).encode() + scan_sample + f'\r\n--{boundary}--\r\n'.encode()

    req_id = urllib.request.Request(f'{base}/api/v1/biometric/identify', data=body_id, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req_id) as r:
        id_res = json.loads(r.read())
        matched_user_id = id_res['user_id']
        assert id_res['matched'] is True, f'Expected match but got: {id_res}'
        similarity = round(id_res.get('similarity', 0) * 100, 1)
        print(f'  [OK] Biometric Identification: Matched user {matched_user_id} with {similarity}% similarity')

    # 3. Test Wallet Top-Up (for the matched customer)
    topup_payload = json.dumps({'amount': 500.0, 'description': 'Terminal reload'}).encode()
    req_topup = urllib.request.Request(f'{base}/api/v1/wallets/{matched_user_id}/topup', data=topup_payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req_topup) as r:
        topup_res = json.loads(r.read())
        print(f'  [OK] Wallet Top-Up: balance = INR {topup_res["balance"]}')

    # 4. Test POS Payment Checkout
    pay_payload = json.dumps({
        'user_id': matched_user_id,
        'amount': 250.0,
        'currency': 'INR',
        'description': 'Palm Biometric POS Checkout'
    }).encode()
    idem_key = str(uuid.uuid4())
    req_pay = urllib.request.Request(
        f'{base}/api/v1/payments',
        data=pay_payload,
        headers={
            'Content-Type': 'application/json',
            'X-Device-ID': 'e8b9252d-c48a-4f38-ae94-10a1a46dffe1',
            'X-Device-Key': 'ZuqDrnh4-U2slC9A3odO0_r3UqJcjqcn-qwgcqrBkCg',
            'Idempotency-Key': idem_key
        }
    )
    with urllib.request.urlopen(req_pay) as r:
        pay_res = json.loads(r.read())
        assert pay_res['success'] is True
        print(f'  [OK] POS Payment Authorized: Ref={pay_res["transaction_reference"]} Remaining=INR {pay_res["remaining_balance"]}')

    # 5. Test Customer Statement / Transactions Ledger
    with urllib.request.urlopen(f'{base}/api/v1/transactions/{matched_user_id}') as r:
        tx_res = json.loads(r.read())
        assert tx_res['total'] >= 1
        print(f'  [OK] Customer Ledger Statement: {tx_res["total"]} transaction(s) verified')

    print('\n=== 3. Testing Admin & Hardware Diagnostics ===')

    # 6. Admin Model Telemetry
    req_model = urllib.request.Request(
        f'{base}/api/v1/admin/model/status',
        headers={'X-Admin-Key': 'your-admin-api-key-change-in-production'}
    )
    with urllib.request.urlopen(req_model) as r:
        model_status = json.loads(r.read())
        print(f'  [OK] Model Telemetry: {model_status["model_version"]} ({model_status["model_type"]}, {model_status["embedding_dim"]}-dim)')

    # 7. Device Authentication Check
    auth_payload = json.dumps({
        'device_id': 'e8b9252d-c48a-4f38-ae94-10a1a46dffe1',
        'device_key': 'ZuqDrnh4-U2slC9A3odO0_r3UqJcjqcn-qwgcqrBkCg'
    }).encode()
    req_dev_auth = urllib.request.Request(
        f'{base}/api/v1/devices/authenticate',
        data=auth_payload,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req_dev_auth) as r:
        dev_res = json.loads(r.read())
        print(f'  [OK] Hardware Terminal Authentication: {dev_res["device_name"]} ({dev_res["connection_status"]})')

    # 8. User Management List
    req_users = urllib.request.Request(
        f'{base}/api/v1/admin/users?page=1&page_size=20',
        headers={'X-Admin-Key': 'your-admin-api-key-change-in-production'}
    )
    with urllib.request.urlopen(req_users) as r:
        users_res = json.loads(r.read())
        print(f'  [OK] Admin User Directory: {users_res["total"]} registered user accounts')

    print('\n=================================================================')
    print(' ALL 8 FRONTEND & BACKEND INTEGRATION TESTS PASSED PERFECTLY! ')
    print('=================================================================')

if __name__ == '__main__':
    run_tests()
