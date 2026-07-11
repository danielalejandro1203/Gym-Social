import json
import streamlit as st
from commons import client_openrouter, client_deepseek, resize_image_for_api

SALVAVIDAS_SYSTEM_PROMPT = """Eres 'Salva Vidas', el especialista en respuestas de emergencia de Gym Social.
Tu misión es sacar del apuro a un hombre que no sabe qué responder en un chat. Recibes los últimos mensajes de la conversación y el tono deseado por el usuario.
Genera UNA SOLA RESPUESTA corta, natural y efectiva, lista para copiar y pegar.
No des explicaciones, ni alternativas, ni diagnósticos. Solo la respuesta.
Usa un lenguaje natural, sin signos de puntuación excesivos. Como hablaría un amigo.
Adapta el tono exactamente a lo que pide el usuario (Divertido, Gracioso, Provocativo, Empático).
Devuelve SOLO la respuesta, sin comillas, sin markdown, sin nada más."""

def extraer_contexto_salvavidas(image):
    """Extrae los últimos mensajes de una captura con Qwen3-VL."""
    image_data = resize_image_for_api(image)
    prompt = """Observa atentamente esta captura de pantalla de un chat (WhatsApp, Instagram, Tinder...). Tu tarea es extraer ÚNICA Y EXCLUSIVAMENTE los últimos 3 o 4 mensajes de la conversación real.

Reglas estrictas:
- Ignora por completo cualquier sticker, emoji grande, foto, vídeo, reacciones, avisos del sistema ("en línea", "escribiendo", fechas, horas, etc.).
- No incluyas nombres de usuario, cabeceras ni pies de la interfaz.
- "TÚ" es la persona que usa burbujas VERDES (o que están alineadas a la DERECHA).
- "ELLA" es la persona que usa burbujas BLANCAS/GRISES (o que están alineadas a la IZQUIERDA).
- Si un mensaje tiene varias líneas, únelas en un solo texto.
- Devuelve EXACTAMENTE un array JSON con el formato [{"sender":"TÚ","message":"..."},{"sender":"ELLA","message":"..."}].
- No inventes mensajes. Si no ves mensajes claros, devuelve un array vacío.
- Solo el JSON, sin markdown ni texto adicional."""

    response = client_openrouter.chat.completions.create(
        model="qwen/qwen3-vl-32b-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        }],
        temperature=0,
        max_tokens=300
    )
    resultado = response.choices[0].message.content.strip()
    if resultado.startswith("```json"): resultado = resultado[7:]
    elif resultado.startswith("```"): resultado = resultado[3:]
    if resultado.endswith("```"): resultado = resultado[:-3]
    return json.loads(resultado.strip())

def generar_respuesta_salvavidas(mensajes, tono="", temperatura=0.9):
    """Genera la respuesta de emergencia con DeepSeek."""
    contexto_texto = "\n".join([f"{'TÚ' if m['sender']=='TÚ' else 'ELLA'}: {m['message']}" for m in mensajes])
    tono_texto = f"Tono deseado: {tono}" if tono else "Tono natural y simpático"
    mensaje_usuario = f"Conversación:\n{contexto_texto}\n\n{tono_texto}"

    response = client_deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SALVAVIDAS_SYSTEM_PROMPT},
            {"role": "user", "content": mensaje_usuario}
        ],
        temperature=temperatura,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()