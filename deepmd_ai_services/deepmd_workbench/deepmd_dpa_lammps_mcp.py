#%%

from fastmcp import FastMCP, Context
from loguru import logger
import modal
import uvicorn
from typing import ClassVar, Optional, Annotated
from pydantic import Field
from fastapi import Request
from fastapi.responses import PlainTextResponse

from deepmd_modal_run_service import get_lammps_simulation_executor_instance
#%%

#%%




#%%
mcp_instance = FastMCP(
    """DeepMD Run Service. Support long run lammps simulation and short run lammps simulation. 
    The environment is setup with CUDA and DeepMD-Kit 3.1.0 in modal T4 GPU environment."""
    )

# @mcp_server.tool(name="run_lammps",           # Custom tool name for the LLM
#     description="Run LAMMPS script")
# def run_lammps(lammps_script: str) -> str:
#     """Run LAMMPS script"""
#     return f"LAMMPS script: {lammps_script}"

class DeepmdDpaLammpsMcp:
    is_initialization:bool = False
    personal_volume:modal.Volume = None

    personal_lammps_cls: modal.Cls = None
    personal_lammps_instance = None


    def __init__(self, mcp_instance: FastMCP, *, owner_user_id: str = 'default_unnamed_user'):
        self.mcp_instance = mcp_instance
        self.owner_user_id = owner_user_id
        self._personal_lammps_instance = None

        self.init_mcp_instance()

        # self.initialization()

    def init_mcp_instance(self):

        mcp_instance.custom_route("/health", methods=["GET"])(self.health_check)
        mcp_instance.resource("config://version")(self.get_version)
        mcp_instance.tool(self.submit_long_run_lammps_simulation,)
        mcp_instance.tool(self.short_run_lammps_simulation, )

    
    @property
    def personal_lammps_instance(self):
        """lazy initialization"""
        if self._personal_lammps_instance is None:
            self._personal_lammps_instance = get_lammps_simulation_executor_instance.local(
                owner_user_id=self.owner_user_id
            )
            self.is_initialization = True
        else:
            pass
        
        return self._personal_lammps_instance
        
    
    def initialization(self):
        instance = self.personal_lammps_instance
        return instance
        

    # @mcp_instance.resource("config://version")
    def get_version(self): 
        return "0.1.0"

    def get_dpa_model_path(self):
        pass



    # @mcp.custom_route("/health", methods=["GET"])
    async def health_check(self, request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    
    async def submit_long_run_lammps_simulation(self,
        commands: Annotated[str, Field(description="The commands to run lammps")] = 'lmp -h', 
        job_dir: Annotated[str, Field(description="The job directory to run lammps")] = '/workspace/', 
        ctx: Context = None,
        ) -> str:
        """
        long run lammps simulation, timeout is 12hours (in T4 GPU environment)
        Production use. note that Price for GPU is approximately $0.59 USD per hour.
        """
        function_call = self.personal_lammps_instance.lammps_simulation_job.spawn(commands=commands, job_dir=job_dir, timeout=60*60*12)

        function_call_id = function_call.object_id

        logger.info(f"submitted long run lammps simulation: {function_call_id=}. {commands=}, {job_dir=} ")
        ctx.info(f"submitted long run lammps simulation: {function_call_id=}. {commands=}, {job_dir=} ")

        return f"success submitted function call id: {function_call_id} {commands=}, {job_dir=}"


    # @mcp_server.tool()
    async def short_run_lammps_simulation(self,
        commands: Annotated[str, Field(description="The commands to run lammps")] = 'lmp -h', 
        job_dir: Annotated[str, Field(description="The job directory to run lammps")] = '/workspace/', 
        ctx: Context = None,
        ) -> str:
        """
        short run lammps simulation, timeout is 30 seconds. (in T4 GPU environment)
        Only for testing if the lammps simulation environment is working / if the lammps input script is not valid/ if the files are uploaded correctly.
        """

        buffer = []
        current_length = 0

        # async for chunk in instance.lammps_simulation_stream.remote.aio(
        for chunk in self.personal_lammps_instance.lammps_simulation_stream.remote_gen(
            commands=commands, 
            job_dir=job_dir, 
            timeout=30
        ):

            line = chunk.decode()
            buffer.append(line)
            current_length += len(line)
            
            if len(buffer) >= 20 or current_length >= 2000:
                await ctx.info("".join(buffer))
                buffer.clear()
                current_length = 0
        
        if buffer:
            await ctx.info("".join(buffer))
        
        return "Simulation completed"

    async def dpa_freeze_model(self, ctx: Context = None) -> str:
        """
        dpa freeze model
        """

        await ctx.info("freezing model...")
        return "Model frozen"

    # async def 




# mcp_server = 




# mcp_app = mcp_server.http_app(path="/mcp", transport="streamable-http", stateless_http=True)
# mcp_app = mcp_server.http_app(transport="streamable-http", stateless_http=True)
# return mcp_app


#%%

if __name__ == "__main__":
    mcp_provider = DeepmdDpaLammpsMcp(mcp_instance)
    mcp_instance.run(transport="streamable-http", port=8002, host="0.0.0.0")
    # mcp_instance.http_app(transport="streamable-http", stateless_http=True)

#%%