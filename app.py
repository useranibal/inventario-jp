import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN Y LIMPIEZA DE INTERFAZ ---
st.set_page_config(page_title="Gestión de Inventario JP", page_icon="📱", layout="wide")

# CSS para ocultar menús y el botón rojo de Streamlit
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
            st.write(f"**Marca:** {item.get('marca', 'N/A')} | **Categoría:** {item.get('categoria', 'Otros')}")
            st.write(f"**Stock:** {item['stock']} | **Precio:** {formatear_moneda(item['precio_venta'])}")
            if st.button("🛒 CONFIRMAR VENTA", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            if st.button("❌ Cerrar", use_container_width=True):
                st.session_state["scanner_input"] = ""
                st.rerun()
        ventana_venta(prod)

st.divider()

# --- 5. CUERPO PRINCIPAL: STOCK (IZQ) | VENTAS (DER) ---
col_inv, col_ventas = st.columns([2.2, 0.8])

with col_inv:
    st.subheader("📦 Inventario por Categorías")
    try:
        res_inv = supabase.table("productos").select("*").execute()
        if res_inv.data:
            df_full = pd.DataFrame(res_inv.data)
            
            # --- ALERTA DE STOCK BAJO (Recuperada) ---
            bajo_stock = df_full[df_full['stock'] <= 5]
            if not bajo_stock.empty:
                if st.button(f"🚨 AVISO: {len(bajo_stock)} productos con stock bajo", type="secondary"):
                    @st.dialog("Productos para Reponer")
                    def alerta_stock(lista):
                        st.table(lista[["nombre", "stock", "categoria"]])
                    alerta_stock(bajo_stock)
            
            # Organización por pestañas
            df_full['categoria'] = df_full['categoria'].fillna("Otros").replace("", "Otros")
            categorias = sorted(df_full['categoria'].unique())
            tabs = st.tabs(categorias)

            for i, cat in enumerate(categorias):
                with tabs[i]:
                    df_cat = df_full[df_full['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
                    df_cat.columns = ["Producto", "Marca", "Stock", "Precio"]
                    st.table(df_cat.style.format({"Precio": lambda x: formatear_moneda(x)}))
    except:
        st.error("Error al cargar datos.")

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

# --- 6. SECCIÓN INFERIOR: CARGA ---
st.divider()
with st.expander("➕ Cargar Stock / Registrar Nuevo"):
    c_cod = st.text_input("Escanear para CARGA", key="carga_field")
    if c_cod:
        res_c = supabase.table("productos").select("*").eq("codigo_barras", c_cod).execute()
        if res_c.data:
            it = res_c.data[0]
            with st.form("upd"):
                st.info(f"Producto: {it['nombre']}")
                n_st = st.number_input("Sumar cantidad", min_value=1)
                if st.form_submit_button("Actualizar Stock"):
                    supabase.table("productos").update({"stock": it['stock']+n_st}).eq("id", it['id']).execute()
                    st.rerun()
        else:
            with st.form("new"):
                st.warning("Nuevo Producto")
                col_a, col_b = st.columns(2)
                with col_a:
                    n_nom = st.text_input("Nombre *")
                    n_mar = st.text_input("Marca")
                    n_cat = st.selectbox("Categoría", ["Accesorios", "Celulares", "Control remoto", "Cargadores", "Otros"])
                with col_b:
                    n_pre = st.number_input("Precio", min_value=0)
                    n_stk = st.number_input("Stock inicial", min_value=1)
                if st.form_submit_button("Guardar"):
                    if n_nom:
                        supabase.table("productos").insert({
                            "nombre": n_nom, "codigo_barras": c_cod, "marca": n_mar,
                            "categoria": n_cat, "stock": n_stk, "precio_venta": int(n_pre)
                        }).execute()
                        st.rerun()