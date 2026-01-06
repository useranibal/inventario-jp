import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Gestión de Inventario JP", 
    page_icon="📱", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Inicializar estado para limpiar el buscador
if "scanner_key" not in st.session_state:
    st.session_state.scanner_key = 0

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display:none !important;}
            [data-testid="stStatusWidget"] {display:none !important;}
            
            [data-testid="stSidebarCollapsedControl"] {
                background-color: #d35400 !important;
                color: white !important;
                border-radius: 5px !important;
            }
            
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
                color: white !important;
            }

            [data-testid="stSidebar"] {
                background-color: #2e2e2e !important;
            }
            
            .stButton > button {
                width: 100%;
                border-radius: 8px;
                height: 3.5em;
                background-color: #4a4a4a;
                color: white !important;
                border: 1px solid #666;
            }

            .stock-alert-bottom {
                background-color: #e74c3c;
                color: white;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
                border: 1px solid #ffffff;
                margin-top: 20px;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except:
    url = "https://bglarwxrbsltqkzmxvjk.supabase.co"
    key = "TU_KEY_AQUI"

supabase: Client = create_client(url, key)

# --- 3. FUNCIONES DE BASE DE DATOS ---
def obtener_datos():
    res = supabase.table("productos").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def realizar_venta(producto_id, stock_actual, nombre, precio):
    if stock_actual > 0:
        try:
            precio_int = int(float(precio))
            supabase.table("productos").update({"stock": stock_actual - 1}).eq("id", producto_id).execute()
            supabase.table("ventas").insert({
                "producto_id": producto_id, "nombre_producto": nombre,
                "cantidad": 1, "precio_venta": precio_int, "total": precio_int
            }).execute()
            st.toast(f"✅ Venta exitosa: {nombre}")
            st.session_state.scanner_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. FRAGMENTO DE AUTO-ACTUALIZACIÓN ---
# Este fragmento se encarga de que la tabla y la alerta lateral cambien solas
@st.fragment(run_every=10) # Se actualiza cada 10 segundos automáticamente
def seccion_dinamica():
    df_actual = obtener_datos()
    
    # 4a. Barra Lateral dentro del fragmento para la alerta
    with st.sidebar:
        st.markdown("### 🛠 MENÚ DE CONTROL")
        st.divider()

        if st.button("🚨 VER DETALLE ALERTAS"):
            if not df_actual.empty:
                bajo = df_actual[df_actual['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= 5]
                if not bajo.empty:
                    @st.dialog("Productos por Reponer")
                    def d_a(): st.table(bajo[["nombre", "stock"]])
                    d_a()

        if st.button("📊 RESUMEN VENTAS"):
            @st.dialog("Ventas")
            def d_v():
                t1, t2 = st.tabs(["Hoy", "Mes"])
                hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
                mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
                res_h = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
                res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", mes).execute()
                with t1: 
                    if res_h.data: st.table(pd.DataFrame(res_h.data).groupby("nombre_producto").sum().reset_index())
                with t2: 
                    if res_m.data: st.table(pd.DataFrame(res_m.data).groupby("nombre_producto").sum().reset_index())
            d_v()

        if st.button("➕ CARGA / NUEVO"):
            @st.dialog("Gestión")
            def d_c():
                c = st.text_input("Código")
                if c:
                    ex = supabase.table("productos").select("*").eq("codigo_barras", c).execute()
                    if ex.data:
                        it = ex.data[0]
                        n = st.number_input("Sumar", min_value=1)
                        if st.button("OK"):
                            supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                            st.rerun()
                    else:
                        n_nom = st.text_input("Nombre"); n_mar = st.text_input("Marca"); n_pre = st.number_input("Precio", min_value=0)
                        if st.button("GUARDAR"):
                            supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": c, "marca": n_mar, "stock": 1, "precio_venta": int(n_pre)}).execute()
                            st.rerun()
            d_c()

        # Alerta inferior dinámica
        st.markdown("<br><br>", unsafe_allow_html=True)
        if not df_actual.empty:
            bajo_stock = df_actual[df_actual['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= 5]
            if not bajo_stock.empty:
                st.markdown(f'<div class="stock-alert-bottom">⚠️ ATENCIÓN<br>Hay {len(bajo_stock)} productos con<br>stock mínimo</div>', unsafe_allow_html=True)

    # 4b. Tablas Centrales dentro del fragmento
    st.divider()
    if not df_actual.empty:
        df_actual['categoria'] = df_actual['categoria'].fillna("Otros").replace("", "Otros")
        categorias = sorted(df_actual['categoria'].unique())
        tabs = st.tabs(categorias)
        for i, cat in enumerate(categorias):
            with tabs[i]:
                df_cat = df_actual[df_actual['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
                st.table(df_cat.rename(columns={"nombre":"Producto", "precio_venta":"Precio"}))

# --- 5. CUERPO CENTRAL (ESCÁNER) ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)

barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER", value="", key=f"v_main_{st.session_state.scanner_key}")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog("Confirmar Venta")
        def d_confirmar(item):
            st.subheader(item['nombre'])
            st.write(f"**Precio:** {formatear_moneda(item['precio_venta'])} | **Stock:** {item['stock']}")
            if st.button("🛒 VENDER", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            if st.button("❌ CANCELAR", use_container_width=True):
                st.session_state.scanner_key += 1
                st.rerun()
        d_confirmar(p)

# Ejecutar la sección dinámica (Tablas y Alertas)
seccion_dinamica()