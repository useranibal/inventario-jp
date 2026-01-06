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

# CSS REFORZADO PARA COLORES Y BOTÓN >>
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display:none !important;}
            [data-testid="stStatusWidget"] {display:none !important;}
            
            /* FORZAR COLOR DEL BOTÓN >> Y HEADER */
            [data-testid="stSidebarCollapsedControl"] {
                background-color: #d35400 !important;
                color: white !important;
                border-radius: 5px !important;
            }
            
            /* FORZAR TEXTO BLANCO EN EL MENÚ LATERAL */
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
                color: white !important;
            }

            [data-testid="stSidebar"] {
                background-color: #2e2e2e !important;
            }
            
            /* Estilo botones laterales */
            .stButton > button {
                width: 100%;
                border-radius: 8px;
                height: 3.5em;
                background-color: #4a4a4a;
                color: white !important;
                border: 1px solid #666;
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

# --- 3. FUNCIONES ---
def realizar_venta(producto_id, stock_actual, nombre, precio):
    if stock_actual > 0:
        try:
            precio_int = int(float(precio))
            supabase.table("productos").update({"stock": stock_actual - 1}).eq("id", producto_id).execute()
            supabase.table("ventas").insert({
                "producto_id": producto_id, "nombre_producto": nombre,
                "cantidad": 1, "precio_venta": precio_int, "total": precio_int
            }).execute()
            st.toast(f"✅ Venta: {nombre}")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. BARRA LATERAL (CON VENTAS HOY Y MES) ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ DE CONTROL")
    st.divider()

    res_data = supabase.table("productos").select("*").execute()
    df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()

    if st.button("🚨 ALERTAS STOCK"):
        if not df_full.empty:
            bajo = df_full[df_full['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= 5]
            @st.dialog("Productos por Reponer")
            def d_a(): st.table(bajo[["nombre", "stock"]])
            d_a()

    if st.button("📊 VER VENTAS"):
        @st.dialog("Resumen de Ventas")
        def d_v():
            # USAMOS TABS PARA MOSTRAR AMBAS
            tab_hoy, tab_mes = st.tabs(["Ventas de Hoy", "Ventas del Mes"])
            
            with tab_hoy:
                hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
                res_h = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
                if res_h.data:
                    df_h = pd.DataFrame(res_h.data).groupby("nombre_producto").sum().reset_index()
                    st.table(df_h)
                else: st.info("No hay ventas hoy.")
                
            with tab_mes:
                inicio_mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
                res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", inicio_mes).execute()
                if res_m.data:
                    df_m = pd.DataFrame(res_m.data).groupby("nombre_producto").sum().reset_index()
                    st.table(df_m)
                else: st.info("No hay ventas registradas este mes.")
        d_v()

    if st.button("➕ CARGA / NUEVO"):
        @st.dialog("Ingreso Mercadería")
        def d_c():
            c = st.text_input("Código")
            if c:
                ex = supabase.table("productos").select("*").eq("codigo_barras", c).execute()
                if ex.data:
                    it = ex.data[0]
                    n = st.number_input("Sumar stock", min_value=1)
                    if st.button("ACTUALIZAR"):
                        supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    st.warning("Producto Nuevo")
                    n_nom = st.text_input("Nombre")
                    n_mar = st.text_input("Marca")
                    n_cat = st.selectbox("Categoría", ["Accesorios", "Celulares", "Control remoto", "Cargadores", "Otros"])
                    n_pre = st.number_input("Precio", min_value=0)
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": c, "marca": n_mar, "categoria": n_cat, "stock": 1, "precio_venta": int(n_pre)}).execute()
                        st.rerun()
        d_c()

# --- 5. CUERPO CENTRAL ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)

barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER", key="venta_main")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog(f"Venta: {p['nombre']}")
        def d_venta_modal(item):
            st.write(f"**Stock:** {item['stock']} | **Precio:** {formatear_moneda(item['precio_venta'])}")
            if st.button("CONFIRMAR VENTA", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
        d_venta_modal(p)

st.divider()

# --- 6. TABLAS ---
if not df_full.empty:
    df_full['categoria'] = df_full['categoria'].fillna("Otros").replace("", "Otros")
    categorias = sorted(df_full['categoria'].unique())
    tabs = st.tabs(categorias)
    for i, cat in enumerate(categorias):
        with tabs[i]:
            df_cat = df_full[df_full['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
            st.table(df_cat.rename(columns={"nombre":"Producto", "precio_venta":"Precio"}))