async def initialize_flow_state(state: FlowState) -> FlowState:
    logging.debug("Checking flow name.")
    task_response = state["task_response"]
    if "result" not in task_response or not task_response["result"]:
        raise ValueError("Task response is missing 'result' data.")

    short_description = task_response["result"][0].get("short_description")
    if not short_description:
        raise ValueError("Short description is missing in the task response.")

    try:
        with open("flow_details.yml", "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
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

    if short_description not in flow_map:
        logging.error(f"No flow found for: {short_description}")
        raise ValueError(f"No flow found for short description: {short_description}")

    mapping_data = flow_map[short_description]
    state["flow_name"] = mapping_data["flow_name"]
    logging.debug(f"Flow name determined: {state['flow_name']}")

    state["additional_variables"] = {"reassignment_group": mapping_data["reassignment_group"]}
    state["actions_list"] = []
    state["current_action"] = ""
    state["worknote_content"] = ""
    state["execution_log"] = []
    state["action_index"] = 0
    state["next_action"] = False
    state["error_occurred"] = False

    logging.debug(f"Initial additional_variables: {state['additional_variables']}")

    updated_state = await update_ticket_state(state, TicketState.WORK_IN_PROGRESS)
    return updated_state

def parse_powershell_output(powershell_response: dict, additional_variables: dict):
    """
    Parse JSON output from the PowerShell script and update additional_variables.
    Returns (updated_vars, worknote_content, error_occurred).
    """
    try:
        error_occurred = False
        if powershell_response["Status"] == "Success":
            try:
                powershell_output = json.loads(powershell_response["Outputs"] or "{}")
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
                error_occurred = True
        else:
            worknote_content = powershell_response["ErrorMessage"]
            error_occurred = True

        logging.debug(f"Updated additional_variables: {additional_variables}")
        return additional_variables, worknote_content, error_occurred
    except Exception as e:
        raise RuntimeError(f"Error parsing PowerShell execution: {e}")
