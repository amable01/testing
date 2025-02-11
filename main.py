# import os
# import json
# import logging
# import yaml
# import asyncio
# import shlex
# from typing import Dict, Tuple, List, Any

# # Configure logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# # Load script type mappings from configuration file
# script_mappings: Dict[str, str] = {}
# try:
#     with open("script_mappings.yml", "r") as f:
#         config = yaml.safe_load(f)
#         script_mappings = config.get("mappings", {})
#         logging.debug(f"Loaded script mappings: {script_mappings}")
# except Exception as e:
#     logging.error(f"Failed to load script mappings: {e}")

# def format_command(interpreter_template: str, script_path: str, args: List[str], ext: str) -> str:
#     """
#     Format the command string based on the interpreter template and script arguments.
#     For PowerShell (.ps1), it wraps each argument in double quotes.
#     For other script types, it uses shlex.quote for safety.

#     Args:
#         interpreter_template (str): The template for the interpreter command.
#         script_path (str): The path to the script.
#         args (List[str]): The arguments to pass to the script.
#         ext (str): The file extension of the script.

#     Returns:
#         str: The formatted command string.
#     """
#     command = interpreter_template.format(script = script_path)


#     if args:
#         if ext == ".ps1":
#             formatted_args = " ".join(f'"{args}"' for arg in args)
#         else:
#             formatted_args = " ".join(shlex.quote(arg) for arg in args)
#         command = f"{command} {formatted_args}"
#     return command

# async def run_script(script_path: str, config_file_path: str) -> Dict[str, str]:
#     """
#     Runs a script based on its file extension using the correct interpreter.
#     Returns a dictionary with keys: Status, OutputMessage, and ErrorMessage.

#     Args:
#         script_path (str): The path to the script.
#         config_file_path (str): The path to the configuration file.

#     Returns:
#         Dict[str, str]: A dictionary containing the execution status, output, and error messages.
#     """
#     logging.debug(f"Running script: {script_path} with config file: {config_file_path}")
#     ext = os.path.splitext(script_path)[1].lower()
#     interpreter = script_mappings.get(ext)
#     if not interpreter:
#         error_msg = f"Unsupported script type: {ext}"
#         logging.error(error_msg)
#         return {"Status": "Error", "OutputMessage": "", "ErrorMessage": error_msg}

#     command = format_command(interpreter, script_path, [config_file_path], ext)
#     logging.debug(f"Executing command: {command}")
#     try:
#         process = await asyncio.create_subprocess_shell(
#             command,
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE
#         )
#         stdout, stderr = await process.communicate()
#         stdout_decoded = stdout.decode().strip() if stdout else ""
#         stderr_decoded = stderr.decode().strip() if stderr else ""
#         if stdout_decoded:
#             logging.debug(f"Command output: {stdout_decoded}")
#         if stderr_decoded:
#             logging.error(f"Command error: {stderr_decoded}")
#         status = "Success" if process.returncode == 0 else "Error"
#         return {"Status": status, "OutputMessage": stdout_decoded, "ErrorMessage": stderr_decoded}
#     except Exception as e:
#         logging.error(f"Failed to execute command: {e}")
#         return {"Status": "Error", "OutputMessage": "", "ErrorMessage": str(e)}

# def parse_script_output(response: Dict[str, str], additional_variables: Dict[str, Any]) -> Tuple[Dict[str, Any], str, bool]:
#     """
#     Parse JSON output from an executed script and update additional_variables.
#     Returns a tuple: (updated_variables, worknote_content, error_occurred).

#     Args:
#         response (Dict[str, str]): The response from the script execution.
#         additional_variables (Dict[str, Any]): Additional variables to update.

#     Returns:
#         Tuple[Dict[str, Any], str, bool]: A tuple containing the updated variables, worknote content, and error status.
#     """
#     try:
#         error_occurred = False
#         if response["Status"] == "Success":
#             try:
#                 # Parse the output as JSON.
#                 output_data = json.loads(response["OutputMessage"] or "{}")
#             except Exception as json_e:
#                 logging.error(f"JSON decode error: {json_e}")
#                 raise RuntimeError("Output is not valid JSON.")

#             if not isinstance(output_data, dict):
#                 raise RuntimeError("Parsed output is not a JSON object.")

#             if output_data.get("Status") == "Success":
#                 # Merge any additional keys (other than control keys) into additional_variables.
#                 for key, value in output_data.items():
#                     if key not in ["Status", "OutputMessage", "ErrorMessage"]:
#                         additional_variables[key] = value
#                 worknote_content = output_data.get("OutputMessage", "Execution Successful")
#             else:
#                 output_message = output_data.get("OutputMessage", "")
#                 error_message = output_data.get("ErrorMessage", "")
#                 worknote_content = f"{output_message}\n{error_message}".strip()
#                 error_occurred = True
#         else:
#             worknote_content = response.get("ErrorMessage", "Unknown error occurred.")
#             error_occurred = True
#         return additional_variables, worknote_content, error_occurred
#     except Exception as e:
#         raise RuntimeError(f"Error parsing script execution output: {e}")

# async def execute_flow_script(state: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Execute the current action script asynchronously.

#     Args:
#         state (Dict[str, Any]): The state dictionary containing execution details.

#     Returns:
#         Dict[str, Any]: The updated state dictionary.
#     """
#     logging.debug("Executing current action.")
#     idx = state.get("action_index", 0)
#     actions = state.get("actions_list", [])
#     additional_vars = state.get("additional_variables", {})
#     task_response = state.get("task_response", {})
#     config_file_path = state.get("config_file_path", "")

#     if idx < len(actions):
#         action_name = actions[idx]
#         action_path = os.path.join("UseCases", state.get("flow_name", ""), action_name)
#         logging.debug(f"Running action script: {action_path}")
#         try:
#             result = await run_script(action_path, config_file_path)

#             # Log the execution details.
#             state.setdefault("execution_log", []).append({
#                 "script": action_name,
#                 "Status": result.get("Status", ""),
#                 "OutputMessage": result.get("OutputMessage", ""),
#                 "ErrorMessage": result.get("ErrorMessage", "")
#             })

#             if result.get("Status") == "Error":
#                 logging.error(f"Error executing {action_name}: {result.get('ErrorMessage')}")
#                 state["worknote_content"] = f"Error in {action_name}: {result.get('ErrorMessage')}"
#                 state["error_occurred"] = True
#             else:
#                 updated_vars, note_content, error_occurred = parse_script_output(result, additional_vars)
#                 state["additional_variables"] = updated_vars
#                 state["worknote_content"] = note_content
#                 state["error_occurred"] = error_occurred
#         except Exception as e:
#             logging.error(f"Execution failed for {action_name}: {e}")
#             state["worknote_content"] = f"Execution failed for {action_name}: {e}"
#             state["error_occurred"] = True
#         finally:
#             # Move to the next action
#             state["action_index"] = idx + 1
#     else:
#         state["worknote_content"] = "All actions executed."
#         state["error_occurred"] = False

#     logging.debug(f"State after executing action: {state}")
#     return state

# async def main():
#     # Mock state for simulation. In a real scenario, this state might come from
#     # a workflow or external event. The YAML flows (like in Flow_mapping.yml) can
#     # be loaded and used to determine the 'flow_name' and other parameters.
#     state = {
#         "task_response": {
#             "result": {
#                 "description": "Select Users Email: user@example.com\nSecurity Group: example_group\nManaged By User: owner@example.com"
#             }
#         },
#         "flow_name": "example_flow",
#         "actions_list": ["example_script.ps1"],
#         "additional_variables": {},
#         "worknote_content": "",
#         "execution_log": [],
#         "action_index": 0,
#         "error_occurred": False,
#         "config_file_path": "testing/UseCases/example_flow/input.json"  # Update with the correct path to your input.json
#     }

#     # Execute the flow script
#     state = await execute_flow_script(state)
#     logging.info(f"Final State: {state}")

# if __name__ == "__main__":
#     asyncio.run(main())


import os
import json
import logging
import yaml
import asyncio
import shlex
from typing import Dict, List, Any

# -----------------------------------------------------------------------------
# Configure Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# -----------------------------------------------------------------------------
# Load Script Mappings from YAML Configuration
# -----------------------------------------------------------------------------
script_mappings: Dict[str, str] = {}
try:
    with open("script_mappings.yml", "r") as f:
        config = yaml.safe_load(f)
        script_mappings = config.get("mappings", {})
    logging.debug(f"Loaded script mappings: {script_mappings}")
except Exception as e:
    logging.error(f"Failed to load script mappings: {e}")

# -----------------------------------------------------------------------------
# Command Formatting Function
# -----------------------------------------------------------------------------
def format_command(interpreter_template: str, script_path: str, args: List[str], ext: str) -> str:
    """
    Constructs the command string.
    For PowerShell scripts, we force usage of the -File parameter and convert the script path to an absolute path.
    """
    if ext == ".ps1":
        # Convert to absolute path to avoid relative path issues
        abs_script_path = os.path.abspath(script_path)
        logging.debug(f"Absolute script path: {abs_script_path}")
        # Build the command using -File. We ignore the interpreter_template from the mapping.
        command = f'powershell -File "{abs_script_path}"'
    else:
        command = interpreter_template.format(script=script_path)

    if args:
        if ext == ".ps1":
            # Wrap each argument in double quotes (adjust as necessary)
            formatted_args = " ".join(f'"{arg}"' for arg in args)
        else:
            formatted_args = " ".join(shlex.quote(arg) for arg in args)
        command = f"{command} {formatted_args}"
    return command

# -----------------------------------------------------------------------------
# Script Runner
# -----------------------------------------------------------------------------
async def run_script(script_path: str, config_file_path: str) -> Dict[str, str]:
    """
    Runs a script based on its file extension using the appropriate interpreter.
    Returns a dictionary with keys: Status, OutputMessage, and ErrorMessage.
    """
    logging.debug(f"Running script: {script_path} with config file: {config_file_path}")
    ext = os.path.splitext(script_path)[1].lower()

    # For PowerShell (.ps1) force the use of the -File parameter regardless of mapping.
    if ext == ".ps1":
        interpreter = 'powershell -File "{script}"'
    else:
        interpreter = script_mappings.get(ext)

    if not interpreter:
        error_msg = f"Unsupported script type: {ext}"
        logging.error(error_msg)
        return {"Status": "Error", "OutputMessage": "", "ErrorMessage": error_msg}

    # Build the command string
    command = format_command(interpreter, script_path, [config_file_path], ext)
    logging.debug(f"Executing command: {command}")

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        stdout_decoded = stdout.decode().strip() if stdout else ""
        stderr_decoded = stderr.decode().strip() if stderr else ""

        if stdout_decoded:
            logging.debug(f"Command output: {stdout_decoded}")
        if stderr_decoded:
            logging.error(f"Command error: {stderr_decoded}")

        status = "Success" if process.returncode == 0 else "Error"
        return {"Status": status, "OutputMessage": stdout_decoded, "ErrorMessage": stderr_decoded}
    except Exception as e:
        logging.error(f"Failed to execute command: {e}")
        return {"Status": "Error", "OutputMessage": "", "ErrorMessage": str(e)}

# -----------------------------------------------------------------------------
# Example Function to Execute a Flow Script (for demonstration)
# -----------------------------------------------------------------------------
async def execute_flow_script(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the current action script asynchronously.
    The state dictionary must contain:
      - actions_list: a list of script filenames
      - action_index: the current index
      - flow_name: the folder name (under UseCases) where scripts reside
      - config_file_path: the path to the config file to pass to the script
    """
    logging.debug("Executing current action.")
    idx = state.get("action_index", 0)
    actions = state.get("actions_list", [])
    if idx < len(actions):
        action_name = actions[idx]
        # Build full path to the script
        script_dir = os.path.join("UseCases", state.get("flow_name", ""))
        script_path = os.path.join(script_dir, action_name)
        logging.debug(f"Running action script: {script_path}")

        if not os.path.exists(script_path):
            logging.error(f"Script file does not exist: {script_path}")
            state["worknote_content"] = f"Script file does not exist: {script_path}"
            state["error_occurred"] = True
            state["action_index"] = idx + 1
            return state

        try:
            result = await run_script(script_path, state.get("config_file_path", ""))
            # Log the execution details
            state.setdefault("execution_log", []).append({
                "script": action_name,
                "Status": result.get("Status", ""),
                "OutputMessage": result.get("OutputMessage", ""),
                "ErrorMessage": result.get("ErrorMessage", "")
            })
            if result.get("Status") == "Error":
                logging.error(f"Error executing {action_name}: {result.get('ErrorMessage')}")
                state["worknote_content"] = f"Error in {action_name}: {result.get('ErrorMessage')}"
                state["error_occurred"] = True
            else:
                state["worknote_content"] = result.get("OutputMessage", "Execution Successful")
                state["error_occurred"] = False
        except Exception as e:
            logging.error(f"Execution failed for {action_name}: {e}")
            state["worknote_content"] = f"Execution failed for {action_name}: {e}"
            state["error_occurred"] = True
        finally:
            state["action_index"] = idx + 1
    else:
        state["worknote_content"] = "All actions executed."
        state["error_occurred"] = False

    logging.debug(f"State after executing action: {state}")
    return state

# -----------------------------------------------------------------------------
# Main (for testing/demo)
# -----------------------------------------------------------------------------
async def main():
    # Build a demo state with an example .ps1 script
    state = {
        "task_response": {
            "result": {
                "description": "Select Users Email: user@example.com\nSecurity Group: example_group\nManaged By User: owner@example.com"
            }
        },
        "flow_name": "example_flow",  # Folder under UseCases
        "actions_list": ["example_script.ps1"],
        "additional_variables": {},
        "worknote_content": "",
        "execution_log": [],
        "action_index": 0,
        "error_occurred": False,
        "config_file_path": os.path.abspath("testing/input.json")  # Use absolute path if needed
    }
    # Execute the flow script
    state = await execute_flow_script(state)
    logging.info(f"Final State: {state}")

if __name__ == "__main__":
    asyncio.run(main())

