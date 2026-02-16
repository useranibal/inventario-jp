import streamlit as st
from supabase import create_client, Client
import pandas as pd
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Alycell - Gestión Integral", page_icon="📱", layout="wide")
STOCK_MINIMO = 3

if "scanner_key" not in st.session_state: st.session_state.scanner_key = 0
if "search_query" not in st.session_state: st.session_state.search_query = ""

# --- 2. CSS ---
st.markdown("""
    <style>
    #MainMenu, footer, .stAppDeployButton, [data-testid="stStatusWidget"] {visibility: hidden; display: none !important;}
    [data-testid="stSidebar"] { background-color: #2e2e2e !important; }
    .stButton > button { width: 100%; border-radius: 8px; background-color: #4a4a4a; color: white !important; }
    .stock-alert-bottom { background-color: #e74c3c; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; border: 2px solid white; margin-top: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONEXIÓN ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 4. FUNCIONES ---
def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

def generar_ticket_js(datos):
    fecha = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')
    es_reparacion = datos.get('tipo') == "REPARACION"
    
    ticket_html = f"""
    <script>
    const win = window.open('', 'Ticket', 'width=450,height=700');
    win.document.write('<html><head><style>');
    win.document.write('body {{ width: 75mm; font-family: "Courier New", monospace; font-size: 11px; padding: 5px; }}');
    win.document.write('.header {{ text-align: center; }} .bold {{ font-weight: bold; }}');
    win.document.write('.hr {{ border-top: 1px dashed black; margin: 5px 0; }}');
    win.document.write('.small {{ font-size: 9px; text-align: justify; line-height: 1.1; }}');
    win.document.write('</style></head><body>');
    
    win.document.write('<div style="font-size: 8px;">{fecha}</div>');
    win.document.write('<div class="header">');
    win.document.write('<div style="font-size: 25px;">📱</div>');
    win.document.write('<div class="bold" style="font-size: 15px;">ALICIA CORREA</div>');
    win.document.write('<div>Calle Rancagua Local Alycell</div>');
    win.document.write('<div>+56 963539746</div>');
    win.document.write('</div><div class="hr"></div>');
    
    win.document.write('<div class="bold">ORDEN N°: {datos['id']}</div>');
    win.document.write('<div>F. Emisión: {fecha}</div>');
    
    if ({str(es_reparacion).lower()}) {{
        win.document.write('<div>CLIENTE: {datos.get('cliente', '')}</div>');
        win.document.write('<div>CELULAR: {datos.get('cel_cliente', '')}</div>');
        win.document.write('<div>ASIGNADO: {datos.get('asignado', '')}</div>');
    }}
    
    win.document.write('<div class="hr"></div><div class="bold">DETALLE:</div>');
    win.document.write('<div>{datos['nombre_prod']}</div>');
    win.document.write('<div style="text-align: right; font-size: 13px;" class="bold">TOTAL: {formatear_moneda(datos['precio'])}</div>');
    
    win.document.write('<div class="hr"></div><div class="bold" style="text-align: center;">GARANTÍA</div>');
    win.document.write('<div class="small">');
    if ({str(es_reparacion).lower()}) {{
        win.document.write('1. Garantía 30 días. 2. No intervenidos. 3. Plazo retiro 90 días. 4. Retiro con carnet. 5. No info a terceros. 6. No responsable por agua/químicos. 7. No responsable pérdida módulo. 8. No responsable daños al abrir si viene golpeado. 9. Respuesta 48hrs. 10. Pantallas solo falla táctil/imagen (no rotas/manchadas).');
    }} else {{
        win.document.write('Garantía legal de 30 días por fallas técnicas. Debe presentar su boleta.');
    }}
    win.document.write('</div><div style="margin-top:20px; text-align:center;">_________________<br>Firma</div>');
    
    win.document.write('</body></html>');
    win.document.close(); win.focus(); win.print(); win.close();
    </script>
    """
    components.html(ticket_html, height=1)

def procesar_transaccion(item, tipo, cliente="", cel="", asig=""):
    try:
        supabase.table("productos").update({"stock": item['stock'] - 1}).eq("id", item['id']).execute()
        res = supabase.table("ventas").insert({
            "producto_id": item['id'], "nombre_producto": item['nombre'],
            "precio_venta": int(item['precio_venta']), "total": int(item['precio_venta'])
        }).execute()
        st.session_state.imprimir_ahora = {
            "id": res.data[0]['id'], "nombre_prod": item['nombre'], "precio": item['precio_venta'],
            "marca": item.get('marca',''), "cliente": cliente, "cel_cliente": cel, "asignado": asig, "tipo": tipo
        }
        st.session_state.scanner_key += 1
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

# --- 5. SIDEBAR (MENÚ RECUPERADO) ---
with st.sidebar:
    st.markdown("### 🛠 MENÚ ALYCELL")
    res_side = supabase.table("productos").select("*").execute()
    df_side = pd.DataFrame(res_side.data) if res_side.data else pd.DataFrame()

    if st.button("🚨 DETALLE ALERTAS"):
        if not df_side.empty:
            bajo = df_side[df_side['stock'] <= STOCK_MINIMO]
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
                    n_cos = st.number_input("Costo"); n_st = st.number_input("Stock", value=1); n_ve = st.number_input("Venta")
                    if st.button("GUARDAR"):
                        supabase.table("productos").insert({"nombre": n_nom, "codigo_barras": cod, "marca": n_mar, "categoria": n_cat, "precio_costo": int(n_cos), "precio_venta": int(n_ve), "stock": int(n_st)}).execute()
                        st.rerun()
        d_c()

    if not df_side.empty:
        bajo_c = len(df_side[df_side['stock'] <= STOCK_MINIMO])
        if bajo_c > 0: st.markdown(f'<div class="stock-alert-bottom">⚠️ {bajo_c} PRODUCTOS EN ALERTA</div>', unsafe_allow_html=True)

# --- 6. CUERPO CENTRAL ---
st.markdown('<h1 style="text-align:center; color:white; background:#d35400; border-radius:10px;">📱 ALYCELL SERVICIO TÉCNICO</h1>', unsafe_allow_html=True)

if "imprimir_ahora" in st.session_state:
    generar_ticket_js(st.session_state.imprimir_ahora)
    del st.session_state.imprimir_ahora

barcode = st.text_input("🔍 ESCANEÉ CÓDIGO (CONSULTA / VENTA)", value="", key=f"v_{st.session_state.scanner_key}")

if barcode:
    res_b = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res_b.data:
        p = res_b.data[0]
        @st.dialog("Datos del Producto")
        def d_v(item):
            st.markdown(f"### {item['nombre']}")
            st.markdown(f"<h1 style='color: #27ae60;'>{formatear_moneda(item['precio_venta'])}</h1>", unsafe_allow_html=True)
            st.write(f"Stock: {item['stock']} | Marca: {item['marca']}")
            st.divider()
            
            tipo = st.radio("Tipo de operación:", ["Venta Normal", "Reparación / Servicio Técnico"])
            
            if tipo == "Reparación / Servicio Técnico":
                c = st.text_input("Nombre Cliente")
                t = st.text_input("Celular Cliente")
                a = st.selectbox("Asignado", ["Juan Pablo", "Alicia"])
                if st.button("✅ FINALIZAR Y EMITIR BOLETA"):
                    if c and t: procesar_transaccion(item, "REPARACION", c, t, a)
                    else: st.warning("Complete datos del cliente")
            else:
                if st.button("🛒 VENTA RÁPIDA"):
                    procesar_transaccion(item, "VENTA")
                    
            if st.button("❌ CANCELAR"): 
                st.session_state.scanner_key += 1
                st.rerun()
        d_v(p)

# --- 7. INVENTARIO (VISTA RECUPERADA) ---
st.divider()
@st.fragment(run_every=30)
def vista_tabla():
    bus = st.text_input("🔎 Buscar en Inventario...", value=st.session_state.search_query)
    df_f = pd.DataFrame(supabase.table("productos").select("*").execute().data)
    if not df_f.empty:
        df_f['Precio'] = df_f['precio_venta'].apply(formatear_moneda)
        if bus:
            mask = df_f.apply(lambda row: row.astype(str).str.contains(bus, case=False, na=False)).any(axis=1)
            st.table(df_f[mask][["nombre", "marca", "stock", "Precio"]])
        else:
            df_f['categoria'] = df_f['categoria'].fillna("Otros")
            tabs = st.tabs(sorted(df_f['categoria'].unique()))
            for i, cat in enumerate(sorted(df_f['categoria'].unique())):
                with tabs[i]:
                    st.table(df_f[df_f['categoria'] == cat][["nombre", "marca", "stock", "Precio"]])
vista_tabla()