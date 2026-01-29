from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO
import psycopg2
import unicodedata
import os
from typing import List

router = APIRouter(prefix="/catalogos")

HOJAS_REQUERIDAS = {
    "Área": ["Area", "Descripcion","Aux1"],
    "Proveedor": ["RFC", "Razon Social", "Tipo de persona", "Telefono", "Correo elecgtrónico", "Estatus"],
    "Contrato": ["No. De contrato","Descripcion","Ejercicio Fiscal","mes","Estatus general","monto total","Monto Maximo","Monto minimo","Activo","Area","RFC Proveedor"],
    "Partida": ["No. De contrato", "Clave Partida", "Descripcion corta", "Monto asignado", "RFC Proveedor"]
}

conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    port=5432
)

# --------------------------------------------------
# NORMALIZAR TEXTO (MAYÚSCULAS + SIN ACENTOS)
# --------------------------------------------------
def normalizar_texto(valor):
    if valor is None:
        return None
    valor = str(valor).strip()
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    return valor.upper()


@router.get("/", response_class=HTMLResponse)
async def home():
    return """
    <h1>Sube tus archivos Excel de catálogo</h1>
    <input type="file" id="file_input" multiple>
    <button onclick="subirArchivo()">Subir</button>
    <div id="resultado"></div>

    <script>
    async function subirArchivo() {
        const input = document.getElementById('file_input');
        if(!input.files.length){ alert("Selecciona al menos un archivo"); return; }

        const fd = new FormData();
        for(const f of input.files){
            fd.append("files", f);  // <-- nombre "files" coincide con FastAPI
        }

        const r = await fetch("/catalogos/subir", {method:"POST", body: fd});
        document.getElementById("resultado").innerHTML = await r.text();
    }
    </script>
    """


# --------------------------------------------------
# ENDPOINT PARA SUBIR MÚLTIPLES EXCEL
# --------------------------------------------------
@router.post("/subir", response_class=HTMLResponse)
async def subir(files: List[UploadFile] = File(...)):
    resultados_finales = []

    for file in files:
        try:
            content = await file.read()
            xls = pd.ExcelFile(BytesIO(content))
            hojas = xls.sheet_names

            # --------------------------------------------------
            # VALIDACIÓN DE HOJAS Y COLUMNAS
            # --------------------------------------------------
            errores = []
            for hoja in HOJAS_REQUERIDAS:
                if hoja not in hojas:
                    errores.append(f"Falta la hoja obligatoria: '{hoja}'")
                    continue

                df = pd.read_excel(xls, hoja)
                columnas_reales = list(df.columns)
                columnas_esperadas = HOJAS_REQUERIDAS[hoja]

                faltantes = [c for c in columnas_esperadas if c not in columnas_reales]
                extras = [c for c in columnas_reales if c not in columnas_esperadas]

                if faltantes or extras:
                    errores.append(
                        f"Hoja '{hoja}' tiene diferencias:\n"
                        f"  Columnas esperadas: {', '.join(columnas_esperadas)}\n"
                        f"  Columnas reales: {', '.join(columnas_reales)}\n"
                        f"  Faltantes: {', '.join(faltantes) if faltantes else 'ninguna'}\n"
                        f"  Extras: {', '.join(extras) if extras else 'ninguna'}"
                    )

            if errores:
                resultados_finales.append(
                    f"<h3 style='color:red;'>Archivo: {file.filename} - Errores</h3><ul>"
                    + "".join([f"<li><pre>{e}</pre></li>" for e in errores])
                    + "</ul>"
                )
                continue  # pasar al siguiente archivo

            # --------------------------------------------------
            # CONEXIÓN A LA DB
            # --------------------------------------------------
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            resultados = []

            # --------------------------------------------------
            # INSERT ÁREA
            # --------------------------------------------------
            df_area = pd.read_excel(xls, "Área")
            insertados_area = 0
            omitidos_area = 0

            for _, r in df_area.iterrows():
                area = normalizar_texto(r["Area"])
                descripcion = normalizar_texto(r["Descripcion"])
                aux = normalizar_texto(r["Aux1"])

                cur.execute("""
                    SELECT 1 FROM facturas.area
                    WHERE area=%s AND descripcion_area=%s LIMIT 1
                """, (area, descripcion))

                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO facturas.area (area, descripcion_area, aux1)
                        VALUES (%s, %s, %s)
                    """, (area, descripcion, aux))
                    insertados_area += 1
                else:
                    omitidos_area += 1

            resultados.append(f"<b>Área:</b> Insertados={insertados_area}, Omitidos={omitidos_area}")

            # --------------------------------------------------
            # INSERT PROVEEDORES
            # --------------------------------------------------
            df_prov = pd.read_excel(xls, "Proveedor")
            insertados_prov = 0
            omitidos_prov = 0

            for _, r in df_prov.iterrows():
                rfc = normalizar_texto(r["RFC"])
                razon = normalizar_texto(r["Razon Social"])
                tipo = normalizar_texto(r["Tipo de persona"])
                telefono = normalizar_texto(r.get("Telefono"))
                email = normalizar_texto(r.get("Correo elecgtrónico"))
                estatus = normalizar_texto(r.get("Estatus"))

                cur.execute("SELECT 1 FROM facturas.proveedores WHERE rfc=%s LIMIT 1", (rfc,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO facturas.proveedores
                        (rfc, razon_social, tipo_persona, telefono, email, estatus)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """, (rfc, razon, tipo, telefono, email, estatus))
                    insertados_prov += 1
                else:
                    omitidos_prov += 1

            resultados.append(f"<b>Proveedor:</b> Insertados={insertados_prov}, Omitidos={omitidos_prov}")

            # --------------------------------------------------
            # INSERT CONTRATO
            # --------------------------------------------------
            df_contrato = pd.read_excel(xls, "Contrato")
            insertados_contrato = 0
            omitidos_contrato = 0

            for _, r in df_contrato.iterrows():
                numero_contrato = normalizar_texto(r["No. De contrato"])
                descripcion = normalizar_texto(r.get("Descripcion"))
                ejercicio = int(r["Ejercicio Fiscal"])
                mes = normalizar_texto(r["mes"])
                estatus = normalizar_texto(r["Estatus general"])
                monto_total = r.get("monto total", 0)
                monto_maximo = r.get("Monto Maximo", 0)
                activo = r.get("Activo", 0)
                area_txt = normalizar_texto(r["Area"])
                rfc_principal = normalizar_texto(r["RFC Proveedor"])

                # Obtener id_area
                cur.execute("SELECT id_area FROM facturas.area WHERE area=%s LIMIT 1", (area_txt,))
                area_row = cur.fetchone()
                if not area_row:
                    raise Exception(f"Área no encontrada: {area_txt}")
                id_area = area_row[0]

                cur.execute("SELECT 1 FROM facturas.contratos WHERE numero_contrato=%s LIMIT 1", (numero_contrato,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO facturas.contratos
                        (numero_contrato, descripcion, ejercicio_fiscal, mes, estatus_general,
                        monto_total, monto_ejercido, activo, id_area, rfc_proov_principal)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (numero_contrato, descripcion, ejercicio, mes, estatus,
                          monto_total, monto_maximo, activo, id_area, rfc_principal))
                    insertados_contrato += 1
                else:
                    omitidos_contrato += 1

            resultados.append(f"<b>Contrato:</b> Insertados={insertados_contrato}, Omitidos={omitidos_contrato}")

            # --------------------------------------------------
            # INSERT PARTIDA
            # --------------------------------------------------
            df_partida = pd.read_excel(xls, "Partida")
            insertados_partida = 0
            omitidos_partida = 0

            for _, r in df_partida.iterrows():
                numero_contrato = normalizar_texto(r["No. De contrato"])
                clave_partida = normalizar_texto(r["Clave Partida"])
                desc_corta = normalizar_texto(r.get("Descripcion corta"))
                monto = r.get("Monto asignado", 0)
                rfc_prov = normalizar_texto(r["RFC Proveedor"])

                cur.execute("""
                    SELECT 1 FROM facturas.partida
                    WHERE numero_contrato=%s AND cve_partida=%s LIMIT 1
                """, (numero_contrato, clave_partida))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO facturas.partida
                        (numero_contrato, cve_partida, desc_corta, monto_asignado, rfc_emisor)
                        VALUES (%s,%s,%s,%s,%s)
                    """, (numero_contrato, clave_partida, desc_corta, monto, rfc_prov))
                    insertados_partida += 1
                else:
                    omitidos_partida += 1

            resultados.append(f"<b>Partida:</b> Insertados={insertados_partida}, Omitidos={omitidos_partida}")

            conn.commit()
            cur.close()
            conn.close()

            resultados_finales.append(
                f"<h3 style='color:green;'>Archivo: {file.filename} procesado correctamente</h3>"
                + "<p>" + "<br>".join(resultados) + "</p>"
            )

        except Exception as e:
            resultados_finales.append(f"<h3 style='color:red;'>Archivo: {file.filename} - Error: {e}</h3>")

    return HTMLResponse("<h2>Resultados:</h2>" + "".join(resultados_finales))