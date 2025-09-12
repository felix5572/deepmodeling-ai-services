import os
from jose import jwt
import json
import base64
from datetime import timedelta
from functools import wraps
from typing import Optional

from ninja import Router, Schema, Field
from ninja import ModelSchema
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, HttpRequest
from django.utils import timezone
from workos import WorkOSClient
from urllib.parse import urlencode
from users.models import User
from loguru import logger




users_router = Router()


# MODAL_JUPYTER_SERVICE_ENDPOINT=""
# Schemas
# default_nexturl = 
DEFAULT_NEXTURL = "/api/users/dashboard"
class JWTExchangeSchema(Schema):
    external_jwt: str
    nexturl: str = Field(default=DEFAULT_NEXTURL)

class JWTValidateSchema(Schema):
    token: str

# Services
class WorkOSService:
    def __init__(self):
        self.client = WorkOSClient(
            api_key=os.getenv("WORKOS_API_KEY"),
            client_id=os.getenv("WORKOS_CLIENT_ID")
        )
    
    def get_authorization_url(self, nexturl: str = None):
        state = base64.urlsafe_b64encode(
            json.dumps({"nexturl": nexturl}).encode()
        ).decode() if nexturl else None
        
        return self.client.user_management.get_authorization_url(
            provider="authkit",
            # redirect_uri=os.getenv("WORKOS_REDIRECT_URI"),
            state=state
        )
    
    def authenticate_with_code(self, code: str):
        return self.client.user_management.authenticate_with_code(
            code=code,
        )

class JWTService:
    def __init__(self):
        self.django_jwt_private_key = os.getenv("DJANGO_JWT_PRIVATE_KEY")
        self.django_jwt_public_key = os.getenv("DJANGO_JWT_PUBLIC_KEY")
        self.algorithm = "RS256"
    
    def generate_token(self, user: User, expire_in: int = 7*24*3600):
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "auth_provider": user.auth_provider,
            "exp": timezone.now() + timedelta(seconds=expire_in)
        }
        return jwt.encode(payload, self.django_jwt_private_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str):
        payload = jwt.decode(token, self.django_jwt_public_key, algorithms=[self.algorithm])
        user_id = payload["user_id"]
        if user_id is None:
            raise jwt.InvalidTokenError("user_id cannot be None")
        user = User.objects.get(user_id=user_id)
        return user, payload

# Services instances
workos_service = WorkOSService()
jwt_service = JWTService()

# Decorators
def auth_required(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            auth_token = auth_header[7:]
        elif request.COOKIES.get('auth_token'):
            auth_token = request.COOKIES.get('auth_token')
        elif request.GET.get('auth_token'):
            auth_token = request.GET.get('auth_token')
        else:
            return JsonResponse({'error': 'Missing or invalid Authorization header'}, status=401)
        user, payload = jwt_service.validate_token(auth_token)
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper

# Auth endpoints
@users_router.get("/auth/authorize")
def get_authorization_url(request, provider: str = "authkit", nexturl: str = None):
    """Get WorkOS authkit authorization URL"""
    authorization_url = workos_service.get_authorization_url(nexturl)
    return HttpResponseRedirect(authorization_url)

@users_router.get("/auth/callback")
def workos_callback(request, code: str, state: str = None):
    """Handle WorkOS callback"""
    auth_response = workos_service.authenticate_with_code(code)
    workos_user = auth_response.user

    user_id = f"user__workos__{workos_user.id}"
    username = f"default_username__workos__{workos_user.id}"
    
    user, created = User.objects.get_or_create(
        user_id=user_id,
        defaults={
            'username': username,
            'email': workos_user.email,
            'first_name': workos_user.first_name,
            'last_name': workos_user.last_name,
            'external_id': workos_user.id,
            'auth_provider': 'workos'
        }
    )
    
    auth_token = jwt_service.generate_token(user)
    
    
    if state:
        decoded_state = json.loads(base64.urlsafe_b64decode(state).decode())
        nexturl = decoded_state.get("nexturl", DEFAULT_NEXTURL)
    else:
        nexturl = DEFAULT_NEXTURL
    
    redirect_url = f"/api/users/auth/success?auth_token={auth_token}&nexturl={nexturl}"
    response = HttpResponseRedirect(redirect_url)

    return response

@users_router.get("/auth/success")
def auth_success(request, auth_token: str, nexturl: str):
    html = f"""
    <html>
        <head><title>auth success</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2>🎉 auth success!</h2>
            <p>redirecting to target page... nexturl: {nexturl}</p>
            <p>redirecting to target page... your jwt token: {auth_token}</p>
            <script>
                setTimeout(() => window.location.href = '{nexturl}', 1000);
            </script>
        </body>
    </html>
    """

    response = HttpResponse(html)
    response.set_cookie(
        "auth_token",
        auth_token,
        max_age=7*24*3600,
        secure=True,
        httponly=True,
        samesite="lax"
    )
    return response

@users_router.get("/dashboard")
@auth_required  
def dashboard(request):
    """Debug dashboard - reuse existing get_current_user logic"""

    user_schema = _get_current_user(request)
    user_dict = user_schema.dict()
    user_json = json.dumps(user_dict, indent=2, ensure_ascii=False, default=str)
    
    html = f"""
    <h1>Debug Dashboard</h1>
    <h2>User Data (same as /api/users/me)</h2>
    <pre>{user_json}</pre>
    <p><a href="/api/users/me">Raw JSON endpoint</a> | <a href="/api/users/auth/logout">Logout</a></p>
    """
    return HttpResponse(html)



@users_router.post("/auth/logout")
def logout(request, nexturl: str = '/'):
    """Logout user"""
    response = HttpResponseRedirect(nexturl)
    return response

# JWT endpoints
@users_router.post("/jwt/issue")
@auth_required
def issue_jwt(request):
    """Issue new JWT token"""
    auth_token = jwt_service.generate_token(request.user)
    return {
        "access_token": auth_token,
        "token_type": "bearer",
        "expires_in": 7*24*3600  # 7 days in seconds
    }

@users_router.post("/jwt/bohrium-proxy/callback")
def callback_bohrium_proxy_jwt(request, data: JWTExchangeSchema):
    """Callback for external JWT"""

    BOHRIUM_PROXY_JWT_PUBLIC_KEY = os.getenv("BOHRIUM_PROXY_JWT_PUBLIC_KEY")
    external_payload = jwt.decode(
        data.external_jwt,
        key=BOHRIUM_PROXY_JWT_PUBLIC_KEY,
        options={"verify_signature": False}
    )
    user_data = external_payload['user_data']
    # user_id = 
    logger.info(f"user_data: {user_data}")


    external_id = user_data['user_id']
    user_id = f"user__bohrium-proxy__{external_id}"
    username = f"default_username__bohrium-proxy__{user_data['name']}"
    organization = f"bohrium-proxy__{user_data['org_id']}"
    email = user_data.get("email", None)

    user, created = User.objects.get_or_create(
        user_id=user_id,
        defaults={
            'username': username,
            'email': email,
            'auth_provider': 'bohrium-proxy',
            'external_id': external_id,
            'organization': organization
        }
    )

    # nexturl = f"{MODAL_JUPYTER_SERVICE_ENDPOINT}/users/{user_id}/sandbox"
    # nexturl = f"/api/users/dashboard"
    nexturl = data.nexturl
    
    auth_token = jwt_service.generate_token(user)

    redirect_url = f"/api/users/auth/success?auth_token={auth_token}&nexturl={nexturl}"
    return HttpResponseRedirect(redirect_url)
    

@users_router.post("/jwt/validate")
def validate_jwt(request, data: JWTValidateSchema):
    """Validate JWT token"""
    user, payload = jwt_service.validate_token(data.token)
    
    return {
        "valid": True,
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "auth_provider": user.auth_provider,
        "organization": user.organization,
        "exp": payload.get("exp")
    }


@users_router.get("/jwt")
@auth_required
def get_jwt(request, expire_in: int = 7*24*3600):
    """Get user JWT"""
    if expire_in > 90*24*3600:
        res = {"error": "Expire time too long"}, 400 
    else:
        auth_token = jwt_service.generate_token(request.user, expire_in=expire_in)
        res = {"auth_token": auth_token, "expires_in": expire_in}
    return res
    

class UserResponseSchema(ModelSchema):
    class Meta:
        model = User
        fields = ["id", "user_id", "username", "email", "first_name", "last_name", "auth_provider", "external_id", "organization"]

def _get_current_user(request) -> UserResponseSchema:
    """Get current authenticated user as UserResponseSchema"""
    user_schema = UserResponseSchema.from_orm(request.user)
    return user_schema

@users_router.get("/me", response=UserResponseSchema)
@auth_required  
def api_me(request):
    user_schema = _get_current_user(request)
    user_dict = user_schema.dict()
    return user_dict


