import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Gestión de Inventario JP", 
    page_icon="📱", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Inicializar estado para limpiar el buscador
if "scanner_key" not in st.session_state:
    st.session_state.scanner_key = 0

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display:none !important;}
            [data-testid="stStatusWidget"] {display:none !important;}
            
            [data-testid="stSidebarCollapsedControl"] {
                background-color: #d35400 !important;
                color: white !important;
                border-radius: 5px !important;
            }
            
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
                color: white !important;
            }

            [data-testid="stSidebar"] {
                background-color: #2e2e2e !important;
            }
            
            .stButton > button {
                width: 100%;
                border-radius: 8px;
                height: 3.5em;
                background-color: #4a4a4a;
                color: white !important;
                border: 1px solid #666;
            }

            .stock-alert-bottom {
                background-color: #e74c3c;
                color: white;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
                border: 1px solid #ffffff;
                margin-top: 20px;
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
            # 1. Actualizar Stock
            supabase.table("productos").update({"stock": stock_actual - 1}).eq("id", producto_id).execute()
            # 2. Registrar Venta
            supabase.table("ventas").insert({
                "producto_id": producto_id, "nombre_producto": nombre,
                "cantidad": 1, "precio_venta": precio_int, "total": precio_int
            }).execute()
            
            st.toast(f"✅ Venta exitosa: {nombre}")
            # 3. Cambiar key para limpiar el buscador y reiniciar
            st.session_state.scanner_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error en la transacción: {e}")

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ DE CONTROL")
    st.divider()

    res_data = supabase.table("productos").select("*").execute()
    df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()

    if st.button("🚨 VER DETALLE ALERTAS"):
        if not df_full.empty:
            bajo = df_full[df_full['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= 5]
            if not bajo.empty:
                @st.dialog("Productos por Reponer")
                def d_a(): st.table(bajo[["nombre", "stock"]])
                d_a()

    if st.button("📊 RESUMEN VENTAS"):
        @st.dialog("Resumen de Ventas")
        def d_v():
            t1, t2 = st.tabs(["Hoy", "Mes"])
            with t1:
                hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
                res = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", hoy).execute()
                if res.data: st.table(pd.DataFrame(res.data).groupby("nombre_producto").sum().reset_index())
            with t2:
                mes = pd.Timestamp.now().replace(day=1).strftime('%Y-%m-%d')
                res_m = supabase.table("ventas").select("nombre_producto, cantidad").gte("created_at", mes).execute()
                if res_m.data: st.table(pd.DataFrame(res_m.data).groupby("nombre_producto").sum().reset_index())
        d_v()

    if st.button("➕ CARGA / NUEVO"):
        @st.dialog("Gestión de Stock")
        def d_c():
            c = st.text_input("Código")
            if c:
                ex = supabase.table("productos").select("*").eq("codigo_barras", c).execute()
                if ex.data:
                    it = ex.data[0]
                    n = st.number_input("Sumar stock", min_value=1)
                    if st.button("ACTUALIZAR"):
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

    # ALERTA INFERIOR
    st.markdown("<br><br>", unsafe_allow_html=True)
    if not df_full.empty:
        bajo_stock = df_full[df_full['stock'].apply(pd.to_numeric, errors='coerce').fillna(0) <= 5]
        if not bajo_stock.empty:
            st.markdown(f'<div class="stock-alert-bottom">⚠️ ATENCIÓN<br>Hay {len(bajo_stock)} productos con<br>stock mínimo</div>', unsafe_allow_html=True)

# --- 5. CUERPO CENTRAL (SISTEMA DE VENTAS) ---
st.markdown('<h1 style="background-color: #d35400; color: white; padding: 15px; text-align: center; border-radius: 10px;">📱 Sistema de Control JP</h1>', unsafe_allow_html=True)

# El buscador usa un key dinámico para resetearse
barcode = st.text_input("🔍 ESCANEÉ AQUÍ PARA VENDER", value="", key=f"v_main_{st.session_state.scanner_key}")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        # Mostramos la información del producto antes de vender
        @st.dialog(f"Confirmar Venta")
        def d_confirmar(item):
            st.subheader(item['nombre'])
            st.write(f"**Marca:** {item.get('marca', 'N/A')}")
            st.write(f"**Precio:** {formatear_moneda(item['precio_venta'])}")
            st.write(f"**Stock actual:** {item['stock']} unidades")
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🛒 VENDER", type="primary", use_container_width=True):
                    realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'])
            with col2:
                if st.button("❌ CANCELAR", use_container_width=True):
                    st.session_state.scanner_key += 1 # Limpia el buscador
                    st.rerun()
        d_confirmar(p)
    else:
        st.error("Código no encontrado. Regístrelo en el menú lateral.")

st.divider()

# --- 6. TABLAS DE INVENTARIO ---
if not df_full.empty:
    df_full['categoria'] = df_full['categoria'].fillna("Otros").replace("", "Otros")
    categorias = sorted(df_full['categoria'].unique())
    tabs = st.tabs(categorias)
    for i, cat in enumerate(categorias):
        with tabs[i]:
            df_cat = df_full[df_full['categoria'] == cat][["nombre", "marca", "stock", "precio_venta"]]
            st.table(df_cat.rename(columns={"nombre":"Producto", "precio_venta":"Precio"}))