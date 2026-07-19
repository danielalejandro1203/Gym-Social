from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import supabase
from datetime import date

router = APIRouter(prefix="/api/auth")

class SignUp(BaseModel):
    email: str
    password: str

class Login(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register(user: SignUp):
    try:
        res = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        # Insertar límites gratuitos para el nuevo usuario
        default_limits = {"monitor": 2, "icebreaker": 2, "salvavidas": 1, "sparring": 0, "espejo": 0}
        supabase.table("usage_limits").insert({
            "user_id": res.user.id,
            "plan": "gratuito",
            "tool_limits": default_limits,
            "last_reset": str(date.today())
        }).execute()
        return {"user": res.user.email, "message": "Usuario registrado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(user: Login):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        return {
            "access_token": res.session.access_token,
            "user": res.user.email
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")