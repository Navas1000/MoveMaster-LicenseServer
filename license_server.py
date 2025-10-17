# license_server.py
# Servidor de licenças para MoveMasterIA
# Compatível com Flask 3.x
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///licenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =====================================================
# Modelo da tabela License
# =====================================================
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration_days = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    active_client = db.Column(db.String(64), nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "key": self.key,
            "created_at": self.created_at.isoformat(),
            "duration_days": self.duration_days,
            "expires_at": self.expires_at.isoformat(),
            "active_client": self.active_client,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }

# =====================================================
# Inicializa o banco de dados na primeira execução
# =====================================================
with app.app_context():
    db.create_all()

# =====================================================
# Rotas administrativas
# =====================================================
@app.route('/admin/create', methods=['POST'])
def admin_create():
    """
    Cria uma nova licença (apenas para o proprietário)
    payload: { "days": 30 }
    """
    j = request.get_json() or {}
    days = int(j.get("days", 30))
    k = str(uuid.uuid4()).replace('-', '')[:32].upper()
    now = datetime.utcnow()
    lic = License(
        key=k,
        duration_days=days,
        expires_at=now + timedelta(days=days)
    )
    db.session.add(lic)
    db.session.commit()
    return jsonify({
        "ok": True,
        "key": k,
        "expires_at": lic.expires_at.isoformat()
    })

@app.route('/admin/list', methods=['GET'])
def admin_list():
    """
    Lista todas as licenças existentes (modo debug/teste)
    """
    items = License.query.all()
    return jsonify([i.to_dict() for i in items])

# =====================================================
# Rotas de cliente (usuário final)
# =====================================================
@app.route('/activate', methods=['POST'])
def activate():
    """
    Ativa a licença no cliente
    payload: { "key": "...", "client_id": "..." }
    """
    j = request.get_json() or {}
    key = j.get("key")
    client_id = j.get("client_id")

    if not key or not client_id:
        return jsonify({"ok": False, "error": "key and client_id required"}), 400

    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"ok": False, "error": "invalid key"}), 404

    now = datetime.utcnow()
    if lic.expires_at < now:
        return jsonify({"ok": False, "error": "expired"}), 403

    # Se já está ativo por outro cliente
    if lic.active_client and lic.active_client != client_id:
        return jsonify({
            "ok": False,
            "error": "already active on another client",
            "active_client": lic.active_client
        }), 403

    lic.active_client = client_id
    lic.last_seen = now
    db.session.commit()

    return jsonify({
        "ok": True,
        "expires_at": lic.expires_at.isoformat()
    })

@app.route('/validate', methods=['POST'])
def validate():
    """
    Verifica se a key é válida e ainda não expirou.
    payload: { "key": "...", "client_id": "..." }
    """
    j = request.get_json() or {}
    key = j.get("key")
    client_id = j.get("client_id")

    if not key:
        return jsonify({"ok": False, "error": "key required"}), 400

    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"ok": False, "error": "invalid key"}), 404

    now = datetime.utcnow()
    if lic.expires_at < now:
        return jsonify({"ok": False, "error": "expired"}), 403

    ok = (lic.active_client is None) or (lic.active_client == client_id)

    return jsonify({
        "ok": ok,
        "active_client": lic.active_client,
        "expires_at": lic.expires_at.isoformat()
    })

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    """
    Mantém a licença ativa enquanto o app está aberto.
    payload: { "key": "...", "client_id": "..." }
    """
    j = request.get_json() or {}
    key = j.get("key")
    client_id = j.get("client_id")

    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"ok": False, "error": "invalid key"}), 404

    if lic.active_client != client_id:
        return jsonify({"ok": False, "error": "not active for this client"}), 403

    lic.last_seen = datetime.utcnow()
    db.session.commit()

    return jsonify({"ok": True})

@app.route('/deactivate', methods=['POST'])
def deactivate():
    """
    Desativa a licença (ex: ao fechar o programa)
    payload: { "key": "...", "client_id": "..." }
    """
    j = request.get_json() or {}
    key = j.get("key")
    client_id = j.get("client_id")

    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"ok": False, "error": "invalid key"}), 404

    if lic.active_client == client_id:
        lic.active_client = None
        lic.last_seen = None
        db.session.commit()
        return jsonify({"ok": True})

    return jsonify({"ok": False, "error": "not active for this client"}), 403

# =====================================================
# Execução do servidor
# =====================================================
if __name__ == '__main__':
    print("🔐 Servidor de Licenças ativo em http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
