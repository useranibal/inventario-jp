import streamlit as st
from supabase import create_client, Client
import pandas as pd
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Alycell - Gestión", page_icon="📱", layout="wide")
STOCK_MINIMO = 3

if "scanner_key" not in st.session_state: st.session_state.scanner_key = 0
if "search_query" not in st.session_state: st.session_state.search_query = ""

# --- CSS ---
st.markdown("""
    <style>
    #MainMenu, footer, .stAppDeployButton, [data-testid="stStatusWidget"] {visibility: hidden; display: none !important;}
    [data-testid="stSidebar"] { background-color: #2e2e2e !important; }
    .stButton > button { width: 100%; border-radius: 8px; background-color: #4a4a4a; color: white !important; }
    .stock-alert-bottom { background-color: #e74c3c; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; border: 2px solid white; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 3. FUNCIONES ---
def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

def generar_ticket_js(datos_venta):
    """Genera el ticket térmico de 80mm con todas las cláusulas"""
    fecha_actual = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')
    
    ticket_html = f"""
    <script>
    function imprimir() {{
        var win = window.open('', 'print', 'width=400,height=600');
        win.document.write('<html><head><style>');
        win.document.write('body {{ width: 80mm; font-family: "Courier New", Courier, monospace; font-size: 12px; padding: 5px; }}');
        win.document.write('.header {{ text-align: center; }}');
        win.document.write('.logo {{ font-size: 40px; }}');
        win.document.write('.bold {{ font-weight: bold; }}');
        win.document.write('.small {{ font-size: 10px; text-align: justify; }}');
        win.document.write('.hr {{ border-top: 1px dashed black; margin: 5px 0; }}');
        win.document.write('</style></head><body>');
        
        // Encabezado
        win.document.write('<div style="font-size: 10px;">{fecha_actual}</div>');
        win.document.write('<div class="header">');
        win.document.write('<div class="logo">📱</div>');
        win.document.write('<div class="bold" style="font-size: 16px;">ALICIA CORREA</div>');
        win.document.write('<div>Calle Rancagua Local Alycell</div>');
        win.document.write('<div>Celular: +56 963539746</div>');
        win.document.write('</div>');
        
        win.document.write('<div class="hr"></div>');
        win.document.write('<div class="bold">ORDEN N°: {datos_venta['id']}</div>');
        win.document.write('<div>F. Emisión: {fecha_actual}</div>');
        win.document.write('<div>F. Entrega: {fecha_actual}</div>');
        win.document.write('<div class="hr"></div>');
        
        // Datos Cliente
        win.document.write('<div><span class="bold">CLIENTE:</span> {datos_venta['cliente']}</div>');
        win.document.write('<div><span class="bold">CELULAR:</span> {datos_venta['cel_cliente']}</div>');
        win.document.write('<div><span class="bold">ASIGNADO:</span> {datos_venta['asignado']}</div>');
        win.document.write('<div class="hr"></div>');
        
        // Producto
        win.document.write('<div class="bold">DETALLE PRODUCTO:</div>');
        win.document.write('<div>{datos_venta['nombre_prod']}</div>');
        win.document.write('<div>Marca: {datos_venta['marca']}</div>');
        win.document.write('<div style="text-align: right; font-size: 14px;" class="bold">TOTAL: {formatear_moneda(datos_venta['precio'])}</div>');
        
        // Garantía
        win.document.write('<div class="hr"></div>');
        win.document.write('<div class="bold" style="text-align: center;">TÉRMINOS DE GARANTÍA</div>');
        win.document.write('<div class="small">');
        win.document.write('1. Garantía aplica 30 días desde entrega o aviso.<br>');
        win.document.write('2. Equipos intervenidos por terceros pierden garantía.<br>');
        win.document.write('3. Plazo máx. retiro: 90 días.<br>');
        win.document.write('4. Retiro titular o autorizado con carnet.<br>');
        win.document.write('5. No se entrega info a terceros.<br>');
        win.document.write('6. ST no responde por daños químicos/líquidos previos.<br>');
        win.document.write('7. ST no responde por pérdida de módulo.<br>');
        win.document.write('8. No hay responsabilidad si equipo golpeado se daña al abrir.<br>');
        win.document.write('9. Tiempo respuesta garantía: 48 horas.<br>');
        win.document.write('10. Pantallas solo garantía por funcionalidad, no por manchas o roturas.');
        win.document.write('</div>');
        
        win.document.write('<div style="margin-top:20px; text-align:center;">_____________________<br>Firma Cliente</div>');
        
        win.document.write('</body></html>');
        win.document.close();
        win.print();
        win.close();
    }}
    imprimir();
    </script>
    """
    components.html(ticket_html, height=0)

def realizar_venta(p_id, stock, nombre, precio, marca, cliente, cel, asignado):
    if stock > 0:
        try:
            # 1. Descontar stock
            supabase.table("productos").update({"stock": stock - 1}).eq("id", p_id).execute()
            # 2. Registrar venta
            res = supabase.table("ventas").insert({
                "producto_id": p_id, "nombre_producto": nombre,
                "cantidad": 1, "precio_venta": int(float(precio)), "total": int(float(precio))
            }).execute()
            
            # 3. Preparar impresión (usamos el ID de la venta recién creada)
            nueva_venta_id = res.data[0]['id']
            st.session_state.imprimir_ahora = {
                "id": nueva_venta_id, "nombre_prod": nombre, "precio": precio,
                "marca": marca, "cliente": cliente, "cel_cliente": cel, "asignado": asignado
            }
            st.session_state.scanner_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ ALYCELL")
    res_data = supabase.table("productos").select("*").execute()
    df_full = pd.DataFrame(res_data.data) if res_data.data else pd.DataFrame()

    if st.button("🚨 DETALLE ALERTAS"):
        bajo = df_full[df_full['stock'] <= STOCK_MINIMO]
        if not bajo.empty:
            @st.dialog("Stock Bajo")
            def d(): st.table(bajo[["nombre", "stock"]])
            d()
    
    if st.button("➕ CARGA / NUEVO"):
        @st.dialog("Inventario")
        def d_c():
            cod = st.text_input("Código")
            if cod:
                ex = supabase.table("productos").select("*").eq("codigo_barras", cod).execute()
                if ex.data:
                    it = ex.data[0]
                    n = st.number_input("Sumar stock", min_value=1)
                    if st.button("OK"):
                        supabase.table("productos").update({"stock": it['stock']+n}).eq("id", it['id']).execute()
                        st.rerun()
                else:
                    n_nom = st.text_input("Nombre"); n_mar = st.text_input("Marca"); n_cat = st.text_input("Categoría")
                    c1, c2 = st.columns(2)
                    with c1: n_cos = st.number_input("Costo"); n_st = st.number_input("Stock", value=1)
                    with c2: n_ve = st.number_input("Venta")
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": cod, "marca": n_mar, "categoria": n_cat, "precio_costo": int(n_cos), "precio_venta": int(n_ve), "stock": int(n_st)}).execute()
                        st.rerun()
        d_c()

# --- 5. CUERPO CENTRAL ---
st.markdown('<h1 style="text-align:center; color:white; background:#d35400; border-radius:10px;">📱 ALYCELL SERVICIO TÉCNICO</h1>', unsafe_allow_html=True)

if "imprimir_ahora" in st.session_state:
    generar_ticket_js(st.session_state.imprimir_ahora)
    del st.session_state.imprimir_ahora

barcode = st.text_input("🔍 ESCANEÉ CÓDIGO", value="", key=f"v_{st.session_state.scanner_key}")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog("Datos de la Orden")
        def d_orden(item):
            st.subheader(item['nombre'])
            nom_c = st.text_input("Nombre del Cliente")
            cel_c = st.text_input("Celular Cliente")
            asig = st.selectbox("Asignado a:", ["Juan Pablo", "Alicia"])
            st.divider()
            if st.button("🛒 CONFIRMAR VENTA E IMPRIMIR", type="primary"):
                if nom_c:
                    realizar_venta(item['id'], item['stock'], item['nombre'], item['precio_venta'], item.get('marca',''), nom_c, cel_c, asig)
                else:
                    st.warning("Ingrese nombre del cliente")
        d_orden(p)

st.divider()

# --- 6. BUSCADOR Y TABLAS ---
@st.fragment(run_every=20)
def seccion_inventario():
    bus = st.text_input("🔍 Buscar Producto...", value=st.session_state.search_query)
    df_f = pd.DataFrame(supabase.table("productos").select("*").execute().data)
    if not df_f.empty:
        df_f['Precio'] = df_f['precio_venta'].apply(formatear_moneda)
        if bus:
            mask = df_f.apply(lambda row: row.astype(str).str.contains(bus, case=False, na=False)).any(axis=1)
            st.table(df_f[mask][["nombre", "marca", "stock", "Precio"]])
        else:
            tabs = st.tabs(sorted(df_f['categoria'].unique()))
            for i, cat in enumerate(sorted(df_f['categoria'].unique())):
                with tabs[i]:
                    st.table(df_f[df_f['categoria'] == cat][["nombre", "marca", "stock", "Precio"]])

seccion_inventario()