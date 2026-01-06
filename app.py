import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN Y LIMPIEZA DE INTERFAZ ---
st.set_page_config(page_title="Gestión de Inventario JP", page_icon="📱", layout="wide")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stAppDeployButton {display:none !important;}
            #stDecoration {display:none !important;}
            [data-testid="stStatusWidget"] {display:none !important;}
            [data-testid="stSidebar"] { background-color: #3d3d3d; }
            [data-testid="stSidebar"] * { color: white; }
            .stButton > button { width: 100%; border-radius: 5px; height: 3em; background-color: #555555; color: white; }
            .stButton > button:hover { background-color: #ff4b4b; }
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

# --- 4. BARRA LATERAL (BOTONES) ---
with st.sidebar:
    st.markdown("### 🛠 Panel de Control")
    st.divider()

    # Cargar datos para alertas
    res_data = supabase.table("productos").select("*").execute()
    df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()
    
    # Botón Alertas
    bajo_stock = df_full[df_full['stock'] <= 5] if not df_full.empty else pd.DataFrame()
    if st.button(f"🚨 AVISO ({len(bajo_stock)})"):
        if not bajo_stock.empty:
            @st.dialog("Reponer Stock")
            def d_alert(): st.table(bajo_stock[["nombre", "stock"]])
            d_alert()

    # Botón Ventas
    if st.button("📈 Ver Ventas"):
        @st.dialog("Resumen de Ventas")
        def d_ventas():
            hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
            res_v = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
            if res_v.data: st.table(pd.DataFrame(res_v.data).groupby("nombre_producto").sum())
            else: st.info("Sin ventas hoy.")
        d_ventas()

    # Botón Carga
    if st.button("➕ Cargar / Nuevo"):
        @st.dialog("Ingreso de Mercadería")
        def d_carga():
            c = st.text_input("Escanear código")
            if c:
                existente = supabase.table("productos").select("*").eq("codigo_barras", c).execute()
                if existente.data:
                    it = existente.data[0]
                    st.info(f"Producto: {it['nombre']}")
                    n = st.number_input("Sumar", min_value=1)
                    if st.button("ACTUALIZAR"):
                        supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    n_nom = st.text_input("Nombre")
                    n_cat = st.selectbox("Categoría", ["Accesorios", "Celulares", "Control remoto", "Otros"])
                    n_pre = st.number_input("Precio", min_value=0)
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": c, "categoria": n_cat, "stock": 1, "precio_venta": int(n_pre)}).execute()
                        st.rerun()
        d_carga()

# --- 5. CUERPO CENTRAL ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)

barcode = st.text_input("👉 ESCANEÉ AQUÍ PARA VENDER", value="")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog(f"Venta: {p['nombre']}")
        def d_v(item):
            st.write(f"Stock: {item['stock']} | Precio: {formatear_moneda(item['precio_venta'])}")
            if st.button("CONFIRMAR VENTA", type="primary"): realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
        d_v(p)

st.divider()

# --- 6. TABLAS POR CATEGORÍA (CORREGIDO) ---
if not df_full.empty:
    # Aseguramos que existan las columnas para evitar el KeyError
    for col in ['categoria', 'marca', 'nombre', 'stock', 'precio_venta']:
        if col not in df_full.columns:
            df_full[col] = "N/A"

    df_full['categoria'] = df_full['categoria'].fillna("Otros").replace("", "Otros")
    categorias = sorted(df_full['categoria'].unique())
    tabs = st.tabs(categorias)

    for i, cat in enumerate(categorias):
        with tabs[i]:
            df_cat = df_full[df_full['categoria'] == cat]
            # Solo mostramos columnas que realmente existan o hayamos creado arriba
            cols_mostrar = ["nombre", "marca", "stock", "precio_venta"]
            st.table(df_cat[cols_mostrar].rename(columns={"nombre":"Producto", "stock":"Stock", "precio_venta":"Precio"}))