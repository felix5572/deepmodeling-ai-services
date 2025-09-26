import modal
import requests
import time
import json
from fastapi import UploadFile, File, Form
from typing import Optional
import os
import asyncio
from fastmcp import FastMCP
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import UploadFile, File, Form
from pydantic import BaseModel

import aiofiles
import shlex
from datetime import datetime
import secrets
from loguru import logger
from fastmcp import Context, FastMCP
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.sessions import DatabaseSessionService
from typing import Union
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt
from modal import FilePatternMatcher



from deepmd_auth_midware import AuthMiddleware

#%%
# Configuration
DEFAULT_LAMMPS_TIMEOUT_SECONDS = 30 
CLEANUP_TIMEOUT_SECONDS = 60         # 1 minute for graceful shutdown

#%%
# Simple Modal app
# app = modal.App("deepmd-run-service")

pip_packages = [
    "fastapi[standard]",
    "uvicorn[standard]",
    "google-adk",
    "fastmcp",
    "requests",
    "modal",
    "sqlalchemy",
    "uvloop",
    "httptools",
    "aiofiles",
    "loguru",
    "sqlalchemy",
    "uvloop",
    "httptools",
    "python-jose[cryptography]",
    "workos",
    "asyncpg",
    "cloudevents",
    "openmeter==1.0.0b188",
]


lammps_image = (
    modal.Image.from_registry("deepmodeling/deepmd-kit:3.1.0_cuda129"
    ).pip_install(pip_packages
    ).run_commands([
        "python -c 'import deepmd; print(\"deepmd installed\")'",
    ])
    .run_commands([
        "lmp -h"
    ]).add_local_python_source("deepmd_lammps_template","draft_metering_midware"
))


web_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(pip_packages).env({


    }).add_local_dir(local_path="./", remote_path="/root/", ignore=~FilePatternMatcher("*.py")
    )
    # .add_local_python_source("deepmd_lammps_template","draft_metering_midware")
    # ).add_local_dir("agent_services", "/app/agent_services")
)



app_name = "deepmd-run-service"
app = modal.App(name=app_name,  secrets=[modal.Secret.from_name("openmeter-token")])

#%% 

@app.cls(image=lammps_image, 
    gpu='T4',
    timeout=3600,
    scaledown_window=10,
    restrict_modal_access=True,
    max_inputs=1
    )
class LammpsSimulationExecutor:

    owner_user_id: str = modal.parameter(default='default_unnamed_user')

    @modal.method()
    def setup_before_enter(self):
        
        
        pass

    @modal.method()
    def cleanup_before_exit(self):
        pass

    @modal.method()
    async def lammps_simulation_job(self, commands: str, job_dir: str, timeout=60):

        commands_list = shlex.split(commands)
        program = commands_list[0]
        args = commands_list[1:]
        logger.info(f"lammps stream running in job_dir: {commands_list=}, {timeout=}, {job_dir=}.")

        process = await asyncio.create_subprocess_exec(
            program,
            *args,
            shell=False,
            cwd=job_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        return_code = None
        try:
            return_code = await asyncio.wait_for(process.wait(), timeout=timeout)    
        except asyncio.TimeoutError:
            process.terminate()
        
        logger.info(f"lammps simulation finished in {job_dir=} {return_code=}.")
        return {"return_code": return_code}
        

    @modal.method(is_generator=True)
    async def lammps_simulation_stream(self, commands: Union[str, list[str]], job_dir: str = '/workspace/', timeout: int = DEFAULT_LAMMPS_TIMEOUT_SECONDS):
        max_seconds = DEFAULT_LAMMPS_TIMEOUT_SECONDS
        yield f"data: [DEEPMD] Starting LAMMPS (timeout: {max_seconds}s)...\n\n".encode()
        
        
        commands_list = shlex.split(commands)

        program = commands_list[0]
        args = commands_list[1:]

        logger.info(f"lammps stream running in job_dir: {commands_list=}, {timeout=}, {job_dir=}.")

        yield f"data: [DEEPMD] Running in job_dir: {job_dir} , timeout: {timeout}s .\n\n".encode()
        yield f"data: [DEEPMD] Running program: {program} , with args: {args}\n\n".encode()

        yield f"data: [DEEPMD] ---origin LAMMPS output below---\n\n".encode()

        process = await asyncio.create_subprocess_exec(
            program,
            *args,
            shell=False,
            cwd=job_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        try:
            async with asyncio.timeout(timeout):
                async for line in process.stdout:
                    yield line

                return_code = await process.wait()
            
            yield f"data: [DEEPMD] ---finished origin LAMMPS simulation output above {return_code=}---\n\n".encode()
            
        except asyncio.TimeoutError:
            yield f"data: [DEEPMD] ---timeout origin LAMMPS simulation output above---\n\n".encode()
            yield (f"data: [DEEPMD] [TIMEOUT] The program is still runnning, "
                f"but the execution exceeded {max_seconds}s limit, terminating now and will kill it in {CLEANUP_TIMEOUT_SECONDS} seconds...\n\n").encode()
            process.terminate()  # Send SIGTERM
            
            # Read any remaining output during cleanup
            try:
                await asyncio.wait_for(process.wait(), timeout=CLEANUP_TIMEOUT_SECONDS)
                # Try to read any final output
                async for line in process.stdout:
                    yield line
                yield f"\ndata: [DEEPMD] [TIMEOUT] Clean shutdown completed\n\n".encode()
            except asyncio.TimeoutError:
                process.kill()  # Force kill
                yield f"data: [DEEPMD] [TIMEOUT] Force kill after {CLEANUP_TIMEOUT_SECONDS} seconds\n\n".encode()
        finally:
            logger.info(f"lammps stream finished in {job_dir=} {process.returncode=}.")


@app.function(image=lammps_image)
def get_lammps_simulation_executor_instance(owner_user_id: str = 'default_unnamed_user'):
    personal_volume_name = f"jupyterlab-personal-{owner_user_id}"

    personal_volume = modal.Volume.from_name(personal_volume_name, create_if_missing=True)

    logger.info(f" {personal_volume.listdir('/')=}")
    LammpsSimulationExecutor_cls = modal.Cls.from_name(app_name='deepmd-run-service',
            name='LammpsSimulationExecutor'
        )

    personal_lammps_cls = LammpsSimulationExecutor_cls.with_options(
            volumes={'/workspace/': personal_volume}
            )
    personal_lammps_instance = personal_lammps_cls(owner_user_id=owner_user_id)

    return personal_lammps_instance
    # return LammpsSimulationExecutor(owner_user_id=owner_user_id)


# @app.function(image=image, gpu='T4')
# def lammps_simulation_stream(*commands: str, ):
#     pass


# class LammpsSimulationStreamParams(BaseModel):
#     commands: list[str]
#     # files: list[UploadFile]
#     basedir: Optional[str]
#     timeout: Optional[int]

#%%

# class AuthMiddleware(BaseHTTPMiddleware):
#     def __init__(self, app, allowed_tokens: set):
#         super().__init__(app)
#         self.allowed_tokens = allowed_tokens
    
#     async def dispatch(self, request, call_next):
#         # 跳过健康检查
#         if request.url.path in ["/health", "/info"]:
#             return await call_next(request)
        
#         # 检查认证
#         auth_header = request.headers.get("Authorization", "")
#         if not auth_header.startswith("Bearer "):
#             return JSONResponse({"error": "Missing token"}, status_code=401)
        
#         token = auth_header[7:]
#         if token not in self.allowed_tokens:
#             return JSONResponse({"error": "Invalid token"}, status_code=403)
        
#         return await call_next(request)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        bypass_paths = ["/health", "/docs", "/openapi.json", "/info", 
            "/proxy-mcp/docs", "/proxy-agent/docs", "/proxy-mcp/openapi.json", "/proxy-agent/openapi.json"
        ]

        if request.url.path in bypass_paths:
            return await call_next(request)


        owner_user_id = self._get_owner_user_id(request=request)
        auth_token = self._extract_token(request)

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

    def _get_owner_user_id(self, request: Request) -> str:
        path_owner_user_id = request.path_params.get("owner_user_id")
        query_owner_user_id = request.query_params.get("owner_user_id")
        if path_owner_user_id and query_owner_user_id:
            if path_owner_user_id != query_owner_user_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inconsistent owner_user_id: {path_owner_user_id=} vs {query_owner_user_id=}"
                )
        
        owner_user_id = path_owner_user_id or query_owner_user_id or 'default_unnamed_user'
        
        return owner_user_id
    
    def _extract_token(self, request: Request) -> str:
        # Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Cookie
        if request.cookies.get("auth_token"):
            return request.cookies.get("auth_token")
        
        # Query parameter
        if request.query_params.get("auth_token"):
            return request.query_params.get("auth_token")
        
        return None
    
    def _validate_token(self, auth_token: str) -> dict:

        DJANGO_JWT_PUBLIC_KEY = os.environ["DJANGO_JWT_PUBLIC_KEY"]
        payload = jwt.decode(auth_token, DJANGO_JWT_PUBLIC_KEY, algorithms=["RS256"])
        if not payload.get("user_id"):
            raise jwt.InvalidTokenError(f"user_id cannot be None {payload=} {auth_token=}")
        return payload





#%%

    

    
@app.cls(
    image=web_image, 
    scaledown_window=20,
    # volumes={'/modal-shared/': agent_session_shared_volume},
    # volumes={'/public/': modal.Volume.from_name(name="deepmd-lammps-sessions-public", create_if_missing=True)},
    # volumes={'/app/data/': modal.Volume.from_name(name="deepmd-agent-services-data")},
    secrets=[modal.Secret.from_name("google-api-key")],
)
class DPLammpsService:
    owner_user_id: str = modal.parameter(default='default_unnamed_user')

    @modal.enter()
    def setup_before_enter(self):
        self.personal_volume_name = f"jupyterlab-personal-{self.owner_user_id}"

        self.personal_volume = modal.Volume.from_name(self.personal_volume_name, create_if_missing=True)
        # self.shared_volume = agent_session_shared_volume
        # agent_session_shared_volume


        self.LammpsSimulationExecutor_cls = modal.Cls.from_name(app_name='deepmd-run-service',
            name='LammpsSimulationExecutor'
        )
        
        self.personal_lammps_cls = self.LammpsSimulationExecutor_cls.with_options(
            volumes={'/workspace/': self.personal_volume}
            )
        self.personal_lammps_instance = self.personal_lammps_cls(owner_user_id=self.owner_user_id)

        
        DeepmdAgentServices_cls = modal.Cls.from_name(app_name='deepmd-run-service',
            name='DeepmdAgentServices'
        )
        
        self.personal_agent_cls = DeepmdAgentServices_cls.with_options(
            volumes={'/workspace/': self.personal_volume}
        )

        # self.personal_agent_cls = DeepmdAgentServices.with_options(
        #     volumes={'/workspace/': self.personal_volume}
        # )

        # self.personal_agent_cls.hydrate()

        self.personal_agent_instance = self.personal_agent_cls(
            owner_user_id=self.owner_user_id,
            # personal_lammps_instance=self.personal_lammps_instance
            )

        # logger.info(f" {self.personal_agent_instance.agent_app.get_web_url()=}")
        # logger.info(f" {self.personal_agent_instance.check_status.remote()=}")

        # self.agent_app = self.personal_agent_instance.get_agent_app.remote()
        # self.remote_url = self.personal_agent_instance.redirect_to_fastapi.remote()
        # self.remote_url = self.personal_agent_instance.agent_app.get_web_url()

        # self.remote_url = self.personal_agent_instance.check_status.get_web_url()
        # self.agent_status = self.personal_agent_instance.agent_app.get_current_stats()

        self.remote_response = self.personal_agent_instance.handle_request.remote(request=None)

        

        logger.info(f" {self.personal_volume.listdir('/')=}")
        # logger.info(f" {self.agent_app=}")
        # logger.info(f" {self.agent_app.get_web_url()=}")
        # logger.info(f" {self.remote_url=}")
        logger.info(f" {self.remote_response=}")
        # logger.info(f" {self.agent_status=}")
        # logger.info(f" {os.listdir('/')=} ")
        # logger.info(f" {os.listdir('/workspace/')=}")
        
        # self.personal_agent_instance.set_

        # sqlite3.connect("/public/deepmd_agent_sessions.db").close()
        # self.agent_session_db_url= f"sqlite:///app/data/deepmd_agent_sessions.db"
        # self.agent_session_service = DatabaseSessionService(db_url=self.agent_session_db_url)

    @modal.exit()
    def cleanup_before_exit(self):
        pass

    # @modal.asgi_app()
    # def proxy_app(self):


    #     return fastapi_app

    @modal.fastapi_endpoint()
    async def handle_request_endpoint(self, request: Request):
        response = await self.personal_agent_instance.handle_request.remote(request=request)
        return response


    @modal.asgi_app()
    def fastapi_app(self):
        # self.mcp_app = self.personal_agent_instance.get_mcp_app.local()
        # self.agent_app = self.personal_agent_instance.get_agent_app.local()
        # mcp_app = self.personal_agent_instance.mcp_app.local()
        # agent_app = self.personal_agent_instance.agent_app.local()

        

        # lifespan = self.mcp_app.router.lifespan_context
        # fastapi_app = FastAPI(title="LAMMPS Service", lifespan=lifespan)
        fastapi_app = FastAPI(title="LAMMPS Service")
        # fastapi_app.mount("/agent-proxy", agent_app)
        # fastapi_app.add_middleware(AuthMiddleware)

        # fastapi_app.mount("/agent-proxy", agent_app)
        # fastapi_app.mount("/", self.agent_app)
        # fastapi_app.mount("/mcp-proxy", self.mcp_app)
        # @fastapi_app.post("/")
        # async def handle_request_endpoint(request: Request):
        #     return self.personal_agent_instance.handle_request.remote(request=request)

        
        @fastapi_app.get("/test-lammps-stream")
        async def test_lammps_stream_endpoint():
            # user_cls = LammpsSimulationExecutor.with_options(
            #     volumes={'/workspace/': modal.Volume.from_name(name="jupyterlab-personal-test_user")}
            #     )
            # instance = user_cls(owner_user_id="test_user")

            return StreamingResponse(
                test_lammps_stream.remote_gen(),
                media_type="text/event-stream"
            )

        @fastapi_app.get("/health")
        async def health_check_endpoint():
            return {"status": "healthy"}

        @fastapi_app.post("/lammps-simulation-stream")
        async def lammps_simulation_stream_endpoint(
            request: Request,
            files: list[UploadFile] = File([], description="The files to run lammps, will be saved to the workdir, with file basename"), 
            commands: str = Form(..., description="The commands to run lammps"), 
            timeout: Optional[int] = Form(20, description="The timeout of the lammps simulation. default is 20 to just test the service"),
            basedir: Optional[str] = Form('/workspace/', description="The basedir of the lammps simulation.  /workspace/ or subfolder. it will combine job_dir/ (default auto generated) "),
            job_dirname: Optional[str] = Form(None, description="(default auto generated if is None. set to empty to disable auto generated).it will combine `basedir` ")
        ):
            
            logger.info(f"lammps stream running in job_dir: {job_dirname=} {type(job_dirname)=} .")  

            if job_dirname is None:
                job_dirname = f"lammps-{datetime.now().astimezone().strftime('%Y%m%d-%H%M%S%Z')}-{secrets.token_hex(4)}/"
            else:
                pass

            job_dir = os.path.join(basedir, job_dirname)

            job_dir_in_volume = job_dir.strip("/workspace")

            logger.info(f"lammps stream running in job_dir: {self.owner_user_id=} {commands=}, {timeout=}, {basedir=}, {job_dirname=} {self.personal_volume=} {job_dir_in_volume=}.")  

            
            with self.personal_volume.batch_upload() as batch:
                for file in files:
                    await file.seek(0)
                    file_basename = os.path.basename(file.filename)
                    remote_file_path = os.path.join(job_dir_in_volume, file_basename)
                    batch.put_file(file.file, remote_file_path)
                    logger.info(f"uploaded file: {file_basename=} to {remote_file_path=}.")

            logger.info(f"uploaded files to job_dir: {job_dir=}.")

            response = StreamingResponse(
                # lammps_simulation_stream.remote_gen(commands),
                self.personal_lammps_instance.lammps_simulation_stream.remote_gen(commands=commands, job_dir=job_dir, timeout=timeout),
                media_type="text/event-stream"
            )

            return response

        return fastapi_app
        # fastapi_app.lifespan = self.personal_agent_instance.get_agent_app().lifespan

        # @modal.asgi_app
        # def mcp_app(self):
        #     mcp_app = self.personal_agent_instance.get_mcp_app()
        #     return mcp_app

        # @modal.asgi_app
        # def agent_app(self):
        #     agent_app = self.personal_agent_instance.get_agent_app()
        #     return agent_app

#%%


