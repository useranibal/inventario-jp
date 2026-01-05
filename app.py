import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN DE PÁGINA Y CONEXIÓN ---
st.set_page_config(page_title="Gestión de Inventario JP", page_icon="📱", layout="wide")

##url = "https://bglarwxrbsltqkzmxvjk.supabase.co"
##key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJnbGFyd3hyYnNsdHFrem14dmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2MjA0MTAsImV4cCI6MjA4MzE5NjQxMH0.hIszeUnrqVv65onnigNHvHzM-lD6XMfo4suYrJoo0l8"
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. FUNCIONES DE LÓGICA ---
def realizar_venta(producto_id, stock_actual, nombre, precio):
    if stock_actual > 0:
        try:
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
            st.error(f"Error técnico: {e}")
    else:
        st.error("❌ Error: No hay stock disponible.")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 3. INTERFAZ DE ESCÁNER (VENTA) ---
st.title("📱 Sistema de Control e Inventario")

if "scanner_input" not in st.session_state:
    st.session_state["scanner_input"] = ""

barcode = st.text_input("ESCANEÉ CÓDIGO DE BARRAS PARA VENTA", key="barcode_field", value=st.session_state["scanner_input"])

if barcode:
    res = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res.data:
        prod = res.data[0]
        @st.dialog(f"Producto: {prod['nombre']}")
        def ventana_venta(item):
            st.write(f"**Stock:** {item['stock']} | **Precio:** {formatear_moneda(item['precio_venta'])}")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💰 Consultar Precio", use_container_width=True):
                    st.info(f"Precio: {formatear_moneda(item['precio_venta'])}")
            with col_b:
                if st.button("🛒 CONFIRMAR VENTA", type="primary", use_container_width=True):
                    realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            
            if st.button("❌ Cerrar y Limpiar", use_container_width=True):
                st.session_state["scanner_input"] = ""
                st.rerun()
        ventana_venta(prod)
    else:
        st.warning(f"⚠️ El código '{barcode}' no existe en el inventario.")

st.divider()

# --- 4. DISTRIBUCIÓN DE COLUMNAS ---
col_inv, col_ventas = st.columns([2, 0.8])

with col_inv:
    st.subheader("📦 Inventario Actual")
    try:
        res_inv = supabase.table("productos").select("nombre, marca, stock, precio_venta").execute()
        if res_inv.data:
            # --- NUEVA LÓGICA DE ALERTA CON BOTÓN ---
            bajo_stock = [p for p in res_inv.data if p['stock'] <= 5]
            
            if bajo_stock:
                col_alerta, col_espacio = st.columns([1, 1])
                with col_alerta:
                    # Botón que abre el diálogo de stock crítico
                    if st.button(f"⚠️ Ver {len(bajo_stock)} productos con Stock Bajo", type="secondary", use_container_width=True):
                        @st.dialog("🚨 Productos que requieren reposición")
                        def mostrar_stock_bajo(lista):
                            df_bajo = pd.DataFrame(lista)[["nombre", "stock"]]
                            df_bajo.columns = ["Producto", "Unidades"]
                            st.table(df_bajo)
                            if st.button("Entendido"):
                                st.rerun()
                        mostrar_stock_bajo(bajo_stock)
            else:
                st.success("✅ Niveles de stock saludables.")
            # ----------------------------------------

            df_inv = pd.DataFrame(res_inv.data)
            df_inv.columns = ["Producto", "Marca", "Stock", "Precio"]
            st.table(df_inv.style.format({"Precio": lambda x: formatear_moneda(x)}))
    except Exception as e:
        st.error("Error al cargar inventario.")

with col_ventas:
    st.subheader("📈 Ventas")
    t_hoy, t_mes = st.tabs(["Hoy", "Mes"])
    with t_hoy:
        hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
        res_v = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
        if res_v.data:
            df_v = pd.DataFrame(res_v.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
            st.table(df_v)
        else: st.info("Sin ventas.")
    with t_mes:
        mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
        res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", mes).execute()
        if res_m.data:
            df_m = pd.DataFrame(res_m.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
            st.table(df_m)
        else: st.info("Sin registros.")

# --- 5. CARGA DE MERCADERÍA ---
st.divider()
with st.expander("➕ Cargar Stock / Registrar Nuevo Producto"):
    c_cod = st.text_input("Escanear código para CARGA", key="carga_field")
    
    if c_cod:
        res_c = supabase.table("productos").select("*").eq("codigo_barras", c_cod).execute()
        
        if res_c.data:
            it = res_c.data[0]
            with st.form("form_update_stock"):
                st.info(f"Producto: **{it['nombre']}**")
                n_st = st.number_input("Cantidad a sumar", min_value=1, step=1)
                n_pr = st.number_input("Confirmar Precio", value=int(float(it['precio_venta'])), step=1000)
                if st.form_submit_button("✅ ACTUALIZAR STOCK"):
                    supabase.table("productos").update({
                        "stock": it['stock'] + n_st,
                        "precio_venta": int(n_pr)
                    }).eq("id", it['id']).execute()
                    st.success("¡Stock actualizado!")
                    st.rerun()
        else:
            st.warning("✨ Código nuevo detectado.")
            with st.form("form_nuevo_registro"):
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    nuevo_nom = st.text_input("Nombre")
                    nuevo_mar = st.text_input("Marca")
                with col_n2:
                    nuevo_cat = st.selectbox("Categoría", ["Celulares", "Accesorios", "Cargadores", "Otros"])
                    nuevo_pre = st.number_input("Precio ($)", min_value=0, step=500)
                
                nuevo_stk = st.number_input("Stock Inicial", min_value=1, step=1)
                
                if st.form_submit_button("🚀 REGISTRAR"):
                    if nuevo_nom:
                        supabase.table("productos").insert({
                            "nombre": nuevo_nom, "codigo_barras": c_cod, "marca": nuevo_mar,
                            "categoria": nuevo_cat, "stock": nuevo_stk, "precio_venta": int(nuevo_pre)
                        }).execute()
                        st.success(f"Producto {nuevo_nom} creado.")
                        st.rerun()