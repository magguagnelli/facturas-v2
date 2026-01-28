from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from catalogos import router as catalogos_router
from cfdi import router as cfdi_router

app = FastAPI(title="Sistema CFDI")

app.include_router(catalogos_router)
app.include_router(cfdi_router)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Sistema CFDI</title>
</head>
<body>
<h1>Sistema CFDI</h1>

<h2>1. Subir catálogos</h2>
<input type="file" id="file_catalogos" multiple>
<button onclick="subirCatalogos()">Subir</button>
<div id="resultado_catalogos"></div>

<hr>

<h2>2. Subir CFDI</h2>
<input type="file" id="file_cfdi" disabled>
<button id="btn_cfdi" onclick="subirCfdi()" disabled>Procesar</button>
<div id="resultado_cfdi"></div>

<script>
async function subirCatalogos() {
    const input = document.getElementById("file_catalogos");
    if (!input.files.length) return alert("Selecciona archivos");

    const fd = new FormData();
    for (const f of input.files) fd.append("files", f);

    const r = await fetch("/catalogos/subir", { method: "POST", body: fd });
    document.getElementById("resultado_catalogos").innerHTML = await r.text();

    document.getElementById("file_cfdi").disabled = false;
    document.getElementById("btn_cfdi").disabled = false;
}

async function subirCfdi() {
    const input = document.getElementById("file_cfdi");
    if (!input.files.length) return alert("Selecciona XML");

    const fd = new FormData();
    fd.append("file", input.files[0]);

    const r = await fetch("/cfdi/procesar", { method: "POST", body: fd });
    document.getElementById("resultado_cfdi").innerHTML = await r.text();

    conectarContrato();
}

function conectarContrato() {
    const select = document.getElementById("select_contrato");
    if (!select) return;

    select.addEventListener("change", async function () {
        const contrato = this.value;
        if (!contrato) return;

        const r = await fetch(`/cfdi/partidas/${contrato}`);
        document.getElementById("div_partidas").innerHTML = await r.text();
    });
}
</script>
</body>
</html>
"""
