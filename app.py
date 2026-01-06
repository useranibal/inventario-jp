import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN Y LIMPIEZA DE INTERFAZ ---
st.set_page_config(
    page_title="Gestión de Inventario JP", 
    page_icon="📱", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# CSS AJUSTADO: No ocultamos el header por completo para no perder el botón del menú
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display:none !important;}
            [data-testid="stStatusWidget"] {display:none !important;}
            
            /* FORZAR VISIBILIDAD DEL BOTÓN DE APERTURA */
            [data-testid="stSidebarCollapsedControl"] {
                display: flex !important;
                visibility: visible !important;
                background-color: #d35400 !important;
                color: white !important;
                border-radius: 5px !important;
                left: 10px !important;
                top: 10px !important;
                z-index: 999999;
            }

            /* Asegurar que la barra lateral tenga color */
            [data-testid="stSidebar"] {
                background-color: #2e2e2e !important;
                min-width: 250px !important;
            }
            
            /* Botones del menú lateral */
            .stButton > button {
                width: 100%;
                border-radius: 8px;
                height: 3.5em;
                background-color: #4a4a4a;
                color: white !important;
                font-weight: bold;
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
            st.toast(f"✅ Venta registrada: {nombre}")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. BARRA LATERAL ---
# Nota: st.sidebar debe estar definido claramente
with st.sidebar:
    st.title("🛠 MENÚ")
    st.divider()

    # Carga de datos
    res_data = supabase.table("productos").select("*").execute()
    df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()

    if st.button("🚨 ALERTAS STOCK"):
        if not df_full.empty:
            bajo = df_full[df_full['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= 5]
            @st.dialog("Reponer")
            def d_a(): st.table(bajo[["nombre", "stock"]])
            d_a()

    if st.button("📊 VER VENTAS"):
        @st.dialog("Ventas")
        def d_v():
            hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
            res = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
            if res.data: st.table(pd.DataFrame(res.data).groupby("nombre_producto").sum())
            else: st.info("Sin ventas hoy.")
        d_v()

    if st.button("➕ CARGA / NUEVO"):
        @st.dialog("Mercadería")
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
                    n_nom = st.text_input("Nombre")
                    n_mar = st.text_input("Marca")
                    n_cat = st.selectbox("Categoría", ["Accesorios", "Celulares", "Otros"])
                    n_pre = st.number_input("Precio", min_value=0)
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": c, "marca": n_mar, "categoria": n_cat, "stock": 1, "precio_venta": int(n_pre)}).execute()
                        st.rerun()
        d_c()

# --- 5. CUERPO CENTRAL ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)

barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER", key="venta_scan")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog(f"Venta: {p['nombre']}")
        def d_v(item):
            st.write(f"Stock: {item['stock']} | Precio: {formatear_moneda(item['precio_venta'])}")
            if st.button("CONFIRMAR", type="primary"): realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
        d_v(p)

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