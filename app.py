import streamlit as st
from supabase import create_client, Client
import pandas as pd
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Alycell - Gestión de Inventario", 
    page_icon="📱", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

STOCK_MINIMO = 3

# Inicializar estados de sesión
if "scanner_key" not in st.session_state:
    st.session_state.scanner_key = 0
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# --- 2. CSS PARA OCULTAR ELEMENTOS DE STREAMLIT ---
st.markdown("""
    <style>
    #MainMenu, footer, .stAppDeployButton, [data-testid="stStatusWidget"], .viewerBadge_container__1QS1n {
        visibility: hidden; display: none !important;
    }
    [data-testid="stSidebar"] { background-color: #2e2e2e !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton > button { 
        width: 100%; border-radius: 8px; height: 3.5em;
        background-color: #4a4a4a; color: white !important; 
    }
    .stock-alert-bottom { 
        background-color: #e74c3c; color: white; padding: 15px; 
        border-radius: 10px; text-align: center; font-weight: bold; 
        border: 2px solid white; margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONEXIÓN A BASE DE DATOS ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except:
    url = "TU_URL_AQUI"
    key = "TU_KEY_AQUI"

supabase: Client = create_client(url, key)

# --- 4. FUNCIONES DE LÓGICA ---
def formatear_moneda(valor):
    try:
        v = int(float(valor))
        return f"$ {v:,}".replace(",", ".")
    except:
        return f"$ {valor}"

def generar_ticket_js(datos):
    """Genera el ticket térmico de 80mm con las 10 cláusulas de Alycell"""
    fecha_emision = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')
    precio_f = formatear_moneda(datos['precio'])
    
    ticket_html = f"""
    <script>
    const win = window.open('', 'ImprimirTicket', 'width=450,height=700');
    win.document.write('<html><head><style>');
    win.document.write('body {{ width: 80mm; font-family: "Courier New", monospace; font-size: 12px; padding: 5px; margin: 0; }}');
    win.document.write('.header {{ text-align: center; margin-bottom: 10px; }}');
    win.document.write('.bold {{ font-weight: bold; }}');
    win.document.write('.hr {{ border-top: 1px dashed black; margin: 5px 0; }}');
    win.document.write('.small {{ font-size: 10px; text-align: justify; line-height: 1.2; }}');
    win.document.write('</style></head><body>');
    
    win.document.write('<div style="font-size: 9px;">{fecha_emision}</div>');
    win.document.write('<div class="header">');
    win.document.write('<div style="font-size: 35px;">📱</div>');
    win.document.write('<div class="bold" style="font-size: 18px;">ALICIA CORREA</div>');
    win.document.write('<div>Calle Rancagua Local Alycell</div>');
    win.document.write('<div>Celular: +56 963539746</div>');
    win.document.write('</div>');
    
    win.document.write('<div class="hr"></div>');
    win.document.write('<div class="bold">ORDEN N°: {datos['id']}</div>');
    win.document.write('<div>F. Emisión: {fecha_emision}</div>');
    win.document.write('<div>F. Entrega: {fecha_emision}</div>');
    win.document.write('<div class="hr"></div>');
    
    win.document.write('<div><span class="bold">CLIENTE:</span> {datos['cliente']}</div>');
    win.document.write('<div><span class="bold">CELULAR:</span> {datos['cel_cliente']}</div>');
    win.document.write('<div><span class="bold">ASIGNADO:</span> {datos['asignado']}</div>');
    win.document.write('<div class="hr"></div>');
    
    win.document.write('<div class="bold">PRODUCTO:</div>');
    win.document.write('<div>{datos['nombre_prod']}</div>');
    win.document.write('<div>Marca: {datos['marca']}</div>');
    win.document.write('<div style="text-align: right; font-size: 14px;" class="bold">TOTAL: {precio_f}</div>');
    
    win.document.write('<div class="hr"></div>');
    win.document.write('<div class="bold" style="text-align: center;">TÉRMINOS DE GARANTÍA</div>');
    win.document.write('<div class="small">');
    win.document.write('1. La Garantía se aplica 30 días desde que se entrega al cliente o se le informa.<br>');
    win.document.write('2. Teléfonos intervenidos por terceros NO tienen garantía.<br>');
    win.document.write('3. Plazo máximo para retirar un celular: 90 días desde ingreso a ST.<br>');
    win.document.write('4. Retiro por titular o autorizado con carnet de identidad.<br>');
    win.document.write('5. No se entrega información a terceros sobre el servicio.<br>');
    win.document.write('6. ST no se hace responsable por equipos con agua, tablet o PC. El lavado químico puede dañar componentes internos por efectos del líquido previo.<br>');
    win.document.write('7. ST no se hace responsable de la pérdida del módulo del equipo.<br>');
    win.document.write('8. Equipos golpeados/pisoteados: Alycell no responde si el equipo se daña al abrirlo.<br>');
    win.document.write('9. Respuesta de garantía: 48 horas según indicación técnica.<br>');
    win.document.write('10. Pantallas cambiadas: Garantía solo si funcionalidad es OK. Pantallas manchadas o rotas NO tienen garantía.');
    win.document.write('</div>');
    
    win.document.write('<div style="margin-top:25px; text-align:center;">_______________________<br>Firma Cliente</div>');
    win.document.write('</body></html>');
    
    win.document.close();
    win.focus();
    win.print();
    win.close();
    </script>
    """
    components.html(ticket_html, height=1)

def realizar_venta(p_id, stock, nombre, precio, marca, cliente, cel, asignado):
    if stock > 0:
        try:
            supabase.table("productos").update({"stock": stock - 1}).eq("id", p_id).execute()
            res = supabase.table("ventas").insert({
                "producto_id": p_id, "nombre_producto": nombre,
                "cantidad": 1, "precio_venta": int(float(precio)), "total": int(float(precio))
            }).execute()
            
            # Guardar datos para que el JS se dispare al recargar
            st.session_state.imprimir_ahora = {
                "id": res.data[0]['id'], "nombre_prod": nombre, "precio": precio,
                "marca": marca, "cliente": cliente, "cel_cliente": cel, "asignado": asignado
            }
            st.session_state.scanner_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error en venta: {e}")

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ ALYCELL")
    st.divider()
    
    res_side = supabase.table("productos").select("*").execute()
    df_side = pd.DataFrame(res_side.data) if res_side.data else pd.DataFrame()

    if st.button("🚨 VER DETALLE ALERTAS"):
        if not df_side.empty:
            bajo = df_side[df_side['stock'] <= STOCK_MINIMO]
            if not bajo.empty:
                @st.dialog("Stock por Reponer")
                def d_alertas():
                    st.table(bajo[["nombre", "marca", "stock"]])
                d_alertas()
            else: st.toast("Inventario OK")

    if st.button("➕ CARGAR / NUEVO"):
        @st.dialog("Gestión Inventario")
        def d_carga():
            cod = st.text_input("Código de Barras")
            if cod:
                ex = supabase.table("productos").select("*").eq("codigo_barras", cod).execute()
                if ex.data:
                    it = ex.data[0]
                    n = st.number_input("Sumar Stock", min_value=1, value=1)
                    if st.button("ACTUALIZAR"):
                        supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    st.warning("NUEVO PRODUCTO")
                    n_nom = st.text_input("Nombre"); n_mar = st.text_input("Marca"); n_cat = st.text_input("Categoría")
                    c1, c2 = st.columns(2)
                    with c1: n_cos = st.number_input("Costo"); n_stk = st.number_input("Stock", value=1)
                    with c2: n_ven = st.number_input("Venta")
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": cod, "marca": n_mar, "categoria": n_cat, "precio_costo": int(n_cos), "precio_venta": int(n_ven), "stock": int(n_stk)}).execute()
                        st.rerun()
        d_carga()

    # Alerta Inferior
    if not df_side.empty:
        bajo_count = len(df_side[df_side['stock'] <= STOCK_MINIMO])
        if bajo_count > 0:
            st.markdown(f'<div class="stock-alert-bottom">⚠️ {bajo_count} PRODUCTOS<br>STOCK MÍNIMO</div>', unsafe_allow_html=True)

# --- 6. CUERPO CENTRAL ---
st.markdown('<h1 style="text-align:center; color:white; background:#d35400; border-radius:10px; padding:10px;">📱 ALYCELL SERVICIO TÉCNICO</h1>', unsafe_allow_html=True)

# DISPARADOR DE IMPRESIÓN
if "imprimir_ahora" in st.session_state:
    generar_ticket_js(st.session_state.imprimir_ahora)
    del st.session_state.imprimir_ahora

# Input de venta
barcode = st.text_input("🔍 ESCANEÉ CÓDIGO PARA VENDER", value="", key=f"v_{st.session_state.scanner_key}")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog("Confirmar Orden")
        def d_orden(item):
            st.subheader(item['nombre'])
            nom_c = st.text_input("Nombre del Cliente")
            cel_c = st.text_input("Celular Cliente")
            asig = st.selectbox("Asignado a:", ["Juan Pablo", "Alicia"])
            st.divider()
            if st.button("🛒 PROCESAR VENTA E IMPRIMIR", type="primary"):
                if nom_c:
                    realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'], item.get('marca',''), nom_c, cel_c, asig)
                else:
                    st.error("Debe ingresar el nombre del cliente.")
            if st.button("CANCELAR"):
                st.session_state.scanner_key += 1
                st.rerun()
        d_orden(p)

st.divider()

# --- 7. BUSCADOR Y TABLAS (FRAGMENT) ---
@st.fragment(run_every=20)
def seccion_inventario():
    col_bus, col_lim = st.columns([4,1])
    with col_bus:
        bus = st.text_input("🔍 Buscar por Nombre, Marca o Categoría...", value=st.session_state.search_query)
    with col_lim:
        st.write(" ")
        if st.button("🧹 Limpiar"):
            st.session_state.search_query = ""
            st.rerun()

    df_f = pd.DataFrame(supabase.table("productos").select("*").execute().data)
    if not df_f.empty:
        df_f['Precio'] = df_f['precio_venta'].apply(formatear_moneda)
        if bus:
            st.session_state.search_query = bus
            mask = df_f.apply(lambda row: row.astype(str).str.contains(bus, case=False, na=False)).any(axis=1)
            st.table(df_f[mask][["nombre", "marca", "stock", "Precio"]].rename(columns={"nombre":"Producto"}))
        else:
            df_f['categoria'] = df_f['categoria'].fillna("Otros").replace("", "Otros")
            tabs = st.tabs(sorted(df_f['categoria'].unique()))
            for i, cat in enumerate(sorted(df_f['categoria'].unique())):
                with tabs[i]:
                    st.table(df_f[df_f['categoria'] == cat][["nombre", "marca", "stock", "Precio"]].rename(columns={"nombre":"Producto"}))

seccion_inventario()