import streamlit as st
import os
import json
import base64
import re
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
# PROMPTS DEL MONITOR (MÁS HUMANO Y NATURAL)
# ------------------------------------------------------------
MONITOR_SYSTEM_PROMPT = """Eres 'El Monitor', el entrenador de Gym Social. Ayudas a hombres a mejorar sus conversaciones con un tono cercano, cálido y natural, como un amigo que te da un consejo mientras entrenan.

## CÓMO DEBES HABLAR
- Usa un lenguaje sencillo y fluido, sin frases muy largas ni demasiada puntuación. 
- Suena como un hermano mayor que está allí para ayudar, no como un robot o un profesor.
- Evita los signos de interrogación o exclamación excesivos. Una conversación natural no está llena de preguntas retóricas.
- Sé motivador, pero con naturalidad. Un "bien hecho" o "tranquilo, se puede mejorar" vale más que un discurso.
- Olvida las estructuras rígidas. No hace falta que cada frase tenga comas o puntos; a veces un "jaja" o un "mira" sueltos hacen que te sientas más humano.

## REGLA DE ORO
- El JSON que recibes ya tiene los mensajes etiquetados. "TÚ" es SIEMPRE el usuario. "ELLA" es SIEMPRE la otra persona.
- No deduzcas roles por el contenido, solo usa las etiquetas.
- Si el usuario añade un contexto, úsalo para personalizar el análisis.

## FORMATO DE SALIDA (JSON)
{
  "diagnosis": {
    "title": "Un título breve y natural, como lo diría un amigo",
    "description": "Explicación corta y sincera, como un consejo de barra de gimnasio",
    "peso": "Ligero, Medio, Pesado o Legendario",
    "emoji": "un emoji"
  },
  "routine": {
    "que_evitar": "Un error concreto, explicado de forma natural",
    "que_hacer": "La alternativa, dicha con calma y sencillez",
    "respuestas": [
      {
        "estilo": "por ejemplo, 'humor', 'curiosidad', 'cumplido', 'propuesta'",
        "texto": "El mensaje sugerido, corto y natural, sin parecer guionizado",
        "porque": "Razón breve y coloquial de por qué funciona"
      }
      // exactamente 4
    ]
  },
  "puntaje_global": número del 1 al 100
}

## REGLAS INQUEBRANTABLES
- Nada de manipulación ni negging.
- Las 4 respuestas deben ser para "TÚ".
- Sé positivo incluso cuando señales errores.
- Habla en español latino neutro, sin regionalismos forzados.

Devuelve SOLO un JSON válido, sin markdown."""

# ------------------------------------------------------------
# PROMPT DEL ICEBREAKER
# ------------------------------------------------------------
ICEBREAKER_SYSTEM_PROMPT = """Eres 'El Icebreaker', el experto en primeros mensajes de Gym Social. Creas líneas de apertura cortas, coquetas y divertidas.

## TU OBJETIVO
Generar EXACTAMENTE 5 líneas de apertura. Cada línea debe ser UNA SOLA FRASE, máximo 2 frases muy cortas.

## LAS 5 LÍNEAS (UNA DE CADA TIPO)
1. **Divertida**: Humor ingenioso y actual.
2. **Observación Encantadora**: Detalle sutil de su perfil.
3. **Pregunta con Gancho**: Curiosa e irresistible.
4. **Cumplido No Físico**: Sobre su energía o estilo.
5. **Wildcard (Comodín)**: Audaz y desafiante.

## REGLAS DE ESTILO (CRÍTICAS)
- MUY CORTO: cada línea debe ser 1 frase, máximo 2 muy cortas.
- COQUETO y GRACIOSO: tono galán divertido y seguro.
- NUNCA vulgar ni empalagoso.
- Español latino neutro, sin regionalismos.
- SIEMPRE prioriza el contexto extra sobre la descripción del perfil.

## FORMATO DE RESPUESTA (JSON)
{
  "perfil_resumen": "Máximo 1 frase sobre su vibe",
  "lineas": [
    {"tipo": "...", "texto": "...", "porque": "..."},
    ...
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


def normalizar_clave(texto):
    texto = texto.lower()
    texto = re.sub(r'\(.*?\)', '', texto)
    texto = re.sub(r'[^a-záéíóúñü]+', '_', texto)
    texto = re.sub(r'_+', '_', texto)
    return texto.strip('_')


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
    if resultado.startswith("```json"):
        resultado = resultado[7:]
    elif resultado.startswith("```"):
        resultado = resultado[3:]
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
                if i + 1 < len(resultado) and resultado[i + 1]["sender"] == sender_i:
                    indices.add(i)
                elif i > 0 and resultado[i - 1]["sender"] == sender_i:
                    indices.add(i)
                elif i == len(resultado) - 1:
                    indices.add(i)
                break
        for j in range(max(0, i - 4), i):
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

    for intento in range(2):
        response = client_deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": MONITOR_SYSTEM_PROMPT},
                      {"role": "user", "content": mensaje_usuario}],
            temperature=temperatura if intento == 0 else 0,
            max_tokens=2500
        )
        resultado = response.choices[0].message.content.strip()
        if resultado.startswith("```json"):
            resultado = resultado[7:]
        elif resultado.startswith("```"):
            resultado = resultado[3:]
        if resultado.endswith("```"): resultado = resultado[:-3]

        try:
            return json.loads(resultado)
        except json.JSONDecodeError:
            ultimo_cierre = resultado.rfind('}')
            if ultimo_cierre != -1:
                try:
                    return json.loads(resultado[:ultimo_cierre + 1])
                except json.JSONDecodeError:
                    pass
            if intento == 1:
                st.error("❌ El Monitor recibió un formato inválido dos veces. Por favor, inténtalo de nuevo.")
                return None


# ------------------------------------------------------------
# FUNCIONES DEL ICEBREAKER
# ------------------------------------------------------------
def extraer_perfil_qwen(image: Image.Image):
    image_data = resize_image_for_api(image)
    prompt = """Analiza esta captura de perfil de Instagram/Tinder. Describe en MÁXIMO 2 oraciones breves: quién es (nombre si se ve), intereses claros y estilo visual general. Sé conciso. No inventes, solo lo que se aprecie en la imagen."""

    response = client_openrouter.chat.completions.create(
        model="qwen/qwen3-vl-32b-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        }],
        temperature=0, max_tokens=300
    )
    return response.choices[0].message.content.strip()


def generar_icebreakers(descripcion_perfil, contexto_extra="", temperatura=0.95):
    base_info = f"Descripción del perfil:\n{descripcion_perfil}" if descripcion_perfil else "El perfil no tiene texto descriptivo."
    if contexto_extra:
        mensaje_usuario = f"{base_info}\n\nContexto adicional del usuario (PRIORITARIO):\n{contexto_extra}"
    else:
        mensaje_usuario = f"{base_info}\n\n(Sin contexto extra. Sé creativo.)"

    for intento in range(2):
        response = client_deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": ICEBREAKER_SYSTEM_PROMPT},
                      {"role": "user", "content": mensaje_usuario}],
            temperature=temperatura if intento == 0 else 0,
            max_tokens=1000
        )
        resultado = response.choices[0].message.content.strip()
        if resultado.startswith("```json"):
            resultado = resultado[7:]
        elif resultado.startswith("```"):
            resultado = resultado[3:]
        if resultado.endswith("```"): resultado = resultado[:-3]

        try:
            return json.loads(resultado)
        except json.JSONDecodeError:
            ultimo_cierre = resultado.rfind('}')
            if ultimo_cierre != -1:
                try:
                    return json.loads(resultado[:ultimo_cierre + 1])
                except json.JSONDecodeError:
                    pass
            if intento == 1:
                st.error("❌ La IA devolvió un formato inválido dos veces. Intenta de nuevo con otro perfil o contexto.")
                return {"perfil_resumen": "", "lineas": []}


# ------------------------------------------------------------
# BOTÓN DE COPIAR
# ------------------------------------------------------------
def copy_button(text):
    """Botón que copia al portapapeles con feedback visual."""
    escaped = text.replace("`", "\\`").replace("$", "\\$")
    html = f"""
    <button onclick="
        var txt = `{escaped}`;
        if (navigator.clipboard) {{
            navigator.clipboard.writeText(txt).then(function() {{
                this.innerHTML = '✅ Copiado';
                setTimeout(()=>{{ this.innerHTML = '📋 Copiar'; }}, 2000);
            }}.bind(this));
        }} else {{
            var el = document.createElement('textarea');
            el.value = txt;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            this.innerHTML = '✅ Copiado';
            setTimeout(()=>{{ this.innerHTML = '📋 Copiar'; }}, 2000);
        }}
    " style="
        background: linear-gradient(135deg, #FF6B6B, #FF8E8E);
        color: white; border: none; padding: 5px 15px;
        border-radius: 20px; cursor: pointer; font-size: 13px;
        font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.2s;
    ">📋 Copiar</button>
    """
    st.components.v1.html(html, height=40)


# ------------------------------------------------------------
# INTERFAZ PRINCIPAL CON NAVEGACIÓN JERÁRQUICA
# ------------------------------------------------------------
st.set_page_config(page_title="Gym Social", page_icon="🏋️", layout="wide")

st.markdown("""
<style>
    @media (max-width: 600px) {
        .stImage img {
            max-width: 280px !important;
            margin: 0 auto;
        }
    }
    .icebreaker-card {
        border: 1px solid #eee;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        background-color: #fafafa;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🏋️ Gym Social")

pilares_disponibles = {
    "Pilar 1: El Monitor": ["📊 Monitor de Chats", "🧊 Icebreaker"],
    "Pilar 2: El Sparring": ["🚧 Próximamente"],
    "Pilar 3: El Espejo": ["🚧 Próximamente"],
    "Pilar 4: La Arena": ["🚧 Próximamente"]
}

pilar_seleccionado = st.sidebar.selectbox("Selecciona un pilar:", list(pilares_disponibles.keys()))
herramientas = pilares_disponibles[pilar_seleccionado]

if len(herramientas) > 1 or herramientas[0] != "🚧 Próximamente":
    herramienta_seleccionada = st.sidebar.selectbox("Herramienta:", herramientas)
else:
    herramienta_seleccionada = None

if herramienta_seleccionada is None or herramienta_seleccionada == "🚧 Próximamente":
    st.title(f"🏋️ Gym Social – {pilar_seleccionado}")
    st.info("🚧 Este pilar estará disponible próximamente. ¡Estamos trabajando para ti!")
    st.stop()

# ------------------------------------------------------------
# MODO MONITOR (CON BOTÓN GUARDAR CONTEXTO)
# ------------------------------------------------------------
if herramienta_seleccionada == "📊 Monitor de Chats":
    st.title("🏋️ Gym Social – El Monitor")
    st.caption("Sube una captura de chat y recibe tu diagnóstico al instante")

    if 'conv_monitor' not in st.session_state:
        st.session_state.conv_monitor = None
    if 'extraccion_monitor' not in st.session_state:
        st.session_state.extraccion_monitor = False
    if 'diagnostico_actual' not in st.session_state:
        st.session_state.diagnostico_actual = None
    if 'temp_actual' not in st.session_state:
        st.session_state.temp_actual = 0.9
    if 'contexto_monitor' not in st.session_state:
        st.session_state.contexto_monitor = ""

    uploaded = st.file_uploader("Selecciona una captura de WhatsApp/Instagram", type=["png", "jpg", "jpeg"],
                                key="monitor_upload")
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, caption="Vista previa", width=300)
        if st.button("🔍 Analizar conversación"):
            with st.spinner("Extrayendo mensajes..."):
                crudos = extraer_chat_qwen(image)
                conversacion = eliminar_replies(crudos)
                st.session_state.conv_monitor = conversacion
                st.session_state.extraccion_monitor = True
                st.session_state.diagnostico_actual = None
                st.session_state.temp_actual = 0.9
                st.session_state.contexto_monitor = ""

        if st.session_state.extraccion_monitor:
            conv = st.session_state.conv_monitor
            st.success(f"✅ {len(conv)} mensajes extraídos")
            st.subheader("📋 Conversación detectada")
            for msg in conv:
                quien = "TÚ" if msg['sender'] == 'TÚ' else "ELLA"
                st.write(f"**{quien}:** {msg['message']}")

            if st.checkbox("¿La extracción es correcta?"):
                st.text_area("Contexto extra (opcional)", placeholder="Ej: quiero invitarla a salir...",
                             key="contexto_texto")
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("💾 Guardar contexto"):
                        st.session_state.contexto_monitor = st.session_state.contexto_texto
                        st.success("✅ Contexto guardado")
                if st.session_state.contexto_monitor:
                    st.info(f"📝 Contexto: {st.session_state.contexto_monitor}")

                boton_texto = "🔄 Obtener otro diagnóstico" if st.session_state.diagnostico_actual else "🧠 Ejecutar diagnóstico"
                if st.button(boton_texto):
                    if st.session_state.diagnostico_actual:
                        st.session_state.temp_actual = min(st.session_state.temp_actual + 0.05, 1.2)
                    with st.spinner(f"Analizando..."):
                        analisis = analizar_con_deepseek(conv, st.session_state.contexto_monitor,
                                                         temperatura=st.session_state.temp_actual)
                        if analisis is None:
                            st.warning("No se pudo generar el diagnóstico.")
                        else:
                            st.session_state.diagnostico_actual = analisis

                if st.session_state.diagnostico_actual:
                    analisis = st.session_state.diagnostico_actual
                    st.subheader(f"🎯 {analisis['diagnosis']['title']}")
                    st.metric("Puntaje Global", f"{analisis['puntaje_global']}/100")
                    pesos_iconos = {"Ligero": "🪶", "Medio": "🏋️", "Pesado": "🏋️‍♂️", "Legendario": "🏆"}
                    peso = analisis['diagnosis'].get('peso', 'Medio')
                    icono = pesos_iconos.get(peso, "🏋️")
                    st.markdown(f"**{icono} Peso del caso:** {peso} {analisis['diagnosis'].get('emoji', '')}")
                    st.write(analisis['diagnosis']['description'])

                    routine = analisis.get('routine', {})
                    if routine:
                        st.subheader("🏋️ Rutina de entrenamiento")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.error(f"❌ Evita: {routine.get('que_evitar', '')}")
                        with col2:
                            st.success(f"✅ Haz: {routine.get('que_hacer', '')}")

                        st.subheader("💬 Opciones de respuesta")
                        emojis_monitor = {"humor": "😂", "curiosidad": "❓", "cumplido": "🎯", "propuesta": "🧲",
                                          "general": "💬"}
                        for i, r in enumerate(routine.get('respuestas', []), 1):
                            estilo = r.get('estilo', 'General')
                            clave = normalizar_clave(estilo)
                            emoji = emojis_monitor.get(clave, "💬")
                            with st.expander(f"{i}. {emoji} [{estilo}] {r.get('texto', '')}"):
                                st.write(f"💡 {r.get('porque', '')}")
                                copy_button(r.get('texto', ''))
            else:
                st.warning("Corrige la extracción antes de continuar.")

# ------------------------------------------------------------
# MODO ICEBREAKER
# ------------------------------------------------------------
elif herramienta_seleccionada == "🧊 Icebreaker":
    st.title("🧊 Gym Social – El Icebreaker")
    st.caption("Sube una captura de un perfil y recibe líneas de apertura irresistibles")

    if 'descripcion_perfil' not in st.session_state:
        st.session_state.descripcion_perfil = None
        st.session_state.perfil_analizado = False
    if 'contexto_icebreaker' not in st.session_state:
        st.session_state.contexto_icebreaker = ""

    uploaded = st.file_uploader("Selecciona una captura de perfil (Instagram, Tinder...)", type=["png", "jpg", "jpeg"],
                                key="icebreaker_upload")
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, caption="Vista previa del perfil", width=300)
        if st.button("👁️ Analizar perfil"):
            with st.spinner("Analizando perfil con IA multimodal..."):
                desc = extraer_perfil_qwen(image)
                st.session_state.descripcion_perfil = desc
                st.session_state.perfil_analizado = True
                st.session_state.contexto_icebreaker = ""

        if st.session_state.perfil_analizado:
            st.success("✅ Perfil analizado")
            st.subheader("📄 Descripción extraída")
            st.info(st.session_state.descripcion_perfil)

            st.text_area("Datos extra (opcional, pero muy importantes)",
                         placeholder="¿Hobbies, trabajo, algo que sepas de ella?", key="contexto_ice_texto")
            if st.button("💾 Guardar contexto", key="guardar_ice"):
                st.session_state.contexto_icebreaker = st.session_state.contexto_ice_texto
                st.success("✅ Contexto guardado")
            if st.session_state.contexto_icebreaker:
                st.info(f"📝 Contexto: {st.session_state.contexto_icebreaker}")

            temp = st.slider("Creatividad", 0.7, 1.5, 0.95, 0.05)

            if st.button("🧊 Generar líneas de apertura"):
                with st.spinner("Generando icebreakers..."):
                    ice = generar_icebreakers(st.session_state.descripcion_perfil, st.session_state.contexto_icebreaker,
                                              temp)

                st.subheader(f"👤 {ice.get('perfil_resumen', '')}")

                emojis = {
                    "divertida": "😂",
                    "observacion_encantadora": "✨",
                    "observacion encantadora": "✨",
                    "observación encantadora": "✨",
                    "pregunta_con_gancho": "❓",
                    "pregunta con gancho": "❓",
                    "cumplido_no_fisico": "💘",
                    "cumplido no físico": "💘",
                    "cumplido no fisico": "💘",
                    "wildcard": "🃏",
                    "wildcard comodín": "🃏",
                    "wildcard comodin": "🃏",
                    "comodin": "🃏",
                    "comodín": "🃏"
                }

                for i, linea in enumerate(ice.get('lineas', []), 1):
                    tipo_original = linea.get('tipo', '').strip()
                    clave_normalizada = tipo_original.lower()
                    clave_normalizada = re.sub(r'[^a-záéíóúñü ]', ' ', clave_normalizada)
                    clave_normalizada = re.sub(r'\s+', ' ', clave_normalizada).strip()

                    emoji = emojis.get(clave_normalizada, None)
                    if emoji is None:
                        emoji = "💬"
                        st.caption(f"⚠️ No se encontró emoji para: '{tipo_original}' (clave: '{clave_normalizada}')")

                    tipo_formateado = tipo_original.replace('_', ' ').title()

                    with st.container():
                        st.markdown(f"""
                        <div class="icebreaker-card">
                            <h4>{emoji} {tipo_formateado}</h4>
                            <p style="font-size:16px; margin:10px 0;">"{linea['texto']}"</p>
                            <p style="color:#666; font-size:13px;">💡 {linea['porque']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        copy_button(linea['texto'])