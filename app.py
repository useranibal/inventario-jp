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
            
            /* Barra lateral gris oscuro */
            [data-testid="stSidebar"] {
                background-color: #2e2e2e;
            }
            [data-testid="stSidebar"] * {
                color: white;
            }
            /* Botones del menú lateral */
            .stButton > button {
                width: 100%;
                border-radius: 8px;
                height: 3.5em;
                background-color: #4a4a4a;
                color: white;
                border: none;
                font-weight: bold;
                margin-bottom: 10px;
            }
            .stButton > button:hover {
                background-color: #d35400;
                color: white;
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
            st.error(f"Error en la base de datos: {e}")
    else:
        st.error("❌ Sin stock disponible.")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. BARRA LATERAL (PANEL DE CONTROL) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛠 MENÚ</h2>", unsafe_allow_html=True)
    st.divider()

    # Carga de datos para cálculos
    res_data = supabase.table("productos").select("*").execute()
    df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()
    
    # Botón 1: Alertas
    if not df_full.empty:
        bajo_stock = df_full[df_full['stock'] <= 5]
        label_alerta = f"🚨 ALERTAS ({len(bajo_stock)})" if not bajo_stock.empty else "✅ STOCK AL DÍA"
        if st.button(label_alerta):
            if not bajo_stock.empty:
                @st.dialog("Productos con Stock Bajo")
                def d_alert():
                    st.table(bajo_stock[["nombre", "stock", "categoria"]])
                d_alert()
            else:
                st.toast("Todo el inventario está en niveles óptimos.")

    # Botón 2: Ver Ventas
    if st.button("📊 RESUMEN VENTAS"):
        @st.dialog("Ventas Registradas")
        def d_ventas():
            t1, t2 = st.tabs(["Ventas de Hoy", "Ventas del Mes"])
            with t1:
                hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
                res_v = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
                if res_v.data:
                    df_v = pd.DataFrame(res_v.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
                    st.table(df_v)
                else: st.info("No hay ventas hoy.")
            with t2:
                mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
                res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", mes).execute()
                if res_m.data:
                    df_m = pd.DataFrame(res_m.data).groupby("nombre_producto")["cantidad"].sum().reset_index()
                    st.table(df_m)
                else: st.info("Sin registros este mes.")
        d_ventas()

    # Botón 3: Carga de Mercadería
    if st.button("➕ CARGA / NUEVO"):
        @st.dialog("Entrada de Mercadería")
        def d_carga():
            c = st.text_input("Escanear código de barras")
            if c:
                existente = supabase.table("productos").select("*").eq("codigo_barras", c).execute()
                if existente.data:
                    it = existente.data[0]
                    st.info(f"Actualizando: {it['nombre']}")
                    n = st.number_input("Cantidad a sumar", min_value=1, step=1)
                    if st.button("ACTUALIZAR STOCK"):
                        supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                        st.success("Stock actualizado")
                        st.rerun()
                else:
                    st.warning("🆕 Producto Nuevo")
                    n_nom = st.text_input("Nombre")
                    n_mar = st.text_input("Marca")
                    n_cat = st.selectbox("Categoría", ["Accesorios", "Celulares", "Control remoto", "Cargadores", "Otros"])
                    n_pre = st.number_input("Precio Venta", min_value=0, step=500)
                    n_stk = st.number_input("Stock Inicial", min_value=1, step=1)
                    if st.button("GUARDAR PRODUCTO"):
                        if n_nom:
                            supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": c, "marca": n_mar, "categoria": n_cat, "stock": n_stk, "precio_venta": int(n_pre)}).execute()
                            st.rerun()
        d_carga()

# --- 5. CUERPO CENTRAL: SISTEMA DE VENTAS ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px; font-family: sans-serif;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)
st.write("")

# Escáner de venta (Muy visible)
barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER", value="", help="Pase el escáner sobre el código de barras del producto")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog(f"Venta: {p['nombre']}")
        def d_v(item):
            st.write(f"**Marca:** {item.get('marca', 'N/A')}")
            st.write(f"**Stock Disponible:** {item['stock']}")
            st.write(f"**Precio Unitario:** {formatear_moneda(item['precio_venta'])}")
            st.divider()
            if st.button("🛒 CONFIRMAR VENTA", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
        d_v(p)
    else:
        st.error(f"El código {barcode} no está registrado en el sistema.")

st.divider()

# --- 6. TABLAS DE INVENTARIO POR PESTAÑAS ---
if not df_full.empty:
    # Limpieza de datos preventiva
    for col in ['categoria', 'marca', 'nombre', 'stock', 'precio_venta']:
        if col not in df_full.columns:
            df_full[col] = "N/A"
    
    df_full['categoria'] = df_full['categoria'].fillna("Otros").replace("", "Otros")
    categorias = sorted(df_full['categoria'].unique())
    
    st.subheader("📦 Consulta de Stock")
    tabs = st.tabs(categorias)

    for i, cat in enumerate(categorias):
        with tabs[i]:
            df_cat = df_full[df_full['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
            df_cat.columns = ["Producto", "Marca", "Stock", "Precio"]
            st.table(df_cat.style.format({"Precio": lambda x: formatear_moneda(x)}))
else:
    st.info("No hay productos cargados en la base de datos.")