from fastapi import Depends, HTTPException, Header
from db import supabase
from datetime import date

async def get_current_user(authorization: str = Header(None)):
    """Extrae y verifica el token JWT del usuario."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    token = authorization.split(" ")[1]
    try:
        user = supabase.auth.get_user(token)
        return user.user
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

def check_usage_limit(tool_name: str):
    """Dependencia que controla los límites diarios por herramienta según el plan."""
    async def _check(user: dict = Depends(get_current_user)):
        user_id = user.id
        today = date.today()

        # Obtener límites del usuario
        res = supabase.table("usage_limits").select("tool_limits").eq("user_id", user_id).execute()
        if not res.data or not res.data[0].get("tool_limits"):
            # Si no tiene límites, asignar plan gratuito por defecto
            default_limits = {"monitor": 2, "icebreaker": 2, "salvavidas": 1, "sparring": 0, "espejo": 0}
            supabase.table("usage_limits").upsert({
                "user_id": user_id,
                "plan": "gratuito",
                "tool_limits": default_limits,
                "last_reset": str(today)
            }).execute()
            tool_limits = default_limits
        else:
            tool_limits = res.data[0]["tool_limits"]

        limit = tool_limits.get(tool_name, 0)
        if limit == 0:
            raise HTTPException(
                status_code=402,
                detail=f"La herramienta '{tool_name}' no está disponible en tu plan actual."
            )

        # Uso diario de la herramienta
        usage_res = supabase.table("tool_usage_daily") \
            .select("count") \
            .eq("user_id", user_id) \
            .eq("tool", tool_name) \
            .eq("usage_date", str(today)) \
            .execute()

        current_usage = usage_res.data[0]["count"] if usage_res.data else 0

        if current_usage >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Has alcanzado el límite diario de {tool_name}."
            )

        # Incrementar uso
        if usage_res.data:
            supabase.table("tool_usage_daily") \
                .update({"count": current_usage + 1}) \
                .eq("user_id", user_id) \
                .eq("tool", tool_name) \
                .eq("usage_date", str(today)) \
                .execute()
        else:
            supabase.table("tool_usage_daily").insert({
                "user_id": user_id,
                "tool": tool_name,
                "usage_date": str(today),
                "count": 1
            }).execute()

        return user
    return _check