import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Alycell - Gestión Integral", page_icon="📱", layout="wide")
STOCK_MINIMO = 3

# TUS DATOS DE GOOGLE (Verificados de tu captura)
SHEET_ID = "1Z8o3YqmkrAHYQYeYhaxs1IwBeLlpo-b8FeGfBrqGKOk" 
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbyQ9OlxXZjwWuC-f2u2wS9m61mFmv5sFulPVc48_ClZzu49OQZkB_1mIPFQJzgCSwJL/exec"
URL_PRODUCTOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=productos"

# --- 2. CSS PARA RECUPERAR EL DISEÑO (FONDO OSCURO LATERAL) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #2e2e2e !important; }
    [data-testid="stSidebar"] .stMarkdown h3 { color: white; }
    .stButton > button { width: 100%; border-radius: 8px; background-color: #4a4a4a; color: white !important; }
    .stock-alert-bottom { background-color: #e74c3c; color: white; padding: 12px; border-radius: 10px; text-align: center; font-weight: bold; border: 2px solid white; margin-top: 10px; }
    /* Ajuste para que las tablas se vean bien en el modo oscuro/claro */
    .stTable { background-color: transparent; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES ---
@st.cache_data(ttl=5) # Actualiza datos cada 5 segundos automáticamente
def cargar_datos():
    try:
        return pd.read_csv(f"{URL_PRODUCTOS}&cache_bust={pd.Timestamp.now().timestamp()}")
    except:
        return pd.DataFrame()

def enviar_venta_a_google(datos):
    try:
        response = requests.post(URL_APPS_SCRIPT, json=datos, timeout=10)
        return response.status_code == 200
    except: return False

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

def generar_ticket_js(datos):
    fecha = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')
    es_reparacion = datos.get('tipo') == "Reparación"
    ticket_html = f"""
    <script>
    const win = window.open('', 'Ticket', 'width=450,height=700');
    win.document.write('<html><head><style>body {{ width: 75mm; font-family: Courier, monospace; padding: 10px; font-size: 12px; }} .header {{ text-align: center; }} .hr {{ border-top: 1px dashed black; margin: 10px 0; }}</style></head><body>');
    win.document.write('<div class="header"><div style="font-size: 18px; font-weight:bold;">📱 ALYCELL</div><div>Alicia Correa</div><div>+56 963539746</div></div><div class="hr"></div>');
    if ({str(es_reparacion).lower()}) {{
        win.document.write('<div>CLIENTE: {datos.get('cliente', '')}</div><div>CEL: {datos.get('celular', '')}</div>');
    }}
    win.document.write('<div class="hr"></div><div><b>{datos['nombre']}</b></div><div style="font-size: 16px; font-weight: bold;">TOTAL: {formatear_moneda(datos['precio'])}</div>');
    win.document.write('<div class="hr"></div><div style="font-size: 10px;">Garantía 30 días por fallas técnicas.</div></body></html>');
    win.document.close(); win.focus(); win.print(); win.close();
    </script>
    """
    components.html(ticket_html, height=1)

# --- 4. CARGA DE DATOS ---
df = cargar_datos()

# --- 5. SIDEBAR (MENÚ RESTAURADO) ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ ALYCELL")
    
    # Cambio: Usamos un expander en lugar de un dialog para evitar el error de Streamlit
    with st.expander("🚨 DETALLE ALERTAS", expanded=False):
        if not df.empty:
            bajo = df[df['stock'] <= STOCK_MINIMO]
            if not bajo.empty:
                st.dataframe(bajo[["nombre", "stock"]], hide_index=True)
            else:
                st.write("Todo en orden ✅")
    
    if st.button("➕ CARGA / NUEVO"):
        st.write("👉 Edita tu Google Sheet para agregar productos.")

    if not df.empty:
        bajo_c = len(df[df['stock'] <= STOCK_MINIMO])
        if bajo_c > 0:
            st.markdown(f'<div class="stock-alert-bottom">⚠️ {bajo_c} PRODUCTOS EN ALERTA</div>', unsafe_allow_html=True)

# --- 6. CUERPO CENTRAL ---
st.markdown('<h1 style="text-align:center; color:white; background:#d35400; border-radius:10px; padding:10px;">📱 ALYCELL SERVICIO TÉCNICO</h1>', unsafe_allow_html=True)

# Lógica de escaneo (Barra de búsqueda principal)
if "scan_key" not in st.session_state: st.session_state.scan_key = 0
barcode = st.text_input("🔍 ESCANEÉ CÓDIGO (CONSULTA / VENTA)", key=f"s_{st.session_state.scan_key}")

if barcode and not df.empty:
    # Búsqueda exacta y limpia
    res = df[df['codigo_barras'].astype(str).str.strip() == str(barcode).strip()]
    
    if not res.empty:
        p = res.iloc[0]
        # Usamos el diálogo SOLO para la venta
        @st.dialog("OPCIONES DE PRODUCTO")
        def d_venta(item):
            st.markdown(f"## {item['nombre']}")
            st.markdown(f"<h1 style='color: #27ae60; text-align: center;'>{formatear_moneda(item['precio_venta'])}</h1>", unsafe_allow_html=True)
            st.write(f"Stock actual: **{item['stock']}** | Marca: **{item['marca']}**")
            st.divider()
            
            opcion = st.radio("Tipo de operación:", ["Venta Rápida", "Reparación"])
            c_nom, c_cel = "", ""
            if opcion == "Reparación":
                c_nom = st.text_input("Nombre Cliente")
                c_cel = st.text_input("Celular")
            
            if st.button("✅ FINALIZAR Y DESCONTAR"):
                with st.spinner("Actualizando Google Sheets..."):
                    datos = {"nombre": item['nombre'], "precio": int(item['precio_venta']), "codigo": str(item['codigo_barras']), "cliente": c_nom, "celular": c_cel, "tipo": opcion}
                    if enviar_venta_a_google(datos):
                        st.success("¡Venta registrada!")
                        generar_ticket_js(datos)
                        st.session_state.scan_key += 1
                        st.rerun()
                    else:
                        st.error("Error de conexión con el Excel.")
        d_venta(p)
    else:
        st.warning(f"Código {barcode} no encontrado en el inventario.")

# --- 7. INVENTARIO POR PESTAÑAS (DISEÑO ORIGINAL) ---
st.divider()
bus = st.text_input("🔎 Buscar en Inventario por nombre...")

if not df.empty:
    df['Precio'] = df['precio_venta'].apply(formatear_moneda)
    if bus:
        mask = df.apply(lambda row: row.astype(str).str.contains(bus, case=False).any(), axis=1)
        st.table(df[mask][["nombre", "marca", "stock", "Precio"]])
    else:
        # Aseguramos que la columna categoria exista
        if 'categoria' in df.columns:
            categorias = sorted(df['categoria'].dropna().unique())
            tabs = st.tabs(categorias)
            for i, cat in enumerate(categorias):
                with tabs[i]:
                    st.table(df[df['categoria'] == cat][["nombre", "marca", "stock", "Precio"]])
        else:
            st.table(df[["nombre", "marca", "stock", "Precio"]])