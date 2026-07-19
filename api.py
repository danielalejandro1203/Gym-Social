from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from PIL import Image
from io import BytesIO
from typing import Optional
import json as json_lib

# Tus módulos de IA
from monitor import extraer_chat_qwen, eliminar_replies, analizar_con_deepseek
from icebreaker import extraer_perfil_qwen, generar_icebreakers
from sparring import SPARRING_PERSONALITIES, evaluar_mensaje, responder_ia, resumen_final
from espejo import analizar_imagen_perfil, generar_auditoria
from salvavidas import extraer_contexto_salvavidas, generar_respuesta_salvavidas

# Autenticación y base de datos
from auth import router as auth_router
from db import supabase
from dependencies import get_current_user, check_usage_limit

app = FastAPI(title="Gym Social API", version="1.0")

# Incluir el router de autenticación (registro y login)
app.include_router(auth_router)

# ================================================================
# PILAR 1: MONITOR DE CHATS
# ================================================================
@app.post("/api/monitor")
async def monitor_endpoint(
    file: UploadFile = File(...),
    contexto: Optional[str] = Form(None),
    temperatura: float = Form(0.9),
    user: dict = Depends(get_current_user),
    _: None = Depends(check_usage_limit("monitor"))
):
    image_bytes = await file.read()
    image = Image.open(BytesIO(image_bytes))

    crudos = extraer_chat_qwen(image)
    conversacion = eliminar_replies(crudos)

    analisis = analizar_con_deepseek(conversacion, contexto=contexto or "", temperatura=temperatura)
    if analisis is None:
        return JSONResponse(content={"error": "No se pudo generar el diagnóstico"}, status_code=500)

    # Registrar el uso en la base de datos
    supabase.table("analyses").insert({
        "user_id": user.id,
        "tool": "monitor",
        "tokens_used": 0
    }).execute()

    return analisis

# ================================================================
# PILAR 1: ICEBREAKER
# ================================================================
@app.post("/api/icebreaker")
async def icebreaker_endpoint(
    file: UploadFile = File(...),
    contexto: Optional[str] = Form(None),
    temperatura: float = Form(0.95),
    user: dict = Depends(get_current_user),
    _: None = Depends(check_usage_limit("icebreaker"))
):
    image_bytes = await file.read()
    image = Image.open(BytesIO(image_bytes))

    descripcion = extraer_perfil_qwen(image)
    resultado = generar_icebreakers(descripcion, contexto or "", temperatura)

    supabase.table("analyses").insert({
        "user_id": user.id,
        "tool": "icebreaker",
        "tokens_used": 0
    }).execute()

    return resultado

# ================================================================
# PILAR 2: SPARRING
# ================================================================
@app.post("/api/sparring")
async def sparring_endpoint(
    mensaje: str = Form(...),
    personalidad: str = Form("Divertida"),
    historial_json: str = Form("[]"),
    accion: str = Form("enviar"),
    user: dict = Depends(get_current_user),
    _: None = Depends(check_usage_limit("sparring"))
):
    historial = json_lib.loads(historial_json) if historial_json else []

    if accion == "terminar":
        puntuaciones = [m.get("punt", 0) for m in historial if m.get("punt")]
        resumen = resumen_final(historial, puntuaciones) if puntuaciones else "No hay suficientes datos para un resumen."
        return {"resumen": resumen}

    evaluacion = evaluar_mensaje(historial, mensaje)
    punt = evaluacion["puntuacion"]
    consejo = evaluacion["consejo"]

    historial.append({"role": "user", "content": mensaje, "punt": punt})
    respuesta = responder_ia(historial, personalidad, nivel=0, temperatura=0.7)

    supabase.table("analyses").insert({
        "user_id": user.id,
        "tool": "sparring",
        "tokens_used": 0
    }).execute()

    return {
        "evaluacion": {"puntuacion": punt, "consejo": consejo},
        "respuesta": respuesta,
        "historial": historial
    }

# ================================================================
# PILAR 3: ESPEJO
# ================================================================
@app.post("/api/espejo")
async def espejo_endpoint(
    files: list[UploadFile] = File(...),
    contexto: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
    _: None = Depends(check_usage_limit("espejo"))
):
    descripciones = []
    for file in files[:3]:
        image_bytes = await file.read()
        image = Image.open(BytesIO(image_bytes))
        desc = analizar_imagen_perfil(image)
        descripciones.append(desc)

    auditoria = generar_auditoria(descripciones, contexto or "")

    supabase.table("analyses").insert({
        "user_id": user.id,
        "tool": "espejo",
        "tokens_used": 0
    }).execute()

    return auditoria

# ================================================================
# PILAR 4: SALVA VIDAS
# ================================================================
@app.post("/api/salvavidas")
async def salvavidas_endpoint(
    file: UploadFile = File(...),
    tono: str = Form("natural"),
    temperatura: float = Form(0.9),
    user: dict = Depends(get_current_user),
    _: None = Depends(check_usage_limit("salvavidas"))
):
    image_bytes = await file.read()
    image = Image.open(BytesIO(image_bytes))

    mensajes = extraer_contexto_salvavidas(image)
    respuesta = generar_respuesta_salvavidas(mensajes, tono=tono, temperatura=temperatura)

    supabase.table("analyses").insert({
        "user_id": user.id,
        "tool": "salvavidas",
        "tokens_used": 0
    }).execute()

    return {"respuesta": respuesta}