import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN Y LIMPIEZA DE INTERFAZ ---
st.set_page_config(page_title="Gestión de Inventario JP", page_icon="📱", layout="wide")

# CSS para ocultar menús, botón de deploy y estilizar la barra lateral
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stAppDeployButton {display:none !important;}
            #stDecoration {display:none !important;}
            [data-testid="stStatusWidget"] {display:none !important;}
            
            /* Color de fondo para la barra lateral (Sidebar) */
            [data-testid="stSidebar"] {
                background-color: #3d3d3d;
            }
            [data-testid="stSidebar"] * {
                color: white;
            }
            /* Estilo para los botones del menú */
            .stButton > button {
                width: 100%;
                border-radius: 5px;
                height: 3em;
                background-color: #555555;
                color: white;
                border: 1px solid #777777;
            }
            .stButton > button:hover {
                background-color: #ff4b4b;
                border-color: #ff4b4b;
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

# --- 3. FUNCIONES DE VENTA ---
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
            st.session_state["scanner_input"] = "" 
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("❌ Sin stock")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. DISEÑO DE BARRA LATERAL (MENÚ DE ACCIONES) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1170/1170577.png", width=80) # Icono decorativo
    st.title("Panel de Control")
    st.divider()

    # Botón 1: Alertas
    res_alert = supabase.table("productos").select("nombre, stock, categoria").execute()
    df_alert = pd.DataFrame(res_alert.data) if res_alert.data else pd.DataFrame()
    bajo_stock = df_alert[df_alert['stock'] <= 5] if not df_alert.empty else pd.DataFrame()
    
    label_alerta = f"🚨 AVISO ({len(bajo_stock)})" if not bajo_stock.empty else "✅ Stock OK"
    if st.button(label_alerta):
        if not bajo_stock.empty:
            @st.dialog("Productos para Reponer")
            def modal_alerta(lista):
                st.table(lista)
            modal_alerta(bajo_stock)
        else:
            st.success("Todos los productos tienen stock suficiente.")

    # Botón 2: Ver Ventas
    if st.button("📈 Ver Ventas (Hoy/Mes)"):
        @st.dialog("Resumen de Ventas")
        def modal_ventas():
            t1, t2 = st.tabs(["Hoy", "Mes"])
            with t1:
                hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
                v_h = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
                if v_h.data: st.table(pd.DataFrame(v_h.data).groupby("nombre_producto").sum())
                else: st.info("No hay ventas hoy.")
            with t2:
                mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
                v_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", mes).execute()
                if v_m.data: st.table(pd.DataFrame(v_m.data).groupby("nombre_producto").sum())
                else: st.info("Sin registros este mes.")
        modal_ventas()

    # Botón 3: Cargar Stock / Nuevo
    if st.button("➕ Cargar / Nuevo Producto"):
        @st.dialog("Ingreso de Mercadería")
        def modal_carga():
            c_cod = st.text_input("Escanear código")
            if c_cod:
                res_c = supabase.table("productos").select("*").eq("codigo_barras", c_cod).execute()
                if res_c.data:
                    it = res_c.data[0]
                    st.info(f"Producto: {it['nombre']}")
                    n_st = st.number_input("Cantidad a sumar", min_value=1)
                    if st.button("ACTUALIZAR"):
                        supabase.table("productos").update({"stock": it['stock']+n_st}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    st.warning("Producto Nuevo")
                    n_nom = st.text_input("Nombre")
                    n_cat = st.selectbox("Categoría", ["Accesorios", "Celulares", "Control remoto", "Cargadores", "Otros"])
                    n_pre = st.number_input("Precio", min_value=0)
                    n_stk = st.number_input("Stock Inicial", min_value=1)
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": c_cod, "categoria": n_cat, "stock": n_stk, "precio_venta": int(n_pre)}).execute()
                        st.rerun()
        modal_carga()

# --- 5. CUERPO CENTRAL: ESCÁNER Y TABLAS ---
# Título con estilo (Fondo Naranja como en tu imagen)
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 20px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)
st.write("")

if "scanner_input" not in st.session_state:
    st.session_state["scanner_input"] = ""

# Buscador Principal (Llamativo)
barcode = st.text_input("👉 ESCANEÉ AQUÍ PARA VENDER", key="barcode_field", value=st.session_state["scanner_input"])

if barcode:
    res = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res.data:
        prod = res.data[0]
        @st.dialog(f"Venta: {prod['nombre']}")
        def ventana_venta(item):
            st.write(f"**Stock actual:** {item['stock']}")
            st.write(f"**Precio:** {formatear_moneda(item['precio_venta'])}")
            if st.button("🛒 CONFIRMAR VENTA", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
        ventana_venta(prod)

st.divider()

# --- 6. INVENTARIO POR PESTAÑAS (CENTRAL) ---
st.subheader("📦 Inventario General")
if not df_alert.empty:
    df_full = df_alert
    df_full['categoria'] = df_full['categoria'].fillna("Otros").replace("", "Otros")
    categorias = sorted(df_full['categoria'].unique())
    tabs = st.tabs(categorias)

    for i, cat in enumerate(categorias):
        with tabs[i]:
            df_cat = df_full[df_full['categoria'] == cat][["nombre", "stock", "precio_venta"]]
            df_cat.columns = ["Producto", "Stock", "Precio"]
            st.table(df_cat.style.format({"Precio": lambda x: formatear_moneda(x)}))