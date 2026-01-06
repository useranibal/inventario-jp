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
            
            /* Color de fondo para la barra lateral (Sidebar) */
            [data-testid="stSidebar"] {
                background-color: #2e2e2e;
            }
            [data-testid="stSidebar"] * {
                color: white;
            }

            /* HACER EL BOTÓN DE "MOSTRAR MENÚ" MÁS VISIBLE CUANDO SE OCULTA */
            button[kind="headerNoPadding"] {
                background-color: #d35400 !important;
                color: white !important;
                border-radius: 50% !important;
                padding: 5px !important;
            }

            /* Estilo para los botones del menú lateral */
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
            st.error(f"Error: {e}")
    else:
        st.error("❌ Sin stock.")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛠 MENÚ</h2>", unsafe_allow_html=True)
    st.divider()

    res_data = supabase.table("productos").select("*").execute()
    df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()
    
    if not df_full.empty:
        bajo_stock = df_full[df_full['stock'] <= 5]
        label_alerta = f"🚨 ALERTAS ({len(bajo_stock)})" if not bajo_stock.empty else "✅ STOCK OK"
        if st.button(label_alerta):
            if not bajo_stock.empty:
                @st.dialog("Stock Bajo")
                def d_a(): st.table(bajo_stock[["nombre", "stock"]])
                d_a()
            else: st.toast("Todo en orden.")

    if st.button("📊 RESUMEN VENTAS"):
        @st.dialog("Ventas Registradas")
        def d_v():
            t1, t2 = st.tabs(["Hoy", "Mes"])
            with t1:
                hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
                res_h = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
                if res_h.data: st.table(pd.DataFrame(res_h.data).groupby("nombre_producto").sum())
                else: st.info("No hay ventas hoy.")
            with t2:
                mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
                res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", mes).execute()
                if res_m.data: st.table(pd.DataFrame(res_m.data).groupby("nombre_producto").sum())
                else: st.info("Sin registros.")
        d_v()

    if st.button("➕ CARGA / NUEVO"):
        @st.dialog("Ingreso Mercadería")
        def d_c():
            c = st.text_input("Escanear código")
            if c:
                ex = supabase.table("productos").select("*").eq("codigo_barras", c).execute()
                if ex.data:
                    it = ex.data[0]
                    st.info(f"Producto: {it['nombre']}")
                    n = st.number_input("Cantidad a sumar", min_value=1)
                    if st.button("ACTUALIZAR"):
                        supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    st.warning("🆕 Nuevo Producto")
                    n_nom = st.text_input("Nombre")
                    n_mar = st.text_input("Marca")
                    n_cat = st.selectbox("Categoría", ["Accesorios", "Celulares", "Control remoto", "Otros"])
                    n_pre = st.number_input("Precio", min_value=0)
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": c, "marca": n_mar, "categoria": n_cat, "stock": 1, "precio_venta": int(n_pre)}).execute()
                        st.rerun()
        d_c()

# --- 5. CUERPO CENTRAL ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)
st.write("")

barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER O CONSULTAR PRECIO", value="")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog(f"Venta: {p['nombre']}")
        def d_venta(item):
            st.write(f"Stock: {item['stock']} | Precio: {formatear_moneda(item['precio_venta'])}")
            if st.button("🛒 CONFIRMAR VENTA", type="primary", use_container_width=True):
                realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
        d_venta(p)

st.divider()

# --- 6. TABLAS POR CATEGORÍA ---
if not df_full.empty:
    for col in ['categoria', 'marca', 'nombre', 'stock', 'precio_venta']:
        if col not in df_full.columns: df_full[col] = "N/A"
    
    df_full['categoria'] = df_full['categoria'].fillna("Otros").replace("", "Otros")
    categorias = sorted(df_full['categoria'].unique())
    tabs = st.tabs(categorias)

    for i, cat in enumerate(categorias):
        with tabs[i]:
            df_cat = df_full[df_full['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
            df_cat.columns = ["Producto", "Marca", "Stock", "Precio"]
            st.table(df_cat.style.format({"Precio": lambda x: formatear_moneda(x)}))