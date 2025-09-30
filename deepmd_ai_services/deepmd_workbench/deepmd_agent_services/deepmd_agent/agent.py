#%%
from google.adk.agents import LlmAgent, Agent, SequentialAgent
from google.adk.tools import google_search
from google.adk.tools import agent_tool
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from google.adk.models.lite_llm import LiteLlm
import litellm 
import os
from google.adk.code_executors import BuiltInCodeExecutor
# import dotenv
from dotenv import load_dotenv

#%%
# os.environ["LITELLM_PROXY_API_BASE"] = "https://litellm.deepmd.us"
# os.environ["LITELLM_PROXY_API_KEY"] = "sk-...XOOw"

load_dotenv()

# os.environ["GOOGLE_API_KEY"] = 'AI..._cQ'

litellm.use_litellm_proxy = True

model_original = "gemini-2.5-flash"

general_model = LiteLlm(model="gemini/gemini-2.5-flash"
    , api_base=os.getenv("LITELLM_PROXY_API_BASE"),
    api_key=os.getenv("LITELLM_PROXY_API_KEY"),
    )

coding_model = LiteLlm(model='deepseek/deepseek-chat',
    api_base=os.getenv("LITELLM_PROXY_API_BASE"),
    api_key=os.getenv("LITELLM_PROXY_API_KEY"),
)

OWNER_USER_ID = os.getenv("OWNER_USER_ID", "default_unnamed_user")
#%%


deepmd_select_dpa_model_agent = LlmAgent(
    model=general_model,
    name="deepmd_select_dpa_model_agent",
    description="Deepmd select dpa model agent. Select the best dpa model for the given task. we could provide the  default dpa model file path.",
    instruction=("""You are an agent that select and provides the deepmd dpa model.
    Selctet the best dpa model for the given task.
    If you are not sure about the best dpa model, you can ask user for more information.
    These model files are locate at /public/DPA-3.1-3M/branch_models/
    Available dpa models are:
    Domains_Alloy.pth , for alloy materials.
    Domains_Anode.pth , for  anode materials in batteries.
    Domains_Cluster.pth , for  cluster materials.
    Domains_Drug.pth , for  drug like small molecules.
    Domains_FerroEle.pth , for  ferroelectric materials.
    Domains_SemiCond.pth , for semi-conductor materials.
    Metals_AlMgCu.pth, for Al Mg Cu materials.
    H2O_H2O_PD.pth , for  water, ice Phase diagram simulation.
    Metals_AlMgCu.pth , for AlMgCu materials.
    solvated_protein_fragments.pt , for protein fragments in solvent.
    Others_HfO2.pth , for HfO2 materials.
    Organic_Reactions.pth , for organic reactions.
    """),
    # tools=[get_deepmd_dpa_select_model]
)



# Define a tool function
# def get_capital_city(country: str) -> str:
#   """Retrieves the capital city for a given country."""
#   # Replace with actual logic (e.g., API call, database lookup)
#   capitals = {"france": "Paris", "japan": "Tokyo", "canada": "Ottawa"}
#   return capitals.get(country.lower(), f"Sorry, I don't know the capital of {country}.")

deepmd_lammps_mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://deepmodeling-ai-services-mcp.zeabur.app/mcp",
        # url="https://deepmodeling--deepmd-lammps-agent-services-mcp-app.modal.run", # remote mcp
        timeout=300,
        # url="http://localhost:8002/mcp",
        # headers={"Authorization": "Bearer your-auth-token"}
    ),
)



deepmd_docs_rag_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        # url="http://localhost:8002/mcp",
        url="https://zqibhdki.sealosbja.site/api/mcp/app/tRmg19AXvG2GL46rZXadjsIb/mcp",
        # url="https://deepmodeling--deepmd-lammps-agent-services-mcp-app.modal.run", # remote mcp
        timeout=300,
        
        # headers={"Authorization": "Bearer your-auth-token"}
    ),
)


deepmd_docs_rag_agent = LlmAgent(
    model=general_model,
    name="deepmd_docs_rag_agent",
    description="Deepmd docs rag agent. Can search the deepmd docs and provide the correct information. can also chat with the chatbot.",
    instruction="""Follow the instructions and tools provided to you. 
    Usually you need to use the tools provided to you to search the deepmd docs and provide the correct information.
    You are an agent that provides the deepmd docs rag. Can search the deepmd docs and provide the correct information. can also chat directly with the chatbot.""",
    tools=[deepmd_docs_rag_toolset]
)

# deepmd_train_agent = LlmAgent(
#     model=model,
#     name="deepmd_train_agent",
#     description="Deepmd train agent",
#     instruction="You are an agent that provides the deepmd train. pretrain finetune models and evaluate models.",
#     # tools=[get_deepmd_train]
# )


# dpa_agent = 

# deepmd_rag_agent,

deepmd_structure_prepare_agent = LlmAgent(
    model=coding_model,
    name="deepmd_structure_prepare_agent",
    description="Deepmd structure prepare agent",
    instruction="""You are a specialized agent for DeepMD structure preparation in computational materials science and molecular dynamics simulations. 
        Usually using Lammps lmp format. simple struture can be visiualize by matplotlib

        **Core Capabilities:**
        1. **Code Generation**: Generate clean, runnable Python code for structure preparation tasks that users can immediately execute and modify in their Jupyter environment
        3. **User Guidance**: Help users clarify vague instructions by asking specific questions about their materials system, target properties, and simulation goals

        **Response Strategy:**
        - For well-defined requests: Generate complete Python code with clear comments and import statements
        - For ambiguous requests: Ask clarifying questions about crystal structure, composition, simulation type (NPT/NVT), target properties, etc.
        - For complex tasks: Break down into step-by-step instructions with code snippets
        - Always provide modifiable code that users can adapt to their specific needs

        **Technical Focus Areas:**
        - Crystal structure generation (bulk, surfaces, interfaces)
        - Defect structure creation (vacancies, interstitials, substitutions)
        - Molecular system preparation (solvation, ion placement)
        - File format conversions (POSCAR, xyz, lammps data)
        - Structure optimization and pre-relaxation

        Remember: Your users are researchers with programming skills working in Jupyter environments, you can always ask user to provide more information if you are not sure about the task.]
        You can also generate 
    """,
)

# deepmd_lammps_simulation_agent = LlmAgent(


deepmd_lammps_input_script_agent = LlmAgent(
    model=coding_model,
    name="deepmd_lammps_input_script_agent",
    description="Deepmd lammps input script agent. Generate the lammps input script for the given task.",
    instruction="""You are an agent that provides the deepmd lammps input script.
    You can generate the lammps input script for the given task.
    If your user ask you something that you do not know clearly, you can ask your user to provide more information.
    Remember: Your users ususally use the DPA3 models. the potential define part is usually like this:
    ```
    mass       1  15.9994  # Oxgen
    mass       2  1.008   # Hydrogen
    pair_style deepmd /public/DPA-3.1-3M/branch_models/H2O_H2O_PD.pth
    pair_coeff * * O H # Oxygen and Hydrogen in sequence.
    ```
    where H2O_H2O_PD.pth is the dpa model file. User may provide their own model file. Or tell you the correct format.
    the second line O H is the atom type. The sequence of the atom type is used by lammps atom type.
    This means atom type 1 is O Oxygen, atom type 2 is H Hydrogen.

    (execute comand like `lmp -i in.lammps` , and your user usually work in /workplace a shared directory or some subdirs of /workplace. ( This is a shared directory by the GPU compute server.)
    so you could tell the user to copy the lammps input script to the /workplace directory and run the command.

    You can also provide the command or generate the code and ask user to run the command in their environment.
    If error message suggest the MPI errors. The most posible is that lack of some files.. structure file, potential file, etc. check or ask the user to check it carefully.
    """,
    tools=[deepmd_lammps_mcp_toolset]
)

deepmd_lammps_simulations_agent = LlmAgent(
    model=coding_model,
    name="deepmd_lammps_simulations_agent",
    description="Deepmd simulations agent",
    instruction="""You are an agent that provides the deepmd lammps simulations.
    Usually you need short lammps simulation first to test the lammps simulation environment and the lammps input script. 
    And you can directly get the lammps output from the short lammps simulation.
    If the lammps input script is not valid, you can use the short lammps simulation to fix the lammps input script.
    You can disscuss with the user to fix the lammps input script.
    Tell the 

    Tell the user the main result in the lammps output or the major error messages.

    If the lammps simulation environment is working, you can use the long lammps simulation to perform the lammps simulation.
    The long lammps simulation is usually used for production use at the GPU server.

    And sometimes there are mistakes (files not found, incorrect format, etc.), 
    so use the deepmd_lammps_mcp_toolset to  test if the lammps input script is valid. 
    (execute comand like `lmp -i in.lammps` , and your user usually work in /workplace a shared directory or some subdirs of /workplace. ( This is a shared directory by the GPU compute server.)


    You can also provide the command  or generate the code and ask user to run the command in their environment .
    """,
    tools=[deepmd_lammps_mcp_toolset]
)

# deepmd_stucture_to_property_agent = LlmAgent(
#     model=model,
#     name="deepmd_stucture_to_property_agent",
#     description="Deepmd stucture to property agent",
#     instruction="You are an agent that provides the deepmd stucture to property.",
#     # subagents=[deepmd_structure_prepare_agent, deepmd_simulations_agent, deepmd_calculate_property_agent],
#     # tools=[get_deepmd_stucture_to_property]
# )

metainfo_agent = LlmAgent(
    model=general_model,
    name="metainfo_agent",
    description="Metainfo agent",
    instruction=("""You are an agent that provides the metainfo of this agent service. 
    showing function, source code, information, send feedback etc.""")
)

deepmd_lammps_dpa3_model_agent = LlmAgent(
    model=coding_model,
    name="deepmd_lammps_dpa3_model_agent",
    description="Deepmd lammps dpa3 model agent. Perform  the dpa3 model selecton, structure preparation, run lammps simulations, deepmd and dp related commands. and logs & data analysis.",
    instruction="""You are an agent that provides the deepmd dpa3 model.

    Your users are researchers with programming skills working in Jupyter environments, you can always ask user to provide more information if you are not sure about the task.
    you can also generate the code for the given task. (Your use can run the code in their Jupyter environment.)
    you can also use the deepmd_docs_rag_toolset to search the deepmd or some domain specific related docs and provide the correct information.(such as code, paper, release note, software usage, etc.)
    In order to help user to use the dpa3 model you need to do the following steps: (and some files or models may be directly provided by the user.)
    1. deepmd_docs_rag_agent: Sometime you need Query the deepmd docs with deepmd_docs_rag_agent agent to get the correct information (including code, paper, release note, software usage, etc.)
    2. deepmd_select_dpa_model_agent: select the best dpa3 model for the given task.  (There are some default dpa models provided by the developer but user can also use their own models.)
    3. deepmd_structure_prepare_agent: prepare the structure for the given task.
    4. deepmd_lammps_input_script_agent: to generate the lammps input script for the given task. (you can ask user to provide more details if you are not sure about the task.)
    5. deepmd_lammps_simulations_agent: run the lammps simulations. (usually you need short lammps simulation first to test the lammps simulation environment then long lammps simulation for production use)
    6. directlygenerate the analyze code and analyze the logs & data.
    If your user ask you something that you do not know clearly, you can just use the deepmd_lammps_mcp_toolset to search the deepmd docs and provide the correct information.
    """,
    sub_agents=[metainfo_agent, deepmd_docs_rag_agent, deepmd_structure_prepare_agent, deepmd_select_dpa_model_agent, deepmd_lammps_input_script_agent, deepmd_lammps_simulations_agent],
    tools=[deepmd_lammps_mcp_toolset, deepmd_docs_rag_toolset]
)


root_agent = deepmd_lammps_dpa3_model_agent


# google_search_tool_agent = LlmAgent(
#     model=model_original,
#     name="google_search_tool",
#     description="Google search tool",
#     instruction="You are an agent that provides the google search.",
#     tools=[google_search]
# )


# search_agent = Agent(
#     model='gemini-2.5-flash',
#     name='SearchAgent',
#     instruction="""
#     You're a spealist in Google Search
#     """,
#     tools=[google_search]
# )

# code_agent = Agent(
#     model='gemini-2.5-flash',
#     name='CodeAgent',
#     instruction="""
#     You're a specialist in Code Execution
#     """,
#     # tools=[BuiltInCodeExecutor()]
#     code_executor=BuiltInCodeExecutor()
# )
# root_agent = Agent(
#     name="RootAgent",
#     model="gemini-2.0-flash-exp",
#     description="Root Agent",
#     tools=[agent_tool.AgentTool(agent=search_agent), agent_tool.AgentTool(agent=code_agent)]
# )



# root_agent = LlmAgent(
#     model=general_model,
#     name="deepmd_root_agent",
#     description="Deepmd root agent",
#     instruction="""You are an agent that provides the deepmd related tasks. Follow the instructions and tools provided to you. 
#     Usually you need to perform the lammps simulations first to test the lammps simulation environment and the lammps input script.
#     Your users are researchers with programming skills working in Jupyter environments, you can always ask user to provide more information if you are not sure about the task. 
#     Or directly generate the code for the given task. (Your user can run these given code in their Jupyter environment.)
#     """,

#     sub_agents=[ deepmd_lammps_dpa3_model_agent],
    # code_executor=BuiltInCodeExecutor(),
    # tools=[BuiltInCodeExecutor()]
    # tools=[agent_tool.AgentTool(agent=search_agent), agent_tool.AgentTool(agent=code_agent)]
    # tools=[google_search]
# )