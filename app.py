import streamlit as st
import os
import json
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Clientes
client_openrouter = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
client_deepseek = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ------------------------------------------------------------
# PROMPTS DEL MONITOR
# ------------------------------------------------------------
MONITOR_SYSTEM_PROMPT = """Eres 'El Monitor', el entrenador estrella de Gym Social. Analizas conversaciones y entregas un diagnóstico táctico-psicológico con el tono directo, motivador y coqueto de un coach de gimnasio. Hablas como un hermano mayor que entrena contigo.

## REGLA DE ORO (LEE ESTO PRIMERO)
- El JSON que recibes ya tiene los mensajes etiquetados. "TÚ" es SIEMPRE el usuario (el que te consulta). "ELLA" es SIEMPRE la otra persona.
- No deduzcas roles por el contenido, solo usa las etiquetas.
- Si el usuario añade un contexto adicional, úsalo para personalizar tu análisis y tus respuestas.

## TU ANÁLISIS DEBE INCLUIR (formato JSON):
1. **pulse_line**: Array de 10 números (1-100) que muestren el nivel de interés de "ELLA". 1 = nulo, 100 = muy alto.
2. **diagnosis**: Objeto con:
   - "title": Título breve y descriptivo.
   - "description": Explicación concisa (máximo 3 frases).
   - "peso": "Ligero", "Medio", "Pesado" o "Legendario".
   - "emoji": Emoji representativo.
3. **routine**: Objeto con:
   - "que_evitar": Error detectado en "TÚ".
   - "que_hacer": Técnica correcta.
   - "respuestas": Array con 3 opciones (estilo, texto, porque).
4. **puntaje_global**: 1-100.

## REGLAS INQUEBRANTABLES:
- NUNCA manipulación, negging o desinterés fingido.
- Explica el "por qué" psicológico.
- Tono cálido, motivador y con humor ligero. Español de Venezuela natural.
- Las 3 respuestas deben ser para "TÚ".

Devuelve SOLO un JSON válido, sin markdown."""

# ------------------------------------------------------------
# PROMPTS DEL ICEBREAKER
# ------------------------------------------------------------
ICEBREAKER_SYSTEM_PROMPT = """Eres 'El Icebreaker', el maestro del primer mensaje en Gym Social. Tu misión es ayudar a hombres a crear líneas de apertura irresistibles, con chispa, respeto y un toque de seducción elegante.

## TU OBJETIVO
Generar EXACTAMENTE 5 líneas de apertura personalizadas, breves y magnéticas, basadas en el perfil y el contexto proporcionado.

## LAS 5 LÍNEAS (UNA DE CADA TIPO)
1. **Divertida**: Ingeniosa, ocurrente, que saque una sonrisa genuina.
2. **Observación Encantadora**: Una lectura sutil de su personalidad o estilo, que demuestre que la has visto de verdad. Cómplice y cálida.
3. **Pregunta con Gancho**: Una pregunta abierta y curiosa que sea irresistible de responder. Nada de entrevistas aburridas.
4. **Cumplido No Físico**: Halago breve y genuino sobre su energía, creatividad, gusto musical o elección de palabras. Nada de cuerpos.
5. **Wildcard (Comodín)**: La línea más audaz pero elegante. Una afirmación segura, un desafío juguetón o un juego de roles sutil.

## REGLAS DE ESTILO (CRÍTICAS)
- Cada línea debe ser CORTA: máximo 2 frases. El impacto está en la brevedad.
- Tono COQUETO y ENCANTADOR, como un galán moderno: cálido, seguro, divertido pero no payaso.
- NUNCA uses piropos vulgares, lenguaje soez, ni emoticones empalagosos.
- Español de Venezuela con naturalidad: "chamo", "chévere", "mano".
- Usa la información del contexto extra como oro para personalizar.

## FORMATO DE RESPUESTA (JSON)
{
  "perfil_resumen": "Breve descripción de su vibe en 2-3 frases",
  "lineas": [
    {"tipo": "divertida", "texto": "...", "porque": "Por qué funciona este humor"},
    {"tipo": "observacion_encantadora", "texto": "...", "porque": "Por qué esta lectura sutil es magnética"},
    {"tipo": "pregunta_con_gancho", "texto": "...", "porque": "Por qué esta pregunta engancha"},
    {"tipo": "cumplido_no_fisico", "texto": "...", "porque": "Por qué este halago es poderoso"},
    {"tipo": "wildcard", "texto": "...", "porque": "Por qué este movimiento es audaz y atractivo"}
  ]
}
Devuelve SOLO el JSON. Sin texto adicional."""

# ------------------------------------------------------------
# FUNCIONES COMUNES
# ------------------------------------------------------------
def resize_image_for_api(img: Image.Image, max_width=512):
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# ------------------------------------------------------------
# FUNCIONES DEL MONITOR
# ------------------------------------------------------------
def extraer_chat_qwen(image: Image.Image):
    image_data = resize_image_for_api(image)
    prompt = """Analiza esta captura de WhatsApp/Instagram. Extrae CADA BURBUJA DE CHAT como un mensaje individual, en orden cronológico.
- Cada burbuja es un mensaje separado, aunque haya varias seguidas del mismo color.
- NO fusiones mensajes consecutivos aunque sean de la misma persona.
- Ignora nombres de perfil, biografías, fechas, horas y cualquier texto de la interfaz.
- "TÚ" = burbujas VERDES (derecha).
- "ELLA" = burbujas BLANCAS/GRISES (izquierda).
- Si un mensaje ocupa varias líneas, únelas en un solo texto.
Devuelve SOLO un array JSON: [{"sender":"TÚ","message":"..."},{"sender":"ELLA","message":"..."}]"""

    response = client_openrouter.chat.completions.create(
        model="qwen/qwen3-vl-32b-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        }],
        temperature=0, max_tokens=600
    )
    resultado = response.choices[0].message.content.strip()
    if resultado.startswith("```json"): resultado = resultado[7:]
    elif resultado.startswith("```"): resultado = resultado[3:]
    if resultado.endswith("```"): resultado = resultado[:-3]
    return json.loads(resultado.strip())

def eliminar_replies(conversacion):
    if not conversacion: return conversacion
    resultado = list(conversacion)
    indices = set()
    for i, msg in enumerate(resultado):
        texto_i = msg["message"].strip()
        sender_i = msg["sender"]
        for j in range(i):
            prev = resultado[j]
            if prev["message"].strip() == texto_i and prev["sender"] != sender_i:
                if i+1 < len(resultado) and resultado[i+1]["sender"] == sender_i: indices.add(i)
                elif i > 0 and resultado[i-1]["sender"] == sender_i: indices.add(i)
                elif i == len(resultado)-1: indices.add(i)
                break
        for j in range(max(0, i-4), i):
            prev = resultado[j]
            if prev["message"].strip() == texto_i and prev["sender"] == sender_i:
                indices.add(i)
                break
    for i in sorted(indices, reverse=True): del resultado[i]
    return resultado

def analizar_con_deepseek(conversacion, contexto="", temperatura=0.8):
    conversacion_texto = json.dumps(conversacion, ensure_ascii=False, indent=2)
    mensaje_usuario = f"Analiza esta conversación:\n\n{conversacion_texto}"
    if contexto: mensaje_usuario += f"\n\nContexto adicional del usuario: {contexto}"
    response = client_deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": MONITOR_SYSTEM_PROMPT}, {"role": "user", "content": mensaje_usuario}],
        temperature=temperatura, max_tokens=2500
    )
    resultado = response.choices[0].message.content.strip()
    if resultado.startswith("```json"): resultado = resultado[7:]
    elif resultado.startswith("```"): resultado = resultado[3:]
    if resultado.endswith("```"): resultado = resultado[:-3]
    return json.loads(resultado)

# ------------------------------------------------------------
# FUNCIONES DEL ICEBREAKER
# ------------------------------------------------------------
def extraer_perfil_qwen(image: Image.Image):
    image_data = resize_image_for_api(image)
    prompt = """Analiza esta captura de un perfil de Instagram (o similar). Describe en detalle todo lo que veas:
- Nombre de la persona (si aparece).
- Biografía (texto completo, sin inventar).
- Intereses o aficiones que se deduzcan de la bio o de las fotos.
- Estilo visual (colores, tipo de fotos, si es artística, fitness, fiestera, etc.).
- Cualquier otro detalle relevante de las historias destacadas, publicaciones o emojis.
Escribe la descripción en un solo texto plano, sin formato JSON, para que un sistema de IA pueda generar líneas de apertura personalizadas."""

    response = client_openrouter.chat.completions.create(
        model="qwen/qwen3-vl-32b-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        }],
        temperature=0, max_tokens=600
    )
    return response.choices[0].message.content.strip()

def generar_icebreakers(descripcion_perfil, contexto_extra="", temperatura=0.95):
    base_info = f"Descripción del perfil:\n{descripcion_perfil}" if descripcion_perfil else "El perfil no tiene texto descriptivo."
    if contexto_extra:
        mensaje_usuario = f"{base_info}\n\nInfo extra del usuario:\n{contexto_extra}"
    else:
        mensaje_usuario = f"{base_info}\n\n(Sin contexto extra. Sé creativo.)"

    response = client_deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": ICEBREAKER_SYSTEM_PROMPT}, {"role": "user", "content": mensaje_usuario}],
        temperature=temperatura, max_tokens=1500
    )
    resultado = response.choices[0].message.content.strip()
    if resultado.startswith("```json"): resultado = resultado[7:]
    elif resultado.startswith("```"): resultado = resultado[3:]
    if resultado.endswith("```"): resultado = resultado[:-3]
    return json.loads(resultado)

# ------------------------------------------------------------
# INTERFAZ PRINCIPAL CON NAVEGACIÓN LATERAL
# ------------------------------------------------------------
st.set_page_config(page_title="Gym Social", page_icon="🏋️", layout="wide")
st.sidebar.title("🏋️ Gym Social")
modo = st.sidebar.radio("Elige una herramienta:", ["📊 Monitor de Chats", "🧊 Icebreaker"])

# ------------------------------------------------------------
# MODO MONITOR
# ------------------------------------------------------------
if modo == "📊 Monitor de Chats":
    st.title("🏋️ Gym Social – El Monitor")
    st.caption("Sube una captura de chat y recibe tu diagnóstico al instante")

    # Inicializar estado de sesión del Monitor
    if 'conv_monitor' not in st.session_state:
        st.session_state.conv_monitor = None
    if 'extraccion_monitor' not in st.session_state:
        st.session_state.extraccion_monitor = False
    if 'diagnostico_actual' not in st.session_state:
        st.session_state.diagnostico_actual = None
    if 'temp_actual' not in st.session_state:
        st.session_state.temp_actual = 0.8

    uploaded = st.file_uploader("Selecciona una captura de WhatsApp/Instagram", type=["png","jpg","jpeg"], key="monitor_upload")
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, caption="Vista previa", width=400)
        if st.button("🔍 Analizar conversación"):
            with st.spinner("Extrayendo mensajes..."):
                crudos = extraer_chat_qwen(image)
                conversacion = eliminar_replies(crudos)
                st.session_state.conv_monitor = conversacion
                st.session_state.extraccion_monitor = True
                st.session_state.diagnostico_actual = None  # Resetear diagnóstico anterior
                st.session_state.temp_actual = 0.8

        if st.session_state.extraccion_monitor:
            conv = st.session_state.conv_monitor
            st.success(f"✅ {len(conv)} mensajes extraídos")
            st.subheader("📋 Conversación detectada")
            for msg in conv:
                quien = "TÚ" if msg['sender'] == 'TÚ' else "ELLA"
                st.write(f"**{quien}:** {msg['message']}")

            if st.checkbox("¿La extracción es correcta?"):
                contexto = st.text_area("Contexto extra (opcional)", placeholder="Ej: quiero invitarla a salir...")

                # Botón para ejecutar (o regenerar) diagnóstico
                boton_texto = "🔄 Obtener otro diagnóstico" if st.session_state.diagnostico_actual else "🧠 Ejecutar diagnóstico"
                if st.button(boton_texto):
                    # Si ya hay un diagnóstico previo, subimos la temperatura
                    if st.session_state.diagnostico_actual:
                        st.session_state.temp_actual = min(st.session_state.temp_actual + 0.05, 1.2)
                    with st.spinner(f"Analizando (temperatura: {st.session_state.temp_actual:.2f})..."):
                        analisis = analizar_con_deepseek(conv, contexto, temperatura=st.session_state.temp_actual)
                        st.session_state.diagnostico_actual = analisis

                # Mostrar diagnóstico si existe
                if st.session_state.diagnostico_actual:
                    analisis = st.session_state.diagnostico_actual
                    if st.session_state.temp_actual == 0.8:
                        st.subheader(f"🎯 {analisis['diagnosis']['title']}")
                    else:
                        st.subheader(f"🎯 NUEVO DIAGNÓSTICO 😎 {analisis['diagnosis']['title']}")
                    st.metric("Puntaje Global", f"{analisis['puntaje_global']}/100")

                    # Peso del caso
                    pesos_iconos = {"Ligero": "🪶", "Medio": "🏋️", "Pesado": "🏋️‍♂️", "Legendario": "🏆"}
                    peso = analisis['diagnosis'].get('peso', 'Medio')
                    icono = pesos_iconos.get(peso, "🏋️")
                    st.markdown(f"**{icono} Peso del caso:** {peso} {analisis['diagnosis'].get('emoji', '')}")

                    # Descripción
                    st.write(analisis['diagnosis']['description'])

                    # Electrocardiograma social (como en consola)
                    pulse = analisis.get('pulse_line', [])
                    if pulse:
                        barra = "".join(["█" if p > 50 else "▒" if p > 25 else "░" for p in pulse])
                        st.subheader("📈 Electrocardiograma Social")
                        st.code(barra, language=None)
                        st.caption(f"Inicio: {pulse[0]} → Final: {pulse[-1]}")

                    # Rutina de entrenamiento
                    routine = analisis.get('routine', {})
                    if routine:
                        st.subheader("🏋️ Rutina de entrenamiento")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.error(f"❌ Evita: {routine.get('que_evitar', '')}")
                        with col2:
                            st.success(f"✅ Haz: {routine.get('que_hacer', '')}")

                        # Opciones de respuesta
                        st.subheader("💬 Opciones de respuesta")
                        for i, r in enumerate(routine.get('respuestas', []), 1):
                            with st.expander(f"{i}. [{r.get('estilo', 'General')}] {r.get('texto', '')}"):
                                st.write(f"💡 {r.get('porque', '')}")
            else:
                st.warning("Corrige la extracción antes de continuar.")

# ------------------------------------------------------------
# MODO ICEBREAKER
# ------------------------------------------------------------
if modo == "🧊 Icebreaker":
    st.title("🧊 Gym Social – El Icebreaker")
    st.caption("Sube una captura de un perfil y recibe líneas de apertura irresistibles")

    if 'descripcion_perfil' not in st.session_state:
        st.session_state.descripcion_perfil = None
        st.session_state.perfil_analizado = False

    uploaded = st.file_uploader("Selecciona una captura de perfil (Instagram, Tinder...)", type=["png","jpg","jpeg"], key="icebreaker_upload")
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, caption="Vista previa del perfil", width=400)
        if st.button("👁️ Analizar perfil"):
            with st.spinner("Analizando perfil con IA multimodal..."):
                desc = extraer_perfil_qwen(image)
                st.session_state.descripcion_perfil = desc
                st.session_state.perfil_analizado = True

        if st.session_state.perfil_analizado:
            st.success("✅ Perfil analizado")
            st.subheader("📄 Descripción extraída")
            st.write(st.session_state.descripcion_perfil[:500] + "..." if len(st.session_state.descripcion_perfil) > 500 else st.session_state.descripcion_perfil)

            contexto = st.text_area("Datos extra (opcional)", placeholder="¿Hobbies, trabajo, algo que sepas de ella?", key="ice_contexto")
            temp = st.slider("Creatividad", 0.7, 1.3, 0.95, 0.05)

            if st.button("🧊 Generar líneas de apertura"):
                with st.spinner("Generando icebreakers..."):
                    ice = generar_icebreakers(st.session_state.descripcion_perfil, contexto, temp)
                st.subheader(f"👤 Vibe: {ice.get('perfil_resumen', '')}")
                for i, linea in enumerate(ice.get('lineas', []), 1):
                    emojis = {"divertida":"😂","observacion_encantadora":"✨","pregunta_con_gancho":"❓","cumplido_no_fisico":"🎯","wildcard":"🧲"}
                    emoji = emojis.get(linea['tipo'], "💬")
                    with st.expander(f"{i}. {emoji} [{linea['tipo'].upper().replace('_',' ')}] {linea['texto']}"):
                        st.write(f"💡 {linea['porque']}")