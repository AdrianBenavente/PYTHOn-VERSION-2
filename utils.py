import requests
import re
import time
from config import Config

def clean_address(address):
    """Limpia la dirección eliminando coordenadas y caracteres no deseados."""
    # 1. Elimina coordenadas dentro del texto (-12.123456, -77.654321)
    address = re.sub(r'-?\d+\.\d+\s*,\s*-?\d+\.\d+', '', address)
    
    # 2. Sustituye caracteres especiales por espacios
    address = re.sub(r'[^a-zA-Z0-9\s,.]', ' ', address)
    
    # 3. Elimina espacios extra
    address = re.sub(r'\s+', ' ', address).strip()

    return address

def get_coordinates(address, retries=3, delay=1):
    """Obtiene coordenadas de Google Maps. Si ya están en el texto, las usa directamente."""
    
    if not address:
        return None, None

    # 1. Intenta extraer coordenadas directamente del texto
    match = re.search(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)', address)
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        print(f"✔ Usando coordenadas extraídas del texto: {lat}, {lon}")
        return lat, lon  

    # 2. Limpiar la dirección antes de buscar
    address = clean_address(address)
    
    # 3. Limitar la búsqueda a Callao, Perú
    address = f"{address}, Callao, Perú"

    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": Config.GOOGLE_MAPS_API_KEY,
        "components": "country:PE|administrative_area:Callao"  # Restringe a Callao
    }

    for attempt in range(retries):
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if data["status"] == "OK":
                location = data["results"][0]["geometry"]["location"]
                return location["lat"], location["lng"]
            else:
                print(f"⚠ Error geocodificando '{address}': {data['status']}")

        print(f"🔄 Reintentando ({attempt + 1}/{retries}) en {delay} segundos...")
        time.sleep(delay)

    return None, None
