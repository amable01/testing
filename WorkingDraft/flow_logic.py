import os
import json
import logging
import asyncio
import subprocess
import yaml
from enum import IntEnum
from typing import Literal
from typing_extensions import TypedDict
 
# Third-party libs
from dotenv import load_dotenv
 
# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
 
# -----------------------------------------------------------------------
# Configure Logging
# -----------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
 
# -----------------------------------------------------------------------
# Load Environment Variables
# -----------------------------------------------------------------------
load_dotenv()
user = os.getenv('SERVICENOW_USER')
pwd = os.getenv('SERVICENOW_PWD')
endpoint = "https://hexawaretechnologiesincdemo8.service-now.com"
db_path = os.getenv('DATABASE_PATH')
 
# -----------------------------------------------------------------------
# Define the FlowState
# -----------------------------------------------------------------------
class FlowState(TypedDict):
    task_response: dict
    flow_name: str
    actions_list: list
    current_action: str
    additional_variables: dict
    worknote_content: str
    execution_log: list  # We'll store logs & updates here
    action_index: int
    next_action: bool
    error_occurred: bool
    reassignment_group: str
 
# -----------------------------------------------------------------------
# Define TicketState
# -----------------------------------------------------------------------
class TicketState(IntEnum):
    PENDING = 0
    OPEN = 1
    WORK_IN_PROGRESS = 2
    CLOSED_COMPLETE = 3
    CLOSED_INCOMPLETE = 4
    CLOSED_SKIPPED = 5
    RESOLVED = 6


# Asynchronous Helper Functions
async def run_script(script_path: str, inputs: dict, task_response: dict) -> dict:
    """
    Execute a script based on its file extension asynchronously.
    Supports:
      - Python (.py): Runs with 'python' interpreter; inputs passed as a JSON string.
      - Node.js (.js): Runs with 'node' interpreter; inputs passed as a JSON string.
      - PowerShell (.ps1): Runs with 'powershell'; inputs passed as individual key-value arguments.

    Args:
        script_path (str): Path to the script file.
        inputs (dict): Input data for the script.

    Returns:
        dict: Execution result containing:
            - Status: "Success" or "Error"
            - OutputMessage: Parsed outputs from the script (if available)
            - ErrorMessage: Any error message encountered
    """
    if not os.path.exists(script_path):
        error_msg = f"Script file not found: {script_path}"
        logging.error(error_msg)
        return {"Status": "Error", "OutputMessage": {}, "ErrorMessage": error_msg}

    ext = os.path.splitext(script_path)[1].lower()

    try:
        if ext == ".py":

            script_dir = os.path.dirname(script_path)
            venv_dir = os.path.join(script_dir, 'venv')
            venv_dir = os.path.abspath(venv_dir)
            logging.info(f"Using virtual environment at: {venv_dir}")

            python_executable = os.path.join(venv_dir, 'Scripts', 'python.exe')
            if not os.path.exists(python_executable):
                return {"Status": "Error", "OutputMessage": {}, "ErrorMessage": f"Python executable not found at: {python_executable}"}

            # Run the script
            inputs_json = json.dumps(inputs)
            command = [python_executable, os.path.abspath(script_path), inputs_json]
            logging.info(f"Executing command: {' '.join(command)}")

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=script_dir
            )
            stdout, stderr = await process.communicate()

            print(stderr)
            print(stdout)

            if process.returncode == 0:
                try:
                    outputs = json.loads(stdout.decode().strip())
                except json.JSONDecodeError:
                    outputs = stdout.decode().strip()
                return {"Status": "Success", "OutputMessage": outputs, "ErrorMessage": ""}
            else:
                return {"Status": "Error", "OutputMessage": {}, "ErrorMessage": stderr.decode().strip()}
        
        elif ext == ".js":
            inputs_json = json.dumps(inputs)
            command = ["node", script_path, inputs_json]

        elif ext == ".ps1":
            header = (
                f"$jsonObject = '{json.dumps(task_response)}' | ConvertFrom-Json; "
                f"$SCTASK_RESPONSE = $jsonObject.result; "
                f"$ADDITIONAL_VARIABLES = '{json.dumps(inputs)}' | ConvertFrom-Json; "
            )
            with open(script_path, 'r') as script_file:
                file_content = script_file.read()

            powershell_script = header + file_content

            return await run_powershell_command(powershell_script)
        else:
            error_msg = f"Unsupported script file type: {ext}"
            logging.error(error_msg)
            return {"Status": "Error", "OutputMessage": {}, "ErrorMessage": error_msg}

        logging.info(f"Executing command: {' '.join(command)}")
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        stdout_decoded = stdout.decode().strip().replace('\r\n',' ')
        stderr_decoded = stderr.decode().strip().replace('\r\n',' ')

        if process.returncode == 0:
            try:
                outputs = json.loads(stdout_decoded)
            except json.JSONDecodeError:
                outputs = stdout_decoded
            return {"Status": "Success", "OutputMessage": outputs, "ErrorMessage": ""}
        else:
            logging.error(f"Script execution error: {stderr_decoded}")
            return {"Status": "Error", "OutputMessage": {}, "ErrorMessage": stderr_decoded}

    except Exception as e:
        logging.error(f"Exception occurred during script execution: {e}")
        return {"Status": "Error", "OutputMessage": {}, "ErrorMessage": str(e)}


# -----------------------------------------------------------------------
# Asynchronous Helper Functions
# -----------------------------------------------------------------------
async def run_powershell_command(command: str):
    """Execute a PowerShell command and return status and output."""
    try:
        logging.debug(f"Executing PowerShell command: {command}")
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True
        )
        return {
            "Status": "Success" if result.returncode == 0 else "Error",
            "OutputMessage": result.stdout.strip(),
            "ErrorMessage": result.stderr.strip(),
        }
    except Exception as e:
        return {
            "Status": "Error",
            "OutputMessage": "",
            "ErrorMessage": str(e)
        }
 
def parse_powershell_output(powershell_response: dict, additional_variables: dict):
    """
    Parse JSON output from the PowerShell script and update additional_variables.
    Returns (updated_vars, worknote_content, error_occurred).
    """
    try:
        error_occured = False
        if powershell_response["Status"] == "Success":
            # Try to load the output as JSON.
            try:
                powershell_output = json.loads(powershell_response["OutputMessage"] or "{}")
            except Exception as json_e:
                logging.error(f"JSON decode error: {json_e}")
                raise RuntimeError("Output is not valid JSON.")
 
            if not isinstance(powershell_output, dict):
                powershell_output = json.loads(powershell_output)
 
            if powershell_output.get("Status") == "Success":
                additional_variables.update(powershell_output)
                worknote_content = powershell_output.get("OutputMessage", "Execution Successful")
            else:
                OutputMessage = powershell_output.get("OutputMessage", "")
                ErrorMessage = powershell_output.get("ErrorMessage", "")
                worknote_content = f"{OutputMessage}\n{ErrorMessage}"
                error_occured = True
        else:
            worknote_content = powershell_response["ErrorMessage"]
        return additional_variables, worknote_content, error_occured
    except Exception as e:
        raise RuntimeError(f"Error parsing PowerShell execution: {e}")
 
# -----------------------------------------------------------------------
# Flow Node Functions (Async)
# -----------------------------------------------------------------------
import httpx
 
async def initialize_flow_state(state: FlowState) -> FlowState:
    """
    Determine the flow name from the short_description and initialize the state.
    Now reading from a YAML file instead of CSV.
    """
    logging.debug("Checking flow name.")
    task_response = state["task_response"]
    if "result" not in task_response or not task_response["result"]:
        raise ValueError("Task response is missing 'result' data.")
 
    short_description = task_response["result"][0].get("short_description")
    if not short_description:
        raise ValueError("Short description is missing in the task response.")
 
    # --- Load from YAML ---
    try:
        with open("flow_details.yml", "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)  # e.g., {"flows": [ {...}, {...} ]}
            # Create a dict that maps a short_description -> { flow_name, reassignment_group, ... }
            flow_map = {
                item["short_description"]: {
                    "flow_name": item["flow_name"],
                    "reassignment_group": item["reassignment_group"],
                }
                for item in yaml_data.get("flows", [])
            }
    except FileNotFoundError:
        raise ValueError("flow_details.yml file not found.")
    except KeyError as e:
        raise ValueError(f"Missing key in flow_details.yml: {e}")
 
    # Lookup the short_description
    if short_description not in flow_map:
        logging.error(f"No flow found for: {short_description}")
        raise ValueError(f"No flow found for short description: {short_description}")
 
    mapping_data = flow_map[short_description]
    state["flow_name"] = mapping_data["flow_name"]
    logging.debug(f"Flow name determined: {state['flow_name']}")
 
    # Optionally store the reassignment_group in state["additional_variables"]
    state["reassignment_group"] = mapping_data["reassignment_group"]
 
    # Initialize state fields
    state["actions_list"] = []
    state["current_action"] = ""
    state["worknote_content"] = ""
    state["execution_log"] = []
    state["action_index"] = 0
    state["next_action"] = False
    state["error_occurred"] = False
    state["additional_variables"] = {}
 
    # Mark ticket as WORK_IN_PROGRESS
    updated_state = await update_ticket_state(state, TicketState.WORK_IN_PROGRESS)
    return updated_state
 
async def update_ticket_state(state: FlowState, task_state: TicketState) -> FlowState:
    """
    Update the ticket state in ServiceNow using the given task_state and log the change.
    """
    try:
        task_response = state["task_response"]
        state_request = {"state": str(task_state.value)}
        updated_state_json = json.dumps(state_request)
 
        table_name = task_response["result"][0]["sys_class_name"]
        sys_id = task_response["result"][0]["sys_id"]
 
        url = f"{endpoint}/api/now/table/{table_name}/{sys_id}"
        async with httpx.AsyncClient() as client:
            auth = (user, pwd)
            resp = await client.put(
                url,
                auth=auth,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                content=updated_state_json
            )
            if resp.status_code != 200:
                raise Exception(f"Failed to update state: {resp.json()}")
 
        state["worknote_content"] = "Worknotes updated successfully"
        # Log the updated ticket state in execution_log
        state["execution_log"].append({
            "action": "update_ticket_state",
            "ticket_state_value": task_state.value,
            "ticket_state_name": task_state.name,
            "description": f"Ticket state successfully updated to {task_state.name} ({task_state.value})."
        })
    except Exception as e:
        raise RuntimeError(f"Error updating state: {e}")
    return state
 
async def retrieve_flow_scripts(state: FlowState) -> FlowState:
    """Fetch PowerShell scripts from UseCases/<flow_name>."""
    logging.debug("Fetching actions for the flow.")
    flow_dir = "UseCases"
    try:
        actions_dir = os.path.join(flow_dir, state["flow_name"])
        actions_list = os.listdir(actions_dir)
    except Exception as e:
        logging.error(f"Error fetching actions: {e}")
        raise RuntimeError(f"Error fetching actions: {e}")
 
    state["actions_list"] = actions_list
    logging.debug(f"Actions found: {actions_list}")
    return state
 
async def evaluate_flow_decision(state: FlowState) -> FlowState:
    """Decide whether to continue or end the flow."""
    logging.debug("Assistant node: deciding next step.")
    if state["error_occurred"]:
        state["next_action"] = False
        updated_state = await update_servicenow_assignment_group(state)
        logging.debug("Assistant: error_occured=True, will end flow.")
        return updated_state
 
    if state["action_index"] < len(state["actions_list"]):
        state["next_action"] = True
        state["current_action"] = state["actions_list"][state["action_index"]]
        logging.debug(f"Assistant: next_action=True. Next script: {state['current_action']}")
    else:
        state["next_action"] = False
        state["current_action"] = ""
        state = await update_ticket_state(state, TicketState.CLOSED_COMPLETE)
        logging.debug("Assistant: no more actions, ending flow.")
 
    return state

async def execute_flow_script(state: FlowState) -> FlowState:
    """
    Executes the current script in the workflow and updates the FlowState accordingly.
    Only executes .ps1, .py, and .js files.
    
    Args:
        state (FlowState): The current state of the workflow, containing action index,
                           actions list, variables, and other relevant data.
    
    Returns:
        FlowState: The updated state after executing the script.
    """
    logging.debug("Executing current action.")
    
    # Retrieve necessary variables from the state
    idx = state["action_index"]
    actions = state["actions_list"]
    additional_vars = state["additional_variables"]
    task_response = state["task_response"]
    flow_name = state["flow_name"]
    
    # Get the current action to execute
    action_name = actions[idx]
    action_path = os.path.join("UseCases", flow_name, action_name)
    logging.debug(f"Checking action script: {action_path}")
    
    # Define allowed file extensions
    allowed_extensions = ('.ps1', '.py', '.js')
    
    # Check if the file has an allowed extension
    if not action_path.lower().endswith(allowed_extensions):
        logging.warning(f"Skipping {action_name}: Unsupported file type")
        state["execution_log"].append({
            "script": action_name,
            "Status": "Skipped",
            "OutputMessage": "Unsupported file type - only .ps1, .py, and .js are allowed",
            "ErrorMessage": ""
        })
        state["worknote_content"] = f"Skipped {action_name}: Unsupported file type"
        state["action_index"] = idx + 1
        return state
    
    try:
        logging.debug(f"Running action script: {action_path}")
        # Execute the script asynchronously
        ps_result = await run_script(action_path, additional_vars, task_response)
        
        # Log the execution result in the state's execution log
        state["execution_log"].append({
            "script": action_name,
            "Status": ps_result["Status"],
            "OutputMessage": ps_result["OutputMessage"],
            "ErrorMessage": ps_result["ErrorMessage"]
        })
        
        if ps_result["Status"] == "Error":
            # Handle error case for all script types
            logging.error(f"Error executing {action_name}: {ps_result['ErrorMessage']}")
            state["worknote_content"] = f"Error in {action_name}: {ps_result['ErrorMessage']}"
            state["error_occurred"] = True
        else:
            # Handle success case uniformly
            output = ps_result["OutputMessage"]
            if isinstance(output, str):
                try:
                    # Attempt to parse as JSON (e.g., PowerShell output)
                    output = json.loads(output)
                except json.JSONDecodeError:
                    # If not JSON, use the string directly as the success message
                    state["worknote_content"] = output
                    state["error_occurred"] = False
                else:
                    # Parsed as dictionary
                    if output.get("Status") == "Success":
                        state["additional_variables"].update(output)
                        state["worknote_content"] = output.get("OutputMessage", "Execution Successful")
                        state["error_occurred"] = False
                    else:
                        state["worknote_content"] = f"{output.get('OutputMessage', '')}\n{output.get('ErrorMessage', '')}"
                        state["error_occurred"] = True
            elif isinstance(output, dict):
                # Output is already a dictionary (e.g., Python/Node.js JSON output)
                if output.get("Status") == "Success":
                    state["additional_variables"].update(output)
                    state["worknote_content"] = output.get("OutputMessage", "Execution Successful")
                    state["error_occurred"] = False
                else:
                    state["worknote_content"] = f"{output.get('OutputMessage', '')}\n{output.get('ErrorMessage', '')}"
                    state["error_occurred"] = True
            else:
                # Fallback: convert unexpected types to string
                state["worknote_content"] = str(output)
                state["error_occurred"] = False
    
    except Exception as e:
        # Handle any exceptions during execution
        logging.error(f"Execution failed for {action_name}: {e}")
        state["worknote_content"] = f"Execution failed for {action_name}: {e}"
        state["error_occurred"] = True
    
    # Increment the action index for the next iteration
    state["action_index"] = idx + 1
    
    return state
 
async def update_servicenow_worknotes(state: FlowState) -> FlowState:
    """Update the ServiceNow record's worknotes with the result of the action."""
    logging.debug("Updating worknotes on ServiceNow.")
    try:
        task_response = state["task_response"]
        content = state["worknote_content"]
 
        table_name = task_response["result"][0]["sys_class_name"]
        sys_id = task_response["result"][0]["sys_id"]
        url = f"{endpoint}/api/now/table/{table_name}/{sys_id}"
 
        body = {"work_notes": content}
 
        async with httpx.AsyncClient() as client:
            auth = (user, pwd)
            resp = await client.put(
                url,
                auth=auth,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json=body
            )
            if resp.status_code != 200:
                logging.error(f"Failed to update worknotes: {resp.json()}")
                raise Exception(f"Failed to update worknotes: {resp.json()}")
 
        state["worknote_content"] = "Worknotes updated successfully"
    except Exception as e:
        logging.error(f"Error updating worknotes: {e}")
        raise RuntimeError(f"Error updating worknotes: {e}")
 
    logging.debug(f"State after updating worknotes: {state}")
    return state
 

async def update_servicenow_assignment_group(state: FlowState):
    try:
        task_response = state["task_response"]
        reassignment_group_sys_id = state["reassignment_group"]
        data = {"assignment_group": reassignment_group_sys_id}
 
        table_name = task_response["result"][0]["sys_class_name"]
        sys_id = task_response["result"][0]["sys_id"]
        url = f"{endpoint}/api/now/table/{table_name}/{sys_id}"
 
        async with httpx.AsyncClient() as client:
            auth = (user, pwd)
            resp = await client.put(
                url,
                auth=auth,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                data=json.dumps(data)
            )
            if resp.status_code != 200:
                raise Exception(f"Failed to update assignment group: {resp.json()}")
 
        state["worknote_content"] = "Worknotes updated successfully"
        # Log the updated ticket state in execution_log
        state["execution_log"].append({
            "action": "update_servicenow_assignment_group",
        })
    except Exception as e:
        raise RuntimeError(f"Error updating assignment group: {e}")
    return state
 
# -----------------------------------------------------------------------
# Decide Whether to Continue or End
# -----------------------------------------------------------------------
def determine_flow_outcome(state: FlowState) -> Literal["execute_flow_script", END]:  # type: ignore
    return "execute_flow_script" if state["next_action"] else END
 
# -----------------------------------------------------------------------
# Build and Compile the StateGraph
# -----------------------------------------------------------------------
builder = StateGraph(FlowState)
 
builder.add_node("initialize_flow_state", initialize_flow_state)
builder.add_node("retrieve_flow_scripts", retrieve_flow_scripts)
builder.add_node("evaluate_flow_decision", evaluate_flow_decision)
builder.add_node("execute_flow_script", execute_flow_script)
builder.add_node("update_servicenow_worknotes", update_servicenow_worknotes)
 
builder.add_edge(START, "initialize_flow_state")
builder.add_edge("initialize_flow_state", "retrieve_flow_scripts")
builder.add_edge("retrieve_flow_scripts", "evaluate_flow_decision")
builder.add_conditional_edges("evaluate_flow_decision", determine_flow_outcome)
builder.add_edge("execute_flow_script", "update_servicenow_worknotes")
builder.add_edge("update_servicenow_worknotes", "evaluate_flow_decision")
 
# We will keep a reference to a compiled graph, but we initialize it via `init_graph()`.
_graph = None
 
async def init_graph():
    """
    Initialize and return the compiled StateGraph with the AsyncSqliteSaver.
    This will be called once in the FastAPI startup event.
    """
    global _graph
    if _graph is None:
        import aiosqlite
        conn = await aiosqlite.connect(db_path, check_same_thread=False)
        memory = AsyncSqliteSaver(conn)
        _graph = builder.compile(checkpointer=memory)
    return _graph
