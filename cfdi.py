from fastapi import APIRouter, UploadFile
from fastapi.responses import HTMLResponse
from lxml import etree
import psycopg2
import os

router = APIRouter(prefix="/cfdi")

DB_CONFIG = psycopg2.connect(
    host=os.environ["DB_HOST"],
    dbname=os.environ["DB_NAME"],
    port=os.environ.get("DB_PORT"),
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
)

# --------------------------------------------------
# XML → dict limpio
# --------------------------------------------------
def xml_to_dict_clean(element):
    tag = etree.QName(element).localname
    data = {}

    if element.attrib:
        data.update(element.attrib)

    if len(element) == 0:
        return element.text or data

    for child in element:
        child_tag = etree.QName(child).localname
        child_data = xml_to_dict_clean(child)

        if child_tag in data:
            if not isinstance(data[child_tag], list):
                data[child_tag] = [data[child_tag]]
            data[child_tag].append(child_data)
        else:
            data[child_tag] = child_data

    return {tag: data}

# --------------------------------------------------
# DB helpers
# --------------------------------------------------
def rfc_existe_en_catalogo(rfc: str):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM facturas.proveedores WHERE rfc=%s LIMIT 1",
        (rfc,)
    )
    existe = cur.fetchone() is not None
    cur.close()
    conn.close()
    return existe


def obtener_contratos_por_rfc(rfc: str):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT numero_contrato
        FROM facturas.partida
        WHERE rfc_emisor = %s
    """, (rfc,))
    contratos = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return contratos


def obtener_partidas_por_contrato(contrato: str):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT cve_partida, desc_corta
        FROM facturas.partida
        WHERE numero_contrato = %s
    """, (contrato,))
    partidas = cur.fetchall()
    cur.close()
    conn.close()
    return partidas

# --------------------------------------------------
# PROCESAR CFDI
# --------------------------------------------------
@router.post("/procesar", response_class=HTMLResponse)
async def procesar(file: UploadFile):
    xml_content = await file.read()

    try:
        xml_doc = etree.fromstring(xml_content)
    except:
        return HTMLResponse("❌ XML inválido", status_code=400)

    xml_dict = xml_to_dict_clean(xml_doc)
    comprobante = xml_dict.get("Comprobante", {})
    emisor = comprobante.get("Emisor", {})
    rfc_emisor = emisor.get("Rfc")

    if not rfc_emisor:
        return HTMLResponse("❌ RFC no encontrado", status_code=400)

    if not rfc_existe_en_catalogo(rfc_emisor):
        return HTMLResponse(
            f"❌ RFC <b>{rfc_emisor}</b> no existe en catálogo",
            status_code=400
        )

    contratos = obtener_contratos_por_rfc(rfc_emisor)
    if not contratos:
        return HTMLResponse("❌ No hay contratos asociados", status_code=400)

    opciones = "".join(
        f"<option value='{c}'>{c}</option>" for c in contratos
    )

    return HTMLResponse(f"""
        ✅ CFDI válido<br>
        ✅ RFC {rfc_emisor}<br><br>

        <b>Contrato:</b><br>
        <select id="select_contrato">
            <option value="">-- Selecciona --</option>
            {opciones}
        </select>

        <div id="div_partidas"></div>
    """)

# --------------------------------------------------
# PARTIDAS
# --------------------------------------------------
@router.get("/partidas/{contrato}", response_class=HTMLResponse)
async def partidas_por_contrato(contrato: str):
    partidas = obtener_partidas_por_contrato(contrato)

    if not partidas:
        return "<p style='color:red;'>No hay partidas</p>"

    opciones = "".join(
        f"<option value='{p[0]}'>{p[0]} - {p[1]}</option>"
        for p in partidas
    )

    return f"""
        <br>
        <b>Partida:</b><br>
        <select id="select_partida">
            <option value="">-- Selecciona --</option>
            {opciones}
        </select>
    """
