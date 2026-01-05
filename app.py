import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN Y LIMPIEZA TOTAL DE INTERFAZ ---
st.set_page_config(page_title="Gestión de Inventario JP", page_icon="📱", layout="wide")

# CSS Reforzado para ocultar botones de Streamlit y mejorar visualización
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stAppDeployButton {display:none !important;}
            #stDecoration {display:none !important;}
            [data-testid="stStatusWidget"] {display:none !important;}
            /* Ajuste para que las tablas no ocupen demasiado espacio vertical */
            .stTable {font-size: 14px;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except:
    url = "https://bglarwxrbsltqkzmxvjk.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnbGFyd3hyYnNsdHFrem14dmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2MjA0MTAsImV4cCI6MjA4MzE5NjQxMH0.hIszeUnrqVv65onnigNHvHzM-lD6XMfo4suYrJoo0l8"

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
            st.success(f"✅ Venta: {nombre}")
            st.session_state["scanner_input"] = "" 
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("❌ Sin stock")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. SECCIÓN SUPERIOR: ESCÁNER ---
st.title("📱 Sistema de Control JP")

if "scanner_input" not in st.session_state:
    st.session_state["scanner_input"] = ""

barcode = st.text_input("ESCANEÉ CÓDIGO DE BARRAS", key="barcode_field", value=st.session_state["scanner_input"])

if barcode:
    res = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res.data:
        prod = res.data[0]
        @st.dialog(f"Vender: {prod['nombre']}")
        def ventana_venta(item):
            st.write(f"**Categoría:** {item.get('categoria', 'Sin Categoría')}")
            st.write(f"**Stock:** {item['stock']} | **Precio:** {formatear_moneda(item['precio_venta'])}")
            if st.button("🛒 CONFIRMAR VENTA", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state["scanner_input"] = ""
                st.rerun()
        ventana_venta(prod)
    elif barcode != "":
        st.warning(f"⚠️ El código '{barcode}' no existe.")

st.divider()

# --- 5. CUERPO PRINCIPAL: STOCK POR CATEGORÍAS (IZQ) | VENTAS (DER) ---
col_inv, col_ventas = st.columns([2.2, 0.8])

with col_inv:
    st.subheader("📦 Inventario por Categorías")
    try:
        # Traemos todos los productos
        res_inv = supabase.table("productos").select("nombre, marca, categoria, stock, precio_venta").execute()
        if res_inv.data:
            df_full = pd.DataFrame(res_inv.data)
            
            # Si la columna categoría no existe o está vacía, llenamos con "Otros"
            if 'categoria' not in df_full.columns:
                df_full['categoria'] = "Otros"
            df_full['categoria'] = df_full['categoria'].fillna("Otros").replace("", "Otros")

            # Obtenemos las categorías únicas para crear las pestañas
            categorias = sorted(df_full['categoria'].unique())
            tabs_cat = st.tabs(categorias)

            # Llenamos cada pestaña con su tabla correspondiente
            for i, cat in enumerate(categorias):
                with tabs_cat[i]:
                    df_cat = df_full[df_full['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
                    df_cat.columns = ["Producto", "Marca", "Stock", "Precio"]
                    st.table(df_cat.style.format({"Precio": lambda x: formatear_moneda(x)}))
        else:
            st.info("El inventario está vacío.")
    except Exception as e:
        st.error(f"Error al cargar inventario: {e}")

with col_ventas:
    st.subheader("📈 Ventas")
    t_hoy, t_mes = st.tabs(["Hoy", "Mes"])
    with t_hoy:
        fecha_hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
        res_v = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", fecha_hoy).execute()
        if res_v.data:
            df_v = pd.DataFrame(res_v.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
            df_v.columns = ["Producto", "Cant."]
            st.table(df_v)
        else: st.info("Sin ventas hoy.")
    with t_mes:
        fecha_mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
        res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", fecha_mes).execute()
        if res_m.data:
            df_m = pd.DataFrame(res_m.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
            df_m.columns = ["Producto", "Total"]
            st.table(df_m)
        else: st.info("Sin registros.")

# --- 6. SECCIÓN INFERIOR: CARGA Y NUEVOS ---
st.divider()
with st.expander("➕ Cargar Stock / Registrar Producto Nuevo"):
    c_cod = st.text_input("Escanear código para CARGA", key="carga_field")
    if c_cod:
        res_c = supabase.table("productos").select("*").eq("codigo_barras", c_cod).execute()
        if res_c.data:
            it = res_c.data[0]
            with st.form("sumar_stock"):
                st.info(f"Producto: {it['nombre']} ({it.get('categoria', 'Otros')})")
                n_st = st.number_input("Cantidad a sumar", min_value=1, step=1)
                if st.form_submit_button("✅ ACTUALIZAR STOCK"):
                    supabase.table("productos").update({"stock": it['stock'] + n_st}).eq("id", it['id']).execute()
                    st.success("¡Stock actualizado!")
                    st.rerun()
        else:
            with st.form("nuevo_producto"):
                st.warning("🆕 REGISTRO DE PRODUCTO NUEVO")
                col1, col2 = st.columns(2)
                with col1:
                    n_nom = st.text_input("Nombre del Producto *")
                    n_mar = st.text_input("Marca")
                    n_cat = st.selectbox("Categoría", ["Celulares", "Accesorios", "Control Remoto", "Cargadores", "Otros"])
                with col2:
                    n_pre = st.number_input("Precio de Venta", min_value=0, step=500)
                    n_stk = st.number_input("Stock Inicial", min_value=1, step=1)
                
                if st.form_submit_button("🚀 REGISTRAR E INGRESAR"):
                    if n_nom:
                        supabase.table("productos").insert({
                            "nombre": n_nom, "codigo_barras": c_cod, "marca": n_mar,
                            "categoria": n_cat, "stock": n_stk, "precio_venta": int(n_pre)
                        }).execute()
                        st.success("Producto creado exitosamente.")
                        st.rerun()
                    else:
                        st.error("El nombre es obligatorio.")