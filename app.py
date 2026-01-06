import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Gestión de Inventario JP", 
    page_icon="📱", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Inicializar estado
if "scanner_key" not in st.session_state:
    st.session_state.scanner_key = 0

# CSS REFORZADO
st.markdown("""
    <style>
    #MainMenu, footer, .stAppDeployButton, [data-testid="stStatusWidget"] {visibility: hidden;}
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #d35400 !important; color: white !important; border-radius: 5px !important;
    }
    [data-testid="stSidebar"] { background-color: #2e2e2e !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton > button {
        width: 100%; border-radius: 8px; height: 3.5em;
        background-color: #4a4a4a; color: white !important; border: 1px solid #666;
    }
    .stock-alert-bottom {
        background-color: #e74c3c; color: white; padding: 15px;
        border-radius: 10px; text-align: center; font-weight: bold;
        border: 1px solid #ffffff; margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except:
    url = "https://bglarwxrbsltqkzmxvjk.supabase.co"
    key = "TU_KEY_AQUI"

supabase: Client = create_client(url, key)

# --- 3. FUNCIONES ---
def realizar_venta(producto_id, stock_actual, nombre, precio):
    if stock_actual > 0:
        try:
            supabase.table("productos").update({"stock": stock_actual - 1}).eq("id", producto_id).execute()
            supabase.table("ventas").insert({
                "producto_id": producto_id, "nombre_producto": nombre,
                "cantidad": 1, "precio_venta": int(float(precio)), "total": int(float(precio))
            }).execute()
            st.toast(f"✅ Venta: {nombre}")
            st.session_state.scanner_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. LÓGICA DE DATOS (SIN RENDERIZADO MIXTO) ---
res_data = supabase.table("productos").select("*").execute()
df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()

# --- 5. BARRA LATERAL (ESTÁTICA PARA EVITAR ERRORES) ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ DE CONTROL")
    st.divider()

    if st.button("🚨 VER DETALLE ALERTAS"):
        if not df_full.empty:
            bajo = df_full[df_full['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= 5]
            if not bajo.empty:
                @st.dialog("Stock Bajo")
                def d_a(): st.table(bajo[["nombre", "stock"]])
                d_a()
            else: st.toast("Stock al día")

    if st.button("📊 RESUMEN VENTAS"):
        @st.dialog("Ventas")
        def d_v():
            t1, t2 = st.tabs(["Hoy", "Mes"])
            hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
            mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
            with t1:
                rh = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
                if rh.data: st.table(pd.DataFrame(rh.data).groupby("nombre_producto").sum().reset_index())
            with t2:
                rm = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", mes).execute()
                if rm.data: st.table(pd.DataFrame(rm.data).groupby("nombre_producto").sum().reset_index())
        d_v()

    if st.button("➕ CARGA / NUEVO"):
        @st.dialog("Inventario")
        def d_c():
            c = st.text_input("Código")
            if c:
                ex = supabase.table("productos").select("*").eq("codigo_barras", c).execute()
                if ex.data:
                    it = ex.data[0]
                    n = st.number_input("Sumar stock", min_value=1)
                    if st.button("OK"):
                        supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    n_nom = st.text_input("Nombre"); n_mar = st.text_input("Marca"); n_pre = st.number_input("Precio", min_value=0)
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": c, "marca": n_mar, "stock": 1, "precio_venta": int(n_pre)}).execute()
                        st.rerun()
        d_c()

    # Alerta en la parte inferior
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    if not df_full.empty:
        bajo_stock = df_full[df_full['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= 5]
        if not bajo_stock.empty:
            st.markdown(f'<div class="stock-alert-bottom">⚠️ ATENCIÓN<br>Hay {len(bajo_stock)} productos con<br>stock mínimo</div>', unsafe_allow_html=True)

# --- 6. CUERPO CENTRAL (REFRESCO AUTOMÁTICO DE TABLAS) ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)

# Input de venta
barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER", value="", key=f"v_main_{st.session_state.scanner_key}")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog("Confirmar Venta")
        def d_conf(item):
            st.subheader(item['nombre'])
            st.write(f"**Precio:** {formatear_moneda(item['precio_venta'])} | **Stock:** {item['stock']}")
            if st.button("🛒 VENDER", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            if st.button("❌ CANCELAR", use_container_width=True):
                st.session_state.scanner_key += 1
                st.rerun()
        d_conf(p)

# Fragmento solo para las tablas (se actualiza cada 10 seg sin romper el menú)
@st.fragment(run_every=10)
def mostrar_tablas():
    st.divider()
    # Volvemos a pedir datos frescos para la tabla
    data_fresca = supabase.table("productos").select("*").execute()
    df_fresco = pd.DataFrame(data_fresca.data) if data_fresca.data else pd.DataFrame()
    
    if not df_fresco.empty:
        df_fresco['categoria'] = df_fresco['categoria'].fillna("Otros").replace("", "Otros")
        cats = sorted(df_fresco['categoria'].unique())
        tabs = st.tabs(cats)
        for i, cat in enumerate(cats):
            with tabs[i]:
                df_cat = df_fresco[df_fresco['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
                st.table(df_cat.rename(columns={"nombre":"Producto", "precio_venta":"Precio"}))

mostrar_tablas()