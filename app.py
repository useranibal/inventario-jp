import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Alycell - Gestión", page_icon="📱", layout="wide")

# DATOS CONFIGURADOS (Corregido según tu captura)
SHEET_ID = "1Z8o3YqmkrAHYQYeYhaxs1IwBeLlpo-b8FeGfBrqGKOk" 
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbyQ9OlxXZjwWuC-f2u2wS9m61mFmv5sFulPVc48_ClZzu49OQZkB_1mIPFQJzgCSwJL/exec"

# URL para leer los productos (Asegúrate que la pestaña se llame 'productos')
URL_PRODUCTOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=productos"

# --- 2. FUNCIONES ---
def cargar_datos():
    try:
        # Usamos un parámetro random para evitar el caché de Google
        df = pd.read_csv(f"{URL_PRODUCTOS}&cache_bust={pd.Timestamp.now().timestamp()}")
        return df
    except Exception as e:
        st.error(f"Error al leer Excel: {e}")
        st.info("Asegúrate de que el archivo de Google Sheets esté compartido como: 'Cualquier persona con el enlace' -> EDITOR")
        return pd.DataFrame()

def enviar_venta_a_google(datos):
    try:
        response = requests.post(URL_APPS_SCRIPT, json=datos)
        return response.status_code == 200
    except:
        return False

def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

def generar_ticket_js(datos):
    fecha = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')
    es_reparacion = datos.get('tipo') == "Reparación"
    
    ticket_html = f"""
    <script>
    const win = window.open('', 'Ticket', 'width=450,height=700');
    win.document.write('<html><head><style>');
    win.document.write('body {{ width: 80mm; font-family: "Courier New", monospace; font-size: 12px; padding: 10px; }}');
    win.document.write('.header {{ text-align: center; font-weight: bold; font-size: 16px; }}');
    win.document.write('.hr {{ border-top: 1px dashed black; margin: 10px 0; }}');
    win.document.write('.total {{ font-size: 18px; font-weight: bold; text-align: right; }}');
    win.document.write('.small {{ font-size: 10px; text-align: justify; }}');
    win.document.write('</style></head><body>');
    
    win.document.write('<div class="header">📱 ALYCELL</div>');
    win.document.write('<div style="text-align:center;">Alicia Correa<br>Calle Rancagua Local Alycell<br>+56 963539746</div>');
    win.document.write('<div class="hr"></div>');
    win.document.write('<div>FECHA: {fecha}</div>');
    
    if ({str(es_reparacion).lower()}) {{
        win.document.write('<div>CLIENTE: {datos.get('cliente', '')}</div>');
        win.document.write('<div>CELULAR: {datos.get('celular', '')}</div>');
    }}
    
    win.document.write('<div class="hr"></div>');
    win.document.write('<div style="font-weight:bold;">DETALLE:</div>');
    win.document.write('<div>{datos['nombre']}</div>');
    win.document.write('<div class="total">TOTAL: {formatear_moneda(datos['precio'])}</div>');
    
    win.document.write('<div class="hr"></div>');
    win.document.write('<div class="small"><b>GARANTÍA:</b> 30 días por fallas técnicas. No cubre golpes, humedad o intervención de terceros. Plazo máximo de retiro: 90 días.</div>');
    win.document.write('<div style="margin-top:30px; text-align:center;">_______________________<br>Firma Cliente</div>');
    
    win.document.write('</body></html>');
    win.document.close(); win.focus(); win.print(); win.close();
    </script>
    """
    components.html(ticket_html, height=1)

# --- 3. INTERFAZ ---
st.markdown('<h1 style="text-align:center; color:white; background:#d35400; padding:10px; border-radius:10px;">📱 ALYCELL - SISTEMA DE CONTROL</h1>', unsafe_allow_html=True)

df = cargar_datos()

if "scan_key" not in st.session_state: st.session_state.scan_key = 0
barcode = st.text_input("🔍 ESCANEE AQUÍ PARA VENDER O CONSULTAR", key=f"s_{st.session_state.scan_key}")

if barcode and not df.empty:
    # Ajustamos para que busque el código de barras sin importar si es número o texto
    res = df[df['codigo_barras'].astype(str).str.contains(str(barcode))]
    
    if not res.empty:
        p = res.iloc[0]
        @st.dialog("OPCIONES DE PRODUCTO")
        def d_venta(item):
            st.markdown(f"## {item['nombre']}")
            st.markdown(f"<h1 style='color: #27ae60; text-align: center;'>{formatear_moneda(item['precio_venta'])}</h1>", unsafe_allow_html=True)
            st.write(f"**Stock disponible:** {item['stock']} | **Marca:** {item['marca']}")
            st.divider()
            
            opcion = st.radio("Seleccione tipo de venta:", ["Venta Rápida", "Reparación"])
            
            c_nom = ""
            c_cel = ""
            if opcion == "Reparación":
                c_nom = st.text_input("Nombre del Cliente")
                c_cel = st.text_input("Celular")
            
            if st.button("🛒 FINALIZAR Y REGISTRAR"):
                if opcion == "Reparación" and (not c_nom or not c_cel):
                    st.warning("Por favor, ingrese los datos del cliente para la reparación.")
                else:
                    datos_finales = {
                        "nombre": item['nombre'],
                        "precio": int(item['precio_venta']),
                        "codigo": str(item['codigo_barras']),
                        "cliente": c_nom,
                        "celular": c_cel,
                        "tipo": opcion
                    }
                    
                    with st.spinner("Procesando..."):
                        if enviar_venta_a_google(datos_finales):
                            st.success("¡Venta exitosa! Stock actualizado.")
                            generar_ticket_js(datos_finales)
                            st.session_state.scan_key += 1
                            st.rerun()
                        else:
                            st.error("Error al conectar con Google Sheets. Revise la conexión.")
        d_venta(p)
    else:
        st.error(f"El código [{barcode}] no existe en el inventario.")

# --- 4. TABLA DE STOCK ---
st.divider()
if not df.empty:
    with st.expander("📦 VER INVENTARIO COMPLETO"):
        st.dataframe(df[["nombre", "marca", "stock", "precio_venta"]], use_container_width=True)