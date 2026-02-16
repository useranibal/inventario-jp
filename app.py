import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Alycell - Gestión Integral", page_icon="📱", layout="wide")
STOCK_MINIMO = 3

# TUS DATOS DE GOOGLE
SHEET_ID = "1Z8o3YqmkrAHYQYeYhaxs1IwBeLlpo-b8FeGfBrqGKOk" 
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbzCqf2L5AIM30JeSTvJlOBlAwCddu3Ss5WX9gwIN8ran8wZx83R8vb2xT2gQz9vwuOy/exec"
URL_PRODUCTOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=productos"

# --- 2. CSS PARA DISEÑO (SIDEBAR OSCURO / DIÁLOGOS CLAROS) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #2e2e2e !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton > button { width: 100%; border-radius: 8px; background-color: #4a4a4a; color: white !important; border: 1px solid #555; }
    .stock-alert-bottom { background-color: #e74c3c; color: white !important; padding: 12px; border-radius: 10px; text-align: center; font-weight: bold; border: 2px solid white; margin-top: 10px; }
    
    /* Forzar que el texto dentro de los diálogos sea legible (oscuro) */
    div[data-testid="stDialog"] * { color: #31333F !important; }
    div[data-testid="stDialog"] h2, div[data-testid="stDialog"] h3 { color: #1f1f1f !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES DE DATOS ---
@st.cache_data(ttl=2)
def cargar_datos():
    try:
        return pd.read_csv(f"{URL_PRODUCTOS}&cache_bust={pd.Timestamp.now().timestamp()}")
    except: return pd.DataFrame()

def ejecutar_accion_google(datos):
    try:
        response = requests.post(URL_APPS_SCRIPT, json=datos, timeout=15)
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
    win.document.write('<div class="header">📱 ALYCELL</div><div style="text-align:center;">Alicia Correa</div><div class="hr"></div>');
    if ({str(es_reparacion).lower()}) {{
        win.document.write('<div>CLIENTE: {datos.get('cliente', '')}</div><div>CEL: {datos.get('celular', '')}</div>');
    }}
    win.document.write('<div class="hr"></div><div><b>{datos['nombre']}</b></div><div style="font-size: 14px; font-weight: bold;">TOTAL: {formatear_moneda(datos['precio'])}</div>');
    win.document.write('<div class="hr"></div><div style="font-size: 10px;">Garantia 30 dias.</div></body></html>');
    win.document.close(); win.focus(); win.print(); win.close();
    </script>
    """
    components.html(ticket_html, height=1)

# --- 4. CARGA INICIAL ---
df = cargar_datos()

# --- 5. SIDEBAR (MENÚ) ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ ALYCELL")
    
    # DIALOGO DE ALERTAS (VENTANA EMERGENTE)
    @st.dialog("🚨 PRODUCTOS CON STOCK BAJO")
    def mostrar_alertas():
        bajo = df[df['stock'] <= STOCK_MINIMO]
        if not bajo.empty:
            st.write("Los siguientes productos requieren reposición:")
            st.table(bajo[["nombre", "stock"]])
        else:
            st.success("¡Todo el stock está al día! ✅")
        if st.button("Cerrar"): st.rerun()

    if st.button("🚨 DETALLE ALERTAS"):
        mostrar_alertas()

    # DIALOGO DE CARGA/NUEVO (VENTANA EMERGENTE)
    @st.dialog("➕ ADMINISTRAR INVENTARIO")
    def modal_carga():
        cod = st.text_input("Escanear o escribir código de barras")
        if cod:
            existente = df[df['codigo_barras'].astype(str).str.strip() == str(cod).strip()]
            if not existente.empty:
                prod = existente.iloc[0]
                st.markdown(f"### {prod['nombre']}")
                st.write(f"Stock actual: **{prod['stock']}**")
                cantidad = st.number_input("¿Cuánto stock desea SUMAR?", min_value=1, value=1)
                if st.button("🔄 ACTUALIZAR STOCK"):
                    datos_envio = {"accion": "actualizar_stock", "codigo": str(cod).strip(), "cantidad": int(cantidad)}
                    if ejecutar_accion_google(datos_envio):
                        st.success("Stock actualizado")
                        st.rerun()
            else:
                st.info("Producto nuevo detectado")
                n_nom = st.text_input("Nombre")
                n_mar = st.text_input("Marca")
                n_cat = st.selectbox("Categoría", ["Accesorios", "Celulares", "Pantallas", "Otros"])
                n_pre = st.number_input("Precio Venta", min_value=0)
                n_stk = st.number_input("Stock Inicial", min_value=1)
                if st.button("💾 GUARDAR NUEVO"):
                    datos_envio = {"accion": "nuevo_producto", "codigo": str(cod).strip(), "nombre": n_nom, "marca": n_mar, "categoria": n_cat, "precio": int(n_pre), "stock": int(n_stk)}
                    if ejecutar_accion_google(datos_envio):
                        st.success("Producto creado")
                        st.rerun()

    if st.button("➕ CARGA / NUEVO"):
        modal_carga()

    if not df.empty:
        bajo_c = len(df[df['stock'] <= STOCK_MINIMO])
        if bajo_c > 0:
            st.markdown(f'<div class="stock-alert-bottom">⚠️ {bajo_c} PRODUCTOS EN ALERTA</div>', unsafe_allow_html=True)

# --- 6. CUERPO CENTRAL (VENTAS) ---
st.markdown('<h1 style="text-align:center; color:white; background:#d35400; border-radius:10px; padding:10px;">📱 ALYCELL SERVICIO TÉCNICO</h1>', unsafe_allow_html=True)

if "scan_key" not in st.session_state: st.session_state.scan_key = 0
barcode = st.text_input("🔍 ESCANEÉ CÓDIGO (CONSULTA / VENTA)", key=f"s_{st.session_state.scan_key}")

if barcode and not df.empty:
    res = df[df['codigo_barras'].astype(str).str.strip() == str(barcode).strip()]
    if not res.empty:
        p = res.iloc[0]
        @st.dialog("OPCIONES DE PRODUCTO")
        def d_venta(item):
            st.markdown(f"## {item['nombre']}")
            st.markdown(f"<h1 style='color: #27ae60; text-align: center;'>{formatear_moneda(item['precio_venta'])}</h1>", unsafe_allow_html=True)
            tipo_op = st.radio("Tipo:", ["Venta Rápida", "Reparación"])
            c_nom, c_cel = "", ""
            if tipo_op == "Reparación":
                c_nom = st.text_input("Nombre Cliente")
                c_cel = st.text_input("Celular")
            if st.button("✅ FINALIZAR"):
                datos = {"accion": "venta", "nombre": item['nombre'], "precio": int(item['precio_venta']), "codigo": str(item['codigo_barras']), "cliente": c_nom, "celular": c_cel, "tipo": tipo_op}
                if ejecutar_accion_google(datos):
                    st.success("Registrado.")
                    generar_ticket_js(datos)
                    st.session_state.scan_key += 1
                    st.rerun()
        d_venta(p)
    else: st.error("No encontrado.")

# --- 7. VISTA DE TABLAS ---
st.divider()
if not df.empty:
    categorias = sorted(df['categoria'].dropna().unique())
    tabs = st.tabs(categorias)
    for i, cat in enumerate(categorias):
        with tabs[i]:
            st.table(df[df['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]])