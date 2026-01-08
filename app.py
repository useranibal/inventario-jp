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

# Constante de Stock Mínimo (Ajustada a 3)
STOCK_MINIMO = 3

if "scanner_key" not in st.session_state:
    st.session_state.scanner_key = 0
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# CSS REFORZADO PARA OCULTAR MARCAS DE AGUA Y ESTILO CHILE
st.markdown("""
    <style>
    /* Ocultar Menú, Marca de agua y botón de despliegue de Streamlit */
    #MainMenu, footer, .stAppDeployButton, [data-testid="stStatusWidget"], .viewerBadge_container__1QS1n {
        visibility: hidden; display: none !important;
    }
    
    /* Estilo del contenedor de la barra lateral */
    [data-testid="stSidebarCollapsedControl"] { background-color: #d35400 !important; color: white !important; }
    [data-testid="stSidebar"] { background-color: #2e2e2e !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* Botones profesionales */
    .stButton > button { width: 100%; border-radius: 8px; background-color: #4a4a4a; color: white !important; height: 3.5em; border: 1px solid #666; }
    .stButton > button:hover { border-color: #d35400; color: #d35400 !important; }

    /* Caja de alerta roja inferior */
    .stock-alert-bottom { 
        background-color: #e74c3c; color: white; padding: 15px; 
        border-radius: 10px; text-align: center; margin-top: 20px; 
        border: 2px solid white; font-weight: bold;
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

# --- 3. FUNCIONES DE LIMPIEZA Y LÓGICA ---
def formatear_moneda(valor):
    """Convierte 10000.00 en $ 10.000 (Formato Peso Chileno)"""
    try:
        # Convertimos a float y luego a int para eliminar decimales de la DB
        v = int(float(valor))
        return f"$ {v:,}".replace(",", ".")
    except:
        return f"$ {valor}"

def realizar_venta(producto_id, stock_actual, nombre, precio):
    if stock_actual > 0:
        try:
            # Registrar venta y descontar stock
            supabase.table("productos").update({"stock": stock_actual - 1}).eq("id", producto_id).execute()
            supabase.table("ventas").insert({
                "producto_id": producto_id, "nombre_producto": nombre,
                "cantidad": 1, "precio_venta": int(float(precio)), "total": int(float(precio))
            }).execute()
            st.toast(f"✅ Venta exitosa: {nombre}")
            st.session_state.scanner_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ DE CONTROL")
    st.divider()

    # Carga de datos fresca
    res_data = supabase.table("productos").select("*").execute()
    df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()

    if st.button("🚨 VER DETALLE ALERTAS"):
        if not df_full.empty:
            bajo = df_full[df_full['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= STOCK_MINIMO]
            if not bajo.empty:
                @st.dialog("Productos Críticos")
                def d_a(): 
                    df_v = bajo[["nombre", "marca", "stock", "precio_venta"]].copy()
                    df_v["precio_venta"] = df_v["precio_venta"].apply(formatear_moneda)
                    st.table(df_v.rename(columns={"precio_venta": "Precio"}))
                d_a()
            else: st.toast("Inventario saludable (Todos > 3)")

    if st.button("📊 RESUMEN VENTAS"):
        @st.dialog("Reporte de Ventas")
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
        @st.dialog("Gestión de Stock")
        def d_c():
            cod = st.text_input("Código de Barras")
            if cod:
                ex = supabase.table("productos").select("*").eq("codigo_barras", cod).execute()
                if ex.data:
                    it = ex.data[0]
                    st.info(f"Detectado: {it['nombre']}")
                    n = st.number_input("Sumar cantidad", min_value=1, value=1)
                    if st.button("GUARDAR"):
                        supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    st.warning("🆕 REGISTRAR NUEVO")
                    n_nom = st.text_input("Nombre"); n_mar = st.text_input("Marca"); n_cat = st.text_input("Categoría")
                    c1, c2 = st.columns(2)
                    with c1: n_cos = st.number_input("Costo", min_value=0); n_stk = st.number_input("Stock inicial", min_value=1)
                    with c2: n_ven = st.number_input("Venta", min_value=0)
                    if st.button("REGISTRAR PRODUCTO"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": cod, "marca": n_mar, "categoria": n_cat, "precio_costo": int(n_cos), "precio_venta": int(n_ven), "stock": int(n_stk)}).execute()
                        st.rerun()
        d_c()

    # ALERTA ROJA INFERIOR (Stock <= 3)
    st.markdown("<br><br>", unsafe_allow_html=True)
    if not df_full.empty:
        bajo_count = len(df_full[df_full['stock'] <= STOCK_MINIMO])
        if bajo_count > 0:
            st.markdown(f'<div class="stock-alert-bottom">⚠️ ATENCIÓN<br>Tienes {bajo_count} productos con<br>stock mínimo (≤ {STOCK_MINIMO})</div>', unsafe_allow_html=True)

# --- 5. SISTEMA DE VENTAS ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)

barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER", value="", key=f"v_main_{st.session_state.scanner_key}")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog("Confirmar Operación")
        def d_conf(item):
            st.subheader(item['nombre'])
            st.write(f"**Marca:** {item.get('marca', 'N/A')}")
            st.write(f"**Precio:** {formatear_moneda(item['precio_venta'])} | **Stock:** {item['stock']}")
            st.divider()
            if st.button("🛒 VENDER PRODUCTO", type="primary"):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            if st.button("❌ CANCELAR"):
                st.session_state.scanner_key += 1
                st.rerun()
        d_conf(p)

st.divider()

# --- 6. BUSCADOR FLEXIBLE Y TABLAS ---
@st.fragment(run_every=20)
def seccion_inventario():
    c_bus, c_lim = st.columns([4, 1])
    with c_bus:
        bus = st.text_input("🔍 Buscar por Nombre, Marca o Categoría...", value=st.session_state.search_query)
    with c_lim:
        st.write(" ")
        if st.button("🧹 Limpiar"):
            st.session_state.search_query = ""
            st.rerun()

    df_fresh = pd.DataFrame(supabase.table("productos").select("*").execute().data)
    
    if not df_fresh.empty:
        # Formatear columna de precio para la vista del usuario
        df_fresh['Precio'] = df_fresh['precio_venta'].apply(formatear_moneda)
        
        if bus:
            st.session_state.search_query = bus
            # Búsqueda que ignora mayúsculas y busca partes del nombre
            mask = df_fresh.apply(lambda row: row.astype(str).str.contains(bus, case=False, na=False)).any(axis=1)
            df_res = df_fresh[mask]
            st.table(df_res[["nombre", "marca", "stock", "Precio"]].rename(columns={"nombre":"Producto"}))
        else:
            df_fresh['categoria'] = df_fresh['categoria'].fillna("Otros").replace("", "Otros")
            cats = sorted(df_fresh['categoria'].unique())
            tabs = st.tabs(cats)
            for i, cat in enumerate(cats):
                with tabs[i]:
                    df_c = df_fresh[df_fresh['categoria'] == cat][["nombre", "marca", "stock", "Precio"]]
                    st.table(df_c.rename(columns={"nombre":"Producto"}))

seccion_inventario()