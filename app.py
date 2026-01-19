from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
from datetime import datetime
import json
import os

app = Flask(__name__)

# Swagger Configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger/"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "IP Source Tracker API",
        "description": "API to track and verify incoming requests from Infor MT AWS NAT IPs (EU-Central-1 Frankfurt)",
        "version": "1.0.0",
        "contact": {
            "name": "IP Source Tracker",
            "url": "https://github.com/KaanKaraca93/IPFinder"
        }
    },
    "host": "ipfinder-1441fde4a5a3.herokuapp.com",
    "basePath": "/",
    "schemes": ["https", "http"],
    "tags": [
        {
            "name": "Tracking",
            "description": "Request tracking endpoints"
        },
        {
            "name": "Monitoring",
            "description": "Logs and statistics"
        }
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

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
    # Heroku ve proxy'ler için header'ları kontrol et
    # X-Forwarded-For: client, proxy1, proxy2
    # İlk IP gerçek client IP'sidir
    
    # X-Forwarded-For header'ı kontrol et
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # Virgülle ayrılmış IP listesinden ilkini al
        ips = [ip.strip() for ip in x_forwarded_for.split(',')]
        if ips and ips[0]:
            return ips[0]
    
    # X-Real-IP header'ı kontrol et
    x_real_ip = request.headers.get('X-Real-IP')
    if x_real_ip:
        return x_real_ip.strip()
    
    # CF-Connecting-IP (Cloudflare)
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip.strip()
    
    # True-Client-IP (Akamai, Cloudflare)
    true_client_ip = request.headers.get('True-Client-IP')
    if true_client_ip:
        return true_client_ip.strip()
    
    # Son çare: request.remote_addr (genelde proxy IP'si)
    return request.remote_addr

def log_request(ip_address, endpoint, method, headers, data, is_expected_ip):
    """Gelen istekleri kaydet"""
    # Debug için tüm IP ile ilgili header'ları kaydet
    ip_headers = {
        'X-Forwarded-For': headers.get('X-Forwarded-For'),
        'X-Real-IP': headers.get('X-Real-IP'),
        'CF-Connecting-IP': headers.get('CF-Connecting-IP'),
        'True-Client-IP': headers.get('True-Client-IP'),
        'Remote-Addr': request.remote_addr
    }
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'ip_address': ip_address,
        'endpoint': endpoint,
        'method': method,
        'headers': dict(headers),
        'ip_debug_headers': ip_headers,
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
    """
    Service Information
    ---
    tags:
      - Monitoring
    responses:
      200:
        description: Service status and available endpoints
        schema:
          type: object
          properties:
            status:
              type: string
              example: active
            service:
              type: string
              example: IP Source Tracker
            expected_nat_ips:
              type: array
              items:
                type: string
              example: ["52.58.37.0", "52.29.28.67", "18.197.50.73"]
            endpoints:
              type: object
              properties:
                webhook:
                  type: string
                  example: /webhook (POST/GET/PUT/DELETE)
                logs:
                  type: string
                  example: /logs
                stats:
                  type: string
                  example: /stats
    """
    return jsonify({
        'status': 'active',
        'service': 'IP Source Tracker',
        'expected_nat_ips': EXPECTED_NAT_IPS,
        'endpoints': {
            'webhook': '/webhook (POST/GET/PUT/DELETE)',
            'logs': '/logs',
            'stats': '/stats',
            'swagger': '/swagger/'
        }
    })

@app.route('/webhook', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def webhook():
    """
    Webhook Endpoint - Track Incoming Requests
    ---
    tags:
      - Tracking
    parameters:
      - name: body
        in: body
        required: false
        description: Optional request payload
        schema:
          type: object
    responses:
      200:
        description: Request successfully logged
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: VERIFIED: Request from expected NAT IP!
            your_ip:
              type: string
              example: 52.58.37.0
            is_expected_nat_ip:
              type: boolean
              example: true
            timestamp:
              type: string
              example: "2026-01-19T12:34:56.789123"
            matched_ip:
              type: string
              example: 52.58.37.0
    """
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
    """
    Get All Request Logs
    ---
    tags:
      - Monitoring
    responses:
      200:
        description: List of all logged requests (newest first)
        schema:
          type: object
          properties:
            logs:
              type: array
              items:
                type: object
                properties:
                  timestamp:
                    type: string
                    example: "2026-01-19T12:34:56.789123"
                  ip_address:
                    type: string
                    example: "52.58.37.0"
                  endpoint:
                    type: string
                    example: "/webhook"
                  method:
                    type: string
                    example: "POST"
                  is_expected_ip:
                    type: boolean
                    example: true
                  matched_nat_ip:
                    type: string
                    example: "52.58.37.0"
            count:
              type: integer
              example: 42
    """
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
    """
    Get Statistics and Comparison
    ---
    tags:
      - Monitoring
    responses:
      200:
        description: Detailed statistics and IP comparison
        schema:
          type: object
          properties:
            total_requests:
              type: integer
              example: 42
              description: Total number of requests logged
            expected_ip_requests:
              type: integer
              example: 35
              description: Requests from expected NAT IPs
            unexpected_ip_requests:
              type: integer
              example: 7
              description: Requests from unexpected IPs
            expected_nat_ips:
              type: array
              items:
                type: string
              example: ["52.58.37.0", "52.29.28.67", "18.197.50.73"]
              description: List of expected Infor MT NAT IPs
            ip_distribution:
              type: object
              example: {"52.58.37.0": 20, "52.29.28.67": 15, "192.168.1.1": 7}
              description: Request count per IP address
            comparison:
              type: array
              items:
                type: string
              example: ["✓ 52.58.37.0: 20 requests (MATCHED)", "✓ 52.29.28.67: 15 requests (MATCHED)", "✗ 18.197.50.73: 0 requests (NOT SEEN YET)"]
              description: Comparison of expected IPs vs actual requests
            unexpected_ips:
              type: object
              example: {"192.168.1.1": 7}
              description: Requests from IPs not in the expected list
    """
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

@app.route('/debug/headers')
def debug_headers():
    """
    Debug Headers - See All Request Headers
    ---
    tags:
      - Monitoring
    responses:
      200:
        description: All request headers and IP detection info
        schema:
          type: object
    """
    client_ip = get_client_ip()
    
    return jsonify({
        'detected_ip': client_ip,
        'is_expected_nat_ip': client_ip in EXPECTED_NAT_IPS,
        'all_headers': dict(request.headers),
        'ip_related_headers': {
            'X-Forwarded-For': request.headers.get('X-Forwarded-For'),
            'X-Real-IP': request.headers.get('X-Real-IP'),
            'CF-Connecting-IP': request.headers.get('CF-Connecting-IP'),
            'True-Client-IP': request.headers.get('True-Client-IP'),
            'Remote-Addr': request.remote_addr
        },
        'request_info': {
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr
        }
    })

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
