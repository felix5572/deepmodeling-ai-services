
#%%
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
import os
from jose import jwt

#%%

DJANGO_JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAoZL6XkXNV7ZZh9HobhNC
XD9TPeD8he6ev5V8W4LkjONnmU+lg1RM3Hax1eA/0cnD0WVMOSE92s82lsVaIXE/
DdjsGcTrbry1ly31umgYlt5b8M369p+E0BPWc2HMqFkat3uZ6emURrU8IOMfP5/t
Ark5dJDBOejSROnLJ7lgXS2IHKX9YyAY/HPRb8BltkREZKdTHSnMnhP3/1Fy8UKQ
upe6tMIXQoq2mAfon33ft1Ti7/gqAtJQVwqptvRBXNyO0bozozaAxRz1hn2siV50
m24lDW8gMDwRJB71lC8pNwwQ+mxGSPZ1iadrYc1Tb/4ob1mW1SPtw91Mzcgxr9CU
MQIDAQAB
-----END PUBLIC KEY-----"""


#%%
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        bypass_paths = ["/health", "/docs", "/openapi.json", "/info",]

        if request.url.path in bypass_paths:
            return await call_next(request)


        
        auth_token = self._extract_token(request)
        # jwt_user_id = aut
        owner_user_id = self.get_owner_user_id(request=request)
    
        if not auth_token and owner_user_id=='default_unnamed_user':
            return await call_next(request)

        if not auth_token:
            raise HTTPException(status_code=401, detail="Missing auth token")
        
        try:
            payload = self._validate_token(auth_token)
            request.state.user = payload 
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token. {payload=} {auth_token=} {e=}")

        if owner_user_id and ( owner_user_id != payload["user_id"] ):
            raise HTTPException(status_code=403, detail=f"owner_user_id does not match token user_id. {owner_user_id=} != {payload['user_id']=}")
        
        return await call_next(request)

    @classmethod
    def get_auth_token(cls, request: Request) -> str:

        # owner_user_id = cls._get_owner_user_id(request=request)
        auth_token = cls._extract_token(request=request)

        payload = cls._validate_token(auth_token=auth_token)
        return auth_token

    @classmethod
    def get_owner_user_id(cls,request: Request) -> str:
        path_owner_user_id = request.path_params.get("owner_user_id")
        query_owner_user_id = request.query_params.get("owner_user_id")
        if path_owner_user_id and query_owner_user_id:
            if path_owner_user_id != query_owner_user_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inconsistent owner_user_id: {path_owner_user_id=} vs {query_owner_user_id=}"
                )
        
        # payload = self._validate_token(auth_token=auth_token)
        # jwt_owner_user_id = self._extract_token(request=request)
        
        owner_user_id = path_owner_user_id or query_owner_user_id or cls.get_jwt_user_id(request=request)

        return owner_user_id

    @classmethod
    def get_jwt_user_id(cls, request: Request) -> str:
        auth_token = cls._extract_token(request=request)
        payload = cls._validate_token(auth_token=auth_token)
        jwt_user_id = payload.get("user_id")
        return jwt_user_id
    
    @staticmethod
    def _extract_token(request: Request) -> str:
        # Authorization header
        auth_header = request.headers.get("Authorization")
        auth_token = None
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]
        # Cookie
        elif request.cookies.get("auth_token"):
            auth_token = request.cookies.get("auth_token")
        # Query parameter
        elif request.query_params.get("auth_token"):
            auth_token = request.query_params.get("auth_token")
        elif request.headers.get("X-Deepmd-User-Auth-Token"):
            auth_token = request.headers.get("X-Deepmd-User-Auth-Token")
        else:
            raise HTTPException(status_code=401, detail="Missing auth token")
        return auth_token
    
    @staticmethod
    def _validate_token(auth_token: str) -> dict:
        # DJANGO_JWT_PUBLIC_KEY = os.environ["DJANGO_JWT_PUBLIC_KEY"]
        payload = jwt.decode(auth_token, DJANGO_JWT_PUBLIC_KEY, algorithms=["RS256"])
        if not payload.get("user_id"):
            raise jwt.InvalidTokenError(f"user_id cannot be None {payload=} {auth_token=}")
        return payload