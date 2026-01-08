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

if "scanner_key" not in st.session_state:
    st.session_state.scanner_key = 0
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# CSS
st.markdown("""
    <style>
    #MainMenu, footer, .stAppDeployButton, [data-testid="stStatusWidget"] {visibility: hidden;}
    [data-testid="stSidebarCollapsedControl"] { background-color: #d35400 !important; color: white !important; }
    [data-testid="stSidebar"] { background-color: #2e2e2e !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton > button { width: 100%; border-radius: 8px; background-color: #4a4a4a; color: white !important; }
    .stock-alert-bottom { background-color: #e74c3c; color: white; padding: 15px; border-radius: 10px; text-align: center; margin-top: 20px; border: 1px solid white; }
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
                "cantidad": 1, "precio_venta": int(precio), "total": int(precio)
            }).execute()
            st.toast(f"✅ Venta: {nombre}")
            st.session_state.scanner_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ DE CONTROL")
    st.divider()

    # Botones de Reportes
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

    if st.button("➕ CARGAR / NUEVO PRODUCTO"):
        @st.dialog("Ingreso de Mercadería")
        def d_carga_completa():
            cod = st.text_input("Código de Barras")
            if cod:
                ex = supabase.table("productos").select("*").eq("codigo_barras", cod).execute()
                if ex.data:
                    it = ex.data[0]
                    st.success(f"Producto detectado: {it['nombre']}")
                    cant = st.number_input("Cantidad a sumar al stock", min_value=1, value=1)
                    if st.button("ACTUALIZAR STOCK"):
                        supabase.table("productos").update({"stock": it['stock'] + cant}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    st.warning("🆕 REGISTRAR PRODUCTO NUEVO")
                    c_nom = st.text_input("Nombre del Producto")
                    c_mar = st.text_input("Marca")
                    c_cat = st.text_input("Categoría (Escríbela manualmente)")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        c_costo = st.number_input("Precio Costo", min_value=0, step=100)
                        c_stk = st.number_input("Stock Inicial", min_value=1, value=1)
                    with col_b:
                        c_venta = st.number_input("Precio Venta", min_value=0, step=100)
                    
                    if st.button("GUARDAR TODO"):
                        if c_nom and c_cat:
                            supabase.table("productos").insert({
                                "nombre": c_nom, "codigo_barras": cod, "marca": c_mar,
                                "categoria": c_cat, "precio_costo": int(c_costo),
                                "precio_venta": int(c_venta), "stock": int(c_stk)
                            }).execute()
                            st.rerun()
                        else: st.error("Nombre y Categoría son obligatorios")
        d_carga_completa()

    # Alerta Inferior
    st.markdown("<br><br>", unsafe_allow_html=True)
    res_alert = supabase.table("productos").select("stock").execute()
    if res_alert.data:
        df_a = pd.DataFrame(res_alert.data)
        bajo = df_a[df_a['stock'] <= 5]
        if not bajo.empty:
            st.markdown(f'<div class="stock-alert-bottom">⚠️ ATENCIÓN<br>Hay {len(bajo)} productos con<br>stock mínimo</div>', unsafe_allow_html=True)

# --- 5. CUERPO CENTRAL ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)

# SECCIÓN DE VENTA
barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER", value="", key=f"v_main_{st.session_state.scanner_key}")
if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog("Confirmar Venta")
        def d_v(item):
            st.write(f"**{item['nombre']}** ({item.get('marca','')})")
            st.write(f"Precio: {formatear_moneda(item['precio_venta'])} | Stock: {item['stock']}")
            if st.button("🛒 CONFIRMAR VENTA", type="primary"): realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            if st.button("CANCELAR"): 
                st.session_state.scanner_key += 1
                st.rerun()
        d_v(p)

st.divider()

# --- 6. BUSCADOR Y TABLAS (FRAGMENTADO) ---
@st.fragment(run_every=15)
def seccion_inventario():
    st.subheader("📦 Consulta de Productos")
    
    # Fila de búsqueda
    col_bus, col_limp = st.columns([4, 1])
    with col_bus:
        busqueda = st.text_input("Escribe nombre, marca o categoría para buscar...", value=st.session_state.search_query, placeholder="Ej: Samsung")
    with col_limp:
        st.write(" ") # Espacio
        if st.button("🧹 Limpiar"):
            st.session_state.search_query = ""
            st.rerun()

    # Cargar datos frescos
    data_res = supabase.table("productos").select("*").execute()
    df = pd.DataFrame(data_res.data) if data_res.data else pd.DataFrame()

    if not df.empty:
        # Aplicar filtro si hay búsqueda
        if busqueda:
            st.session_state.search_query = busqueda
            mask = df.apply(lambda row: busqueda.lower() in row.astype(str).str.lower().values, axis=1)
            df_filtered = df[mask]
        else:
            df_filtered = df

        if busqueda:
            st.write(f"Resultados para: **{busqueda}**")
            st.table(df_filtered[["nombre", "marca", "categoria", "stock", "precio_venta"]].rename(columns={"nombre":"Producto","precio_venta":"Precio"}))
        else:
            # Vista por Categorías (Pestañas)
            df_filtered['categoria'] = df_filtered['categoria'].fillna("Otros").replace("", "Otros")
            cats = sorted(df_filtered['categoria'].unique())
            tabs = st.tabs(cats)
            for i, cat in enumerate(cats):
                with tabs[i]:
                    df_cat = df_filtered[df_filtered['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
                    st.table(df_cat.rename(columns={"nombre":"Producto", "precio_venta":"Precio"}))

seccion_inventario()