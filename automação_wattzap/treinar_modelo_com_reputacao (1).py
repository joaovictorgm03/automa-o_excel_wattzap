
import ssl
import socket
import requests
import pandas as pd
import re
import joblib
from urllib.parse import urlparse
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Caminho do dataset CSV
CSV_PATH = "Dataset_Balanceado_Final.csv"

# Função para extrair features completas de reputação e estrutura
def extrair_features_completas(url):
    features = {}
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path

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
        features["ends_with_br"] = int(domain.endswith(".br")) if domain else 0
        features["has_ip"] = int(bool(re.search(r'http[s]?://(\d{1,3}\.){3}\d{1,3}', url)))

        # DNS resolve
        try:
            socket.gethostbyname(domain)
            features["dns_resolves"] = 1
        except:
            features["dns_resolves"] = 0

        # SSL
        try:
            context = ssl.create_default_context()
            with context.wrap_socket(socket.socket(), server_hostname=domain) as s:
                s.settimeout(3)
                s.connect((domain, 443))
                s.getpeercert()
            features["ssl_valid"] = 1
        except:
            features["ssl_valid"] = 0

        # Redirects
        try:
            resp = requests.get(url, timeout=5)
            features["num_redirects"] = len(resp.history)
        except:
            features["num_redirects"] = -1

    except Exception as e:
        # Se qualquer erro crítico, retorna todas as features como 0
        features = {k: 0 for k in [
            "url_length", "num_dots", "num_hyphens", "num_slashes", "has_at_symbol", "has_https",
            "has_login", "has_verify", "has_secure", "has_bank", "has_boleto", "has_nfe",
            "has_cartao", "ends_with_br", "has_ip", "dns_resolves", "ssl_valid", "num_redirects"
        ]}

    return features

# Carregar dataset
df = pd.read_csv(CSV_PATH)
assert "url" in df.columns, "Erro: coluna 'url' não encontrada no CSV."
urls = df["url"].tolist()

# Extrair features com paralelismo
print("🔄 Extraindo features das URLs...")
features_list = []
with ThreadPoolExecutor(max_workers=10) as executor:
    future_to_url = {executor.submit(extrair_features_completas, url): url for url in urls}
    for future in tqdm(as_completed(future_to_url), total=len(future_to_url)):
        try:
            features = future.result()
        except Exception as e:
            print(f"Erro em uma URL: {e}")
            features = {k: 0 for k in [
                "url_length", "num_dots", "num_hyphens", "num_slashes", "has_at_symbol", "has_https",
                "has_login", "has_verify", "has_secure", "has_bank", "has_boleto", "has_nfe",
                "has_cartao", "ends_with_br", "has_ip", "dns_resolves", "ssl_valid", "num_redirects"
            ]}
        features_list.append(features)

# Converter para DataFrame
X = pd.DataFrame(features_list)
y = df["label"]

# Treinar modelo
X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.3, random_state=42)
model = RandomForestClassifier(random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

# Avaliação
y_pred = model.predict(X_test)
print("\n🔍 Relatório de Classificação:")
print(classification_report(y_test, y_pred))

# Salvar modelo
joblib.dump(model, "modelo_com_reputacao.pkl")
print("\n✅ Modelo salvo como 'modelo_com_reputacao.pkl'")
