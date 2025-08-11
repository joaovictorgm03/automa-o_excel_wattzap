
import ssl
import socket
import requests
import pandas as pd
import re
import joblib
from urllib.parse import urlparse

# Caminho do modelo treinado
MODEL_PATH = "modelo_com_reputacao.pkl"

# Função para extrair features da URL
def extrair_features_completas(url):
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    features = {}

    features["url_length"] = len(url)
    features["num_dots"] = url.count('.')
    features["num_hyphens"] = url.count('-')
    features["num_slashes"] = url.count('/')
    features["has_at_symbol"] = int('@' in url)
    features["has_https"] = int(parsed.scheme == "https")
    features["has_login"] = int("login" in url.lower())
    features["has_verify"] = int("verify" in url.lower())
    features["has_secure"] = int("secure" in url.lower())
    features["has_bank"] = int("bank" in url.lower())
    features["has_boleto"] = int("boleto" in url.lower())
    features["has_nfe"] = int("nfe" in url.lower())
    features["has_cartao"] = int("cartao" in url.lower())
    features["ends_with_br"] = int(domain.endswith(".br"))
    features["has_ip"] = int(bool(re.match(r'http[s]?://(\d{1,3}\.){3}\d{1,3}', url)))

    try:
        socket.gethostbyname(domain)
        features["dns_resolves"] = 1
    except:
        features["dns_resolves"] = 0

    def check_ssl(domain):
        try:
            context = ssl.create_default_context()
            with context.wrap_socket(socket.socket(), server_hostname=domain) as s:
                s.settimeout(3)
                s.connect((domain, 443))
                s.getpeercert()
            return 1
        except:
            return 0

    features["ssl_valid"] = check_ssl(domain)

    try:
        resp = requests.get(url, timeout=5)
        features["num_redirects"] = len(resp.history)
    except:
        features["num_redirects"] = -1

    return features

# Carregar o modelo treinado
modelo = joblib.load(MODEL_PATH)

# Entrada do usuário
url = input("Digite a URL para análise: ").strip()
features = extrair_features_completas(url)
X = pd.DataFrame([features])

# Previsão
predicao = modelo.predict(X)[0]
proba = modelo.predict_proba(X)[0][int(predicao)]

print(f"\n🔍 Resultado:")
print(f"URL: {url}")
print(f"Classificação: {'⚠️ Suspeita' if predicao == 1 else '✅ Segura'}")
print(f"Confiança: {proba * 100:.2f}%")
