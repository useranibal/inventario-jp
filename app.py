import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS (OCULTAR MENÚS) ---
st.set_page_config(page_title="Gestión de Inventario JP", page_icon="📱", layout="wide")

# CSS para ocultar el botón "Hosted with Streamlit", el pie de página y el menú superior
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stAppDeployButton {display:none;}
            #stDecoration {display:none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 2. CONEXIÓN SEGURA A BASE DE DATOS ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except:
    # Valores de respaldo por si fallan los secrets (solo para pruebas)
    url = "https://bglarwxrbsltqkzmxvjk.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnbGFyd3hyYnNsdHFrem14dmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2MjA0MTAsImV4cCI6MjA4MzE5NjQxMH0.hIszeUnrqVv65onnigNHvHzM-lD6XMfo4suYrJoo0l8"

supabase: Client = create_client(url, key)

# --- 3. FUNCIONES DE LÓGICA ---
def realizar_venta(producto_id, stock_actual, nombre, precio):
    if stock_actual > 0:
        try:
            # Convertimos a int(float()) para evitar errores de sintaxis en Supabase
            precio_int = int(float(precio))
            supabase.table("productos").update({"stock": stock_actual - 1}).eq("id", producto_id).execute()
            supabase.table("ventas").insert({
                "producto_id": producto_id, "nombre_producto": nombre,
                "cantidad": 1, "precio_venta": precio_int, "total": precio_int
            }).execute()
            st.success(f"✅ Venta registrada: {nombre}")
            st.session_state["scanner_input"] = "" 
            st.rerun()
        except Exception as e:
            st.error(f"Error al registrar venta: {e}")
    else:
        st.error("❌ Error: No hay stock disponible.")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. INTERFAZ DE ESCÁNER (VENTA) ---
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
            st.write(f"**Marca:** {item.get('marca', 'N/A')}")
            st.write(f"**Stock actual:** {item['stock']}")
            st.write(f"**Precio:** {formatear_moneda(item['precio_venta'])}")
            st.divider()
            if st.button("🛒 CONFIRMAR VENTA", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            
            if st.button("❌ Cerrar y Limpiar", use_container_width=True):
                st.session_state["scanner_input"] = ""
                st.rerun()
        ventana_venta(prod)
    else:
        st.warning(f"⚠️ El código '{barcode}' no existe en el inventario.")

# --- 5. RESUMEN DE VENTAS ---
st.subheader("📈 Resumen de Salidas (ventas)")
t_hoy, t_mes = st.tabs(["Ventas de Hoy", "Ventas del Mes"])

with t_hoy:
    hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
    res_v = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
    if res_v.data:
        df_v = pd.DataFrame(res_v.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
        df_v.columns = ["Producto", "Unidades Vendidas"]
        st.table(df_v)
    else: st.info("No se han registrado ventas hoy.")

with t_mes:
    mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
    res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", mes).execute()
    if res_m.data:
        df_m = pd.DataFrame(res_m.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
        df_m.columns = ["Producto", "Total Mes"]
        st.table(df_m)
    else: st.info("Sin registros este mes.")

# --- 6. CARGA DE MERCADERÍA ---
with st.expander("➕ Cargar Stock / Registrar Nuevo Producto"):
    c_cod = st.text_input("Escanear código para CARGA", key="carga_field")
    if c_cod:
        res_c = supabase.table("productos").select("*").eq("codigo_barras", c_cod).execute()
        if res_c.data:
            it = res_c.data[0]
            with st.form("upd_stock"):
                st.info(f"Producto: {it['nombre']}")
                n_st = st.number_input("Cantidad a sumar", min_value=1, step=1)
                if st.form_submit_button("✅ ACTUALIZAR STOCK"):
                    supabase.table("productos").update({"stock": it['stock'] + n_st}).eq("id", it['id']).execute()
                    st.success("Stock actualizado.")
                    st.rerun()
        else:
            with st.form("new_prod"):
                st.warning("✨ Producto nuevo detectado")
                n_nom = st.text_input("Nombre del Producto")
                n_mar = st.text_input("Marca")
                n_pre = st.number_input("Precio de Venta", min_value=0, step=500)
                n_stk = st.number_input("Stock Inicial", min_value=1)
                if st.form_submit_button("🚀 REGISTRAR PRODUCTO"):
                    if n_nom:
                        supabase.table("productos").insert({
                            "nombre": n_nom, "codigo_barras": c_cod, "marca": n_mar,
                            "stock": n_stk, "precio_venta": int(n_pre)
                        }).execute()
                        st.success("Producto creado con éxito.")
                        st.rerun()

# --- 7. ALERTAS Y TABLA DE INVENTARIO ---
st.divider()
st.subheader("⚠️ Alertas de Reposición")
try:
    res_inv = supabase.table("productos").select("nombre, marca, stock, precio_venta").execute()
    if res_inv.data:
        bajo_stock = [p for p in res_inv.data if p['stock'] <= 5]
        if bajo_stock:
            if st.button(f"🚨 Hay {len(bajo_stock)} productos con stock bajo.", type="secondary"):
                @st.dialog("Productos para Reponer")
                def mostrar_bajo(lista):
                    st.table(pd.DataFrame(lista)[["nombre", "stock"]])
                mostrar_bajo(bajo_stock)
        else:
            st.success("Niveles de stock saludables ✅")

        st.subheader("📦 Inventario Actual")
        df_inv = pd.DataFrame(res_inv.data)
        df_inv.columns = ["Producto", "Marca", "Stock", "Precio"]
        st.table(df_inv.style.format({"Precio": lambda x: formatear_moneda(x)}))
except Exception:
    st.error("Error al cargar la tabla de inventario.")