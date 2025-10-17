# gen_keys.py
# Gera uma nova key via servidor de licenças local

import requests

SERVER = "http://127.0.0.1:5000"  # servidor local

def create(days=30):
    try:
        r = requests.post(f"{SERVER}/admin/create", json={"days": days})
        if r.status_code == 200:
            data = r.json()
            print("✅ Nova licença criada:")
            print(f"Key: {data['key']}")
            print(f"Expira em: {data['expires_at']}")
        else:
            print("❌ Erro:", r.text)
    except Exception as e:
        print("Erro de conexão com o servidor:", e)

if __name__ == "__main__":
    create(30)
