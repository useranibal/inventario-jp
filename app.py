import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN Y LIMPIEZA TOTAL DE INTERFAZ ---
st.set_page_config(page_title="Gestión de Inventario JP", page_icon="📱", layout="wide")

# CSS Avanzado para ocultar TODO: botón rojo, marca de agua, menú y cabecera
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stAppDeployButton {display:none !important;}
            #stDecoration {display:none !important;}
            [data-testid="stStatusWidget"] {display:none !important;}
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
        @st.dialog(f"Producto: {prod['nombre']}")
        def ventana_venta(item):
            st.write(f"**Stock:** {item['stock']} | **Precio:** {formatear_moneda(item['precio_venta'])}")
            if st.button("🛒 CONFIRMAR VENTA", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            if st.button("❌ Cerrar", use_container_width=True):
                st.session_state["scanner_input"] = ""
                st.rerun()
        ventana_venta(prod)
    elif barcode != "":
        st.warning(f"⚠️ El código '{barcode}' no existe.")

st.divider()

# --- 5. CUERPO PRINCIPAL: COLUMNAS (STOCK IZQ | VENTAS DER) ---
# Definimos pesos: 2 para inventario (ancho) y 1 para ventas (más angosto)
col_inv, col_ventas = st.columns([2, 1])

with col_inv:
    st.subheader("📦 Inventario Actual")
    try:
        res_inv = supabase.table("productos").select("nombre, marca, stock, precio_venta").execute()
        if res_inv.data:
            # Botón de Alerta de Stock (Solo aparece si hay stock bajo)
            bajo_stock = [p for p in res_inv.data if p['stock'] <= 5]
            if bajo_stock:
                if st.button(f"⚠️ {len(bajo_stock)} productos con Stock Bajo", type="secondary"):
                    @st.dialog("🚨 Reposición Necesaria")
                    def alerta(lista):
                        st.table(pd.DataFrame(lista)[["nombre", "stock"]])
                    alerta(bajo_stock)
            
            # Tabla de inventario
            df_inv = pd.DataFrame(res_inv.data)
            df_inv.columns = ["Producto", "Marca", "Stock", "Precio"]
            st.table(df_inv.style.format({"Precio": lambda x: formatear_moneda(x)}))
    except:
        st.error("Error al conectar con el inventario.")

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
        else:
            st.info("Hoy no hay ventas.")

    with t_mes:
        fecha_mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
        res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", fecha_mes).execute()
        if res_m.data:
            df_m = pd.DataFrame(res_m.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
            df_m.columns = ["Producto", "Total"]
            st.table(df_m)
        else:
            st.info("Sin registros este mes.")

# --- 6. SECCIÓN INFERIOR: CARGA ---
st.divider()
with st.expander("➕ Cargar Stock / Nuevo Producto"):
    c_cod = st.text_input("Escanear para CARGA", key="carga_field")
    if c_cod:
        res_c = supabase.table("productos").select("*").eq("codigo_barras", c_cod).execute()
        if res_c.data:
            it = res_c.data[0]
            with st.form("upd"):
                st.info(f"Producto: {it['nombre']}")
                n_st = st.number_input("Cantidad a sumar", min_value=1)
                if st.form_submit_button("✅ ACTUALIZAR"):
                    supabase.table("productos").update({"stock": it['stock'] + n_st}).eq("id", it['id']).execute()
                    st.success("¡Stock sumado!")
                    st.rerun()
        else:
            with st.form("new"):
                st.warning("Nuevo producto")
                n_nom = st.text_input("Nombre")
                n_pre = st.number_input("Precio", min_value=0)
                n_stk = st.number_input("Stock inicial", min_value=1)
                if st.form_submit_button("🚀 REGISTRAR"):
                    supabase.table("productos").insert({
                        "nombre": n_nom, "codigo_barras": c_cod, "stock": n_stk, "precio_venta": int(n_pre)
                    }).execute()
                    st.rerun()