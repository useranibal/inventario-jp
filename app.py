import streamlit as st
from supabase import create_client, Client
import pandas as pd
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Alycell - Gestión", page_icon="📱", layout="wide")
STOCK_MINIMO = 3

if "scanner_key" not in st.session_state: st.session_state.scanner_key = 0

# --- 2. CONEXIÓN ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 3. FUNCIONES ---
def formatear_moneda(valor):
    try: return f"$ {int(float(valor)):,}".replace(",", ".")
    except: return f"$ {valor}"

def generar_ticket_js(datos):
    """Genera el ticket según el tipo (Venta o Reparación)"""
    fecha = pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')
    es_reparacion = datos.get('tipo') == "REPARACION"
    
    ticket_html = f"""
    <script>
    const win = window.open('', 'Ticket', 'width=450,height=700');
    win.document.write('<html><head><style>');
    win.document.write('body {{ width: 80mm; font-family: "Courier New", monospace; font-size: 12px; padding: 5px; }}');
    win.document.write('.header {{ text-align: center; }} .bold {{ font-weight: bold; }}');
    win.document.write('.hr {{ border-top: 1px dashed black; margin: 5px 0; }}');
    win.document.write('.small {{ font-size: 10px; text-align: justify; }}');
    win.document.write('</style></head><body>');
    
    win.document.write('<div style="font-size: 9px;">{fecha}</div>');
    win.document.write('<div class="header">');
    win.document.write('<div style="font-size: 30px;">📱</div>');
    win.document.write('<div class="bold" style="font-size: 16px;">ALICIA CORREA</div>');
    win.document.write('<div>Calle Rancagua Local Alycell</div>');
    win.document.write('<div>+56 963539746</div>');
    win.document.write('</div><div class="hr"></div>');
    
    win.document.write('<div class="bold">ORDEN N°: {datos['id']}</div>');
    if {str(es_reparacion).lower()}:
        win.document.write('<div>CLIENTE: {datos.get('cliente', '---')}</div>');
        win.document.write('<div>CELULAR: {datos.get('cel_cliente', '---')}</div>');
        win.document.write('<div>ASIGNADO: {datos.get('asignado', '---')}</div>');
    
    win.document.write('<div class="hr"></div><div class="bold">PRODUCTO/SERVICIO:</div>');
    win.document.write('<div>{datos['nombre_prod']}</div>');
    win.document.write('<div style="text-align: right; font-size: 14px;" class="bold">TOTAL: {formatear_moneda(datos['precio'])}</div>');
    
    win.document.write('<div class="hr"></div><div class="bold" style="text-align: center;">GARANTÍA</div>');
    win.document.write('<div class="small">');
    win.document.write('1. 30 días de garantía. 2. No intervenidos por terceros. 3. Retiro máx 90 días.');
    if {str(es_reparacion).lower()}:
        win.document.write(' 4. Mostrar carnet. 5. No info a terceros. 6. No responsable por agua. 7. No responsable pérdida módulo. 8. No responsable por golpes al abrir. 9. Respuesta 48hrs. 10. Pantallas solo falla funcional.');
    win.document.write('</div><div style="margin-top:20px; text-align:center;">_________________<br>Firma</div>');
    
    win.document.write('</body></html>');
    win.document.close(); win.focus(); win.print(); win.close();
    </script>
    """
    components.html(ticket_html, height=1)

def procesar_transaccion(item, tipo, cliente="", cel="", asig=""):
    try:
        # Descontar stock
        supabase.table("productos").update({"stock": item['stock'] - 1}).eq("id", item['id']).execute()
        # Registrar venta
        res = supabase.table("ventas").insert({
            "producto_id": item['id'], "nombre_producto": item['nombre'],
            "precio_venta": int(item['precio_venta']), "total": int(item['precio_venta'])
        }).execute()
        
        st.session_state.imprimir_ahora = {
            "id": res.data[0]['id'], "nombre_prod": item['nombre'], "precio": item['precio_venta'],
            "marca": item.get('marca',''), "cliente": cliente, "cel_cliente": cel, 
            "asignado": asig, "tipo": tipo
        }
        st.session_state.scanner_key += 1
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

# --- 4. INTERFAZ ---
st.markdown('<h1 style="text-align:center; color:white; background:#d35400; border-radius:10px;">📱 ALYCELL SISTEMA</h1>', unsafe_allow_html=True)

if "imprimir_ahora" in st.session_state:
    generar_ticket_js(st.session_state.imprimir_ahora)
    del st.session_state.imprimir_ahora

barcode = st.text_input("🔍 ESCANEÉ CÓDIGO", value="", key=f"v_{st.session_state.scanner_key}")

if barcode:
    res = supabase.table("productos").select("*").eq("codigo_barras", barcode).execute()
    if res.data:
        p = res.data[0]
        @st.dialog("Opciones de Producto")
        def d_opciones(item):
            st.markdown(f"### {item['nombre']}")
            st.markdown(f"## PRECIO: {formatear_moneda(item['precio_venta'])}")
            st.write(f"Stock actual: {item['stock']} | Marca: {item['marca']}")
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🛒 VENTA RÁPIDA", help="Solo boleta de precio"):
                    procesar_transaccion(item, "VENTA")
            with col2:
                reparar = st.toggle("🛠 ES REPARACIÓN / SERVICIO")
            
            if reparar:
                st.info("Complete datos del cliente para la garantía completa")
                nom_c = st.text_input("Nombre Cliente")
                cel_c = st.text_input("Celular")
                asig = st.selectbox("Asignado", ["Juan Pablo", "Alicia"])
                if st.button("✅ FINALIZAR REPARACIÓN"):
                    if nom_c and cel_c:
                        procesar_transaccion(item, "REPARACION", nom_c, cel_c, asig)
                    else: st.warning("Faltan datos del cliente")
            
            if st.button("❌ CERRAR / CONSULTAR OTRO"):
                st.session_state.scanner_key += 1
                st.rerun()
        d_opciones(p)
    else: st.error("Producto no encontrado")

# --- 5. TABLA INVENTARIO ---
st.divider()
df = pd.DataFrame(supabase.table("productos").select("*").execute().data)
if not df.empty:
    df['Precio'] = df['precio_venta'].apply(formatear_moneda)
    st.dataframe(df[["nombre", "marca", "stock", "Precio"]], use_container_width=True)