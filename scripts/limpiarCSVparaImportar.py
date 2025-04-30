import pandas as pd

def convertir_grado_decimal(coord):
    if pd.isna(coord):
        return None
    coord = coord.strip().replace("°", "")
    if "," in coord:
        lat, lon = coord.split(",")
        lat = lat.strip()
        lon = lon.strip()
    else:
        return None

    def a_decimal(valor):
        if "S" in valor or "W" in valor:
            return -float(valor[:-1].strip())
        else:
            return float(valor[:-1].strip())

    return a_decimal(lat), a_decimal(lon)

# Cargar el CSV
df = pd.read_csv("./scripts/DatosExtrasPelileo.csv", sep=";", dtype=str)

# Paso 1: Separar coordenadas en latitud y longitud en formato decimal
latitudes = []
longitudes = []

for coord in df["COORDENADAS DIVIDIR"]:
    resultado = convertir_grado_decimal(coord)
    if resultado:
        latitudes.append(resultado[0])
        longitudes.append(resultado[1])
    else:
        latitudes.append(None)
        longitudes.append(None)

df["gps_latitud"] = latitudes
df["gps_longitud"] = longitudes


def oracion_sencilla(texto):
    if pd.isna(texto) or not isinstance(texto, str):
        return texto
    return texto.strip().capitalize()
df['CIUDAD UNIR A DETALLES DIRECCION'] = df['CIUDAD UNIR A DETALLES DIRECCION'].apply(oracion_sencilla)

# Paso 2: Unir ciudad a detalles_direccion
df["detalles_direccion"] = (
    df["detalles_direccion"].fillna("") + 
    " - " + 
    df["CIUDAD UNIR A DETALLES DIRECCION"].fillna("")
)

# Paso 3: Normalizar text
def titulo_sencillo(texto):
    if pd.isna(texto) or not isinstance(texto, str):
        return texto
    return texto.strip().title()

# Aplica formato solo a ciertas columnas
df["nombre"] = df["nombre"].apply(titulo_sencillo)
df["detalles_direccion"] = df["detalles_direccion"].apply(oracion_sencilla)
df["direccion"] = df["direccion"].apply(oracion_sencilla)
df["detalles_sordo"] = df["detalles_sordo"].apply(oracion_sencilla)
df["detalles_familia"] = df["detalles_familia"].apply(oracion_sencilla)

# Guardar el resultado
df.to_csv("salida_limpia.csv", sep=";", index=False)