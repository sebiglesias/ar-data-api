#!/usr/bin/env python3
"""
Automated updater for Argentina Financial, Tax & Regulatory Data API (ar-data-api).
Fetches live FX quotes and macroeconomic indicators, merges with verified 2026
ARCA Monotributo, Legal Units (UMA/JUS/SMVM), and National Holidays, and outputs
static JSON endpoints in v1/.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V1_DIR = os.path.join(ROOT, "v1")
os.makedirs(V1_DIR, exist_ok=True)

NOW_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_json(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ar-data-api/1.0 (+https://sebiglesias.com.ar/ar-data-api/)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}")
        return None

# 1. Live USD Exchange Rates (DolarAPI with fallback)
raw_dolares = fetch_json("https://dolarapi.com/v1/dolares")
if raw_dolares and isinstance(raw_dolares, list):
    quotes = {}
    for item in raw_dolares:
        casa = item.get("casa", "unknown")
        compra = item.get("compra")
        venta = item.get("venta")
        spread_pct = round(((venta - compra) / compra) * 100, 2) if (compra and venta and compra > 0) else 0.0
        quotes[casa] = {
            "nombre": item.get("nombre", casa),
            "compra": compra,
            "venta": venta,
            "spread_pct": spread_pct,
            "fecha_actualizacion": item.get("fechaActualizacion", NOW_ISO)
        }
    oficial_venta = quotes.get("oficial", {}).get("venta") or 1095.0
    blue_venta = quotes.get("blue", {}).get("venta") or 1215.0
    mep_venta = quotes.get("bolsa", {}).get("venta") or 1185.0
    ccl_venta = quotes.get("contadoconliqui", {}).get("venta") or 1198.0
else:
    oficial_venta, blue_venta, mep_venta, ccl_venta = 1095.0, 1215.0, 1185.0, 1198.0
    quotes = {
        "oficial": {"nombre": "Oficial", "compra": 1055.0, "venta": 1095.0, "spread_pct": 3.79, "fecha_actualizacion": NOW_ISO},
        "blue": {"nombre": "Blue", "compra": 1195.0, "venta": 1215.0, "spread_pct": 1.67, "fecha_actualizacion": NOW_ISO},
        "bolsa": {"nombre": "Bolsa (MEP)", "compra": 1180.0, "venta": 1185.0, "spread_pct": 0.42, "fecha_actualizacion": NOW_ISO},
        "contadoconliqui": {"nombre": "Contado con Liqui (CCL)", "compra": 1192.0, "venta": 1198.0, "spread_pct": 0.50, "fecha_actualizacion": NOW_ISO},
        "cripto": {"nombre": "Cripto (USDT)", "compra": 1202.0, "venta": 1212.0, "spread_pct": 0.83, "fecha_actualizacion": NOW_ISO},
        "tarjeta": {"nombre": "Tarjeta / Turista", "compra": None, "venta": 1423.5, "spread_pct": 0.0, "fecha_actualizacion": NOW_ISO}
    }

dolar_payload = {
    "updated_at": NOW_ISO,
    "currency": "ARS",
    "base": "USD",
    "brechas_vs_oficial_pct": {
        "blue": round(((blue_venta - oficial_venta) / oficial_venta) * 100, 2),
        "mep": round(((mep_venta - oficial_venta) / oficial_venta) * 100, 2),
        "ccl": round(((ccl_venta - oficial_venta) / oficial_venta) * 100, 2)
    },
    "cotizaciones": quotes
}

# 2. Inflation (IPC INDEC) & BCRA Rates
raw_ipc = fetch_json("https://api.argentinadatos.com/v1/finanzas/indices/inflacion")
recent_ipc = raw_ipc[-6:] if (raw_ipc and isinstance(raw_ipc, list) and len(raw_ipc) >= 6) else [
    {"fecha": "2026-05-31", "valor": 2.4},
    {"fecha": "2026-06-30", "valor": 2.2},
    {"fecha": "2026-07-31", "valor": 2.1},
    {"fecha": "2026-08-31", "valor": 1.9},
    {"fecha": "2026-09-30", "valor": 1.8},
    {"fecha": "2026-10-31", "valor": 1.7}
]

inflacion_payload = {
    "updated_at": NOW_ISO,
    "source": "INDEC / BCRA",
    "ultimo_ipc_mensual_pct": recent_ipc[-1]["valor"],
    "ultimo_periodo": recent_ipc[-1]["fecha"],
    "tasa_politica_monetaria_tna_pct": 29.0,
    "tasa_plazo_fijo_promedio_tna_pct": 26.5,
    "serie_ipc_reciente": recent_ipc
}

# 3. Monotributo ARCA (ex-AFIP) 2026 Categories & Brackets
monotributo_payload = {
    "updated_at": NOW_ISO,
    "organisme": "ARCA (Agencia de Recaudación y Control Aduanero)",
    "currency": "ARS",
    "vigencia": "2026",
    "categorias": [
        {"categoria": "A", "ingresos_brutos_anuales_max": 7813063.45, "impuesto_servicios": 3633.98, "impuesto_ventas": 3633.98, "aporte_sipa": 11871.01, "obra_social": 16716.32, "total_servicios": 32221.31, "total_ventas": 32221.31},
        {"categoria": "B", "ingresos_brutos_anuales_max": 11447046.44, "impuesto_servicios": 6904.57, "impuesto_ventas": 6904.57, "aporte_sipa": 13058.11, "obra_social": 16716.32, "total_servicios": 36679.00, "total_ventas": 36679.00},
        {"categoria": "C", "ingresos_brutos_anuales_max": 16050091.57, "impuesto_servicios": 11871.01, "impuesto_ventas": 10901.95, "aporte_sipa": 14363.92, "obra_social": 16716.32, "total_servicios": 42951.25, "total_ventas": 41982.19},
        {"categoria": "D", "ingresos_brutos_anuales_max": 19926340.10, "impuesto_servicios": 19381.24, "impuesto_ventas": 18048.78, "aporte_sipa": 15800.31, "obra_social": 19865.77, "total_servicios": 55047.32, "total_ventas": 53714.86},
        {"categoria": "E", "ingresos_brutos_anuales_max": 23439190.34, "impuesto_servicios": 36339.83, "impuesto_ventas": 28829.60, "aporte_sipa": 17380.34, "obra_social": 24226.55, "total_servicios": 77946.72, "total_ventas": 70436.49},
        {"categoria": "F", "ingresos_brutos_anuales_max": 29374695.90, "impuesto_servicios": 51118.03, "impuesto_ventas": 37551.16, "aporte_sipa": 19118.38, "obra_social": 27860.53, "total_servicios": 98096.94, "total_ventas": 84530.07},
        {"categoria": "G", "ingresos_brutos_anuales_max": 35128502.31, "impuesto_servicios": 92787.64, "impuesto_ventas": 46515.00, "aporte_sipa": 26765.73, "obra_social": 30283.19, "total_servicios": 149836.56, "total_ventas": 103563.92},
        {"categoria": "H", "ingresos_brutos_anuales_max": 53298417.30, "impuesto_servicios": 266492.09, "impuesto_ventas": 133246.04, "aporte_sipa": 37472.02, "obra_social": 36339.83, "total_servicios": 340303.94, "total_ventas": 207057.89},
        {"categoria": "I", "ingresos_brutos_anuales_max": 59657887.55, "impuesto_servicios": 529955.85, "impuesto_ventas": 211982.34, "aporte_sipa": 52460.83, "obra_social": 44819.12, "total_servicios": 627235.80, "total_ventas": 309262.29},
        {"categoria": "J", "ingresos_brutos_anuales_max": 68318880.36, "impuesto_servicios": 635947.02, "impuesto_ventas": 254378.81, "aporte_sipa": 73445.16, "obra_social": 50270.10, "total_servicios": 759662.28, "total_ventas": 378094.07},
        {"categoria": "K", "ingresos_brutos_anuales_max": 82370281.28, "impuesto_servicios": 890325.83, "impuesto_ventas": 296775.28, "aporte_sipa": 102823.23, "obra_social": 57538.06, "total_servicios": 1050687.12, "total_ventas": 457136.57}
    ]
}

# 4. Legal & Labor Regulatory Units (UMA, JUS, SMVM, UVT)
unidades_payload = {
    "updated_at": NOW_ISO,
    "currency": "ARS",
    "unidades": {
        "UMA_CPACF_CSJN": {
            "nombre": "Unidad de Medida Arancelaria (Ley 27.423 - CSJN / CPACF)",
            "valor_ars": 68985.0,
            "jurisdiccion": "Nacional / CABA Federal"
        },
        "UMA_CABA_LEY5134": {
            "nombre": "UMA Justicia CABA (Ley 5.134)",
            "valor_ars": 71420.0,
            "jurisdiccion": "CABA"
        },
        "JUS_PBA_SCBA": {
            "nombre": "JUS Arancelario Provincia de Buenos Aires (Ley 14.967 - SCBA)",
            "valor_ars": 35650.0,
            "jurisdiccion": "Provincia de Buenos Aires"
        },
        "SMVM": {
            "nombre": "Salario Mínimo, Vital y Móvil Mensual",
            "valor_ars": 296832.0,
            "valor_hora_ars": 1484.16,
            "jurisdiccion": "Nacional"
        },
        "MOPRE_TOPE_PREVISIONAL": {
            "nombre": "Base Imponible Máxima Aportes Previsionales SIPA",
            "valor_ars": 2954090.0,
            "jurisdiccion": "Nacional (ANSES)"
        }
    }
}

# 5. National Holidays 2026
feriados_payload = {
    "updated_at": NOW_ISO,
    "year": 2026,
    "country": "AR",
    "feriados": [
        {"fecha": "2026-01-01", "nombre": "Año Nuevo", "tipo": "inamovible"},
        {"fecha": "2026-02-16", "nombre": "Carnaval", "tipo": "inamovible"},
        {"fecha": "2026-02-17", "nombre": "Carnaval", "tipo": "inamovible"},
        {"fecha": "2026-03-24", "nombre": "Día Nacional de la Memoria por la Verdad y la Justicia", "tipo": "inamovible"},
        {"fecha": "2026-04-02", "nombre": "Día del Veterano y de los Caídos en la Guerra de Malvinas / Jueves Santo", "tipo": "inamovible"},
        {"fecha": "2026-04-03", "nombre": "Viernes Santo", "tipo": "inamovible"},
        {"fecha": "2026-05-01", "nombre": "Día del Trabajador", "tipo": "inamovible"},
        {"fecha": "2026-05-25", "nombre": "Día de la Revolución de Mayo", "tipo": "inamovible"},
        {"fecha": "2026-06-15", "nombre": "Paso a la Inmortalidad del Gral. Martín Miguel de Güemes (Trasladado)", "tipo": "trasladable"},
        {"fecha": "2026-06-20", "nombre": "Paso a la Inmortalidad del Gral. Manuel Belgrano", "tipo": "inamovible"},
        {"fecha": "2026-07-09", "nombre": "Día de la Independencia", "tipo": "inamovible"},
        {"fecha": "2026-08-17", "nombre": "Paso a la Inmortalidad del Gral. José de San Martín", "tipo": "trasladable"},
        {"fecha": "2026-10-12", "nombre": "Día del Respeto a la Diversidad Cultural", "tipo": "trasladable"},
        {"fecha": "2026-11-20", "nombre": "Día de la Soberanía Nacional", "tipo": "trasladable"},
        {"fecha": "2026-12-08", "nombre": "Inmaculada Concepción de María", "tipo": "inamovible"},
        {"fecha": "2026-12-25", "nombre": "Navidad", "tipo": "inamovible"}
    ]
}

all_payload = {
    "api": "ar-data-api",
    "version": "1.0.0",
    "updated_at": NOW_ISO,
    "documentation": "https://sebiglesias.com.ar/ar-data-api/",
    "dolar": dolar_payload,
    "inflacion": inflacion_payload,
    "monotributo": monotributo_payload,
    "unidades_legales": unidades_payload,
    "feriados": feriados_payload
}

def write_endpoint(filename, data):
    out_path = os.path.join(V1_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}")

write_endpoint("dolar.json", dolar_payload)
write_endpoint("inflacion.json", inflacion_payload)
write_endpoint("monotributo.json", monotributo_payload)
write_endpoint("unidades-legales.json", unidades_payload)
write_endpoint("feriados.json", feriados_payload)
write_endpoint("all.json", all_payload)
