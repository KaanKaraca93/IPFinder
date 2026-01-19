from flask import Flask, request, jsonify
from datetime import datetime
import json
import os

app = Flask(__name__)

# NAT IP'ler - Infor MT AWS (EU-Central-1 Frankfurt)
EXPECTED_NAT_IPS = [
    '52.58.37.0',
    '52.29.28.67',
    '18.197.50.73'
]

# Log dosyası
LOG_FILE = 'request_logs.json'

def get_client_ip():
    """İstemcinin gerçek IP adresini al (proxy arkasında bile)"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def log_request(ip_address, endpoint, method, headers, data, is_expected_ip):
    """Gelen istekleri kaydet"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'ip_address': ip_address,
        'endpoint': endpoint,
        'method': method,
        'headers': dict(headers),
        'data': data,
        'is_expected_ip': is_expected_ip,
        'matched_nat_ip': ip_address if is_expected_ip else None
    }
    
    # Mevcut logları oku
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except:
            logs = []
    
    # Yeni log ekle
    logs.append(log_entry)
    
    # Son 1000 kaydı tut
    logs = logs[-1000:]
    
    # Dosyaya yaz
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    
    return log_entry

@app.route('/')
def index():
    """Ana sayfa - Basit bilgi"""
    return jsonify({
        'status': 'active',
        'service': 'IP Source Tracker',
        'expected_nat_ips': EXPECTED_NAT_IPS,
        'endpoints': {
            'webhook': '/webhook (POST/GET/PUT/DELETE)',
            'logs': '/logs',
            'stats': '/stats'
        }
    })

@app.route('/webhook', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def webhook():
    """Webhook endpoint - Tüm istekleri yakala"""
    client_ip = get_client_ip()
    is_expected = client_ip in EXPECTED_NAT_IPS
    
    # Request data'yı al
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.get_data(as_text=True)
    except:
        data = None
    
    # İsteği logla
    log_entry = log_request(
        ip_address=client_ip,
        endpoint=request.path,
        method=request.method,
        headers=dict(request.headers),
        data=data,
        is_expected_ip=is_expected
    )
    
    # Response döndür
    response_data = {
        'success': True,
        'message': 'Request received and logged',
        'your_ip': client_ip,
        'is_expected_nat_ip': is_expected,
        'timestamp': log_entry['timestamp']
    }
    
    if is_expected:
        response_data['message'] = 'VERIFIED: Request from expected NAT IP!'
        response_data['matched_ip'] = client_ip
    else:
        response_data['message'] = 'Request logged but NOT from expected NAT IP'
    
    return jsonify(response_data), 200

@app.route('/logs')
def get_logs():
    """Log kayıtlarını göster (en yeni önce)"""
    if not os.path.exists(LOG_FILE):
        return jsonify({'logs': [], 'count': 0})
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        
        return jsonify({
            'logs': list(reversed(logs)),
            'count': len(logs)
        })
    except:
        return jsonify({'logs': [], 'count': 0})

@app.route('/stats')
def get_stats():
    """İstatistikler ve karşılaştırma"""
    if not os.path.exists(LOG_FILE):
        return jsonify({
            'total_requests': 0,
            'expected_ip_requests': 0,
            'unexpected_ip_requests': 0,
            'expected_nat_ips': EXPECTED_NAT_IPS,
            'comparison': 'No requests logged yet'
        })
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        
        total = len(logs)
        expected = sum(1 for log in logs if log.get('is_expected_ip'))
        
        # IP'lere göre grup
        ip_counts = {}
        for log in logs:
            ip = log.get('ip_address')
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        # Karşılaştırma yap
        comparison = []
        for ip in EXPECTED_NAT_IPS:
            if ip in ip_counts:
                comparison.append(f"✓ {ip}: {ip_counts[ip]} requests (MATCHED)")
            else:
                comparison.append(f"✗ {ip}: 0 requests (NOT SEEN YET)")
        
        unexpected_ips = {ip: count for ip, count in ip_counts.items() if ip not in EXPECTED_NAT_IPS}
        
        return jsonify({
            'total_requests': total,
            'expected_ip_requests': expected,
            'unexpected_ip_requests': total - expected,
            'expected_nat_ips': EXPECTED_NAT_IPS,
            'ip_distribution': ip_counts,
            'comparison': comparison,
            'unexpected_ips': unexpected_ips if unexpected_ips else 'None'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("IP Source Tracker")
    print("=" * 60)
    print(f"Expected NAT IPs:")
    for ip in EXPECTED_NAT_IPS:
        print(f"  • {ip}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port)
