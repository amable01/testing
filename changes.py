def parse_powershell_output(powershell_response: dict, additional_variables: dict):
    """
    Parse JSON output from the PowerShell script and update additional_variables.
    Returns (updated_vars, worknote_content, error_occurred).
    """
    try:
        error_occurred = False
        worknote_content = ""

        if powershell_response["Status"] == "Success":
            try:
                # Attempt to parse the output as JSON
                powershell_output = json.loads(powershell_response["Outputs"])
            except json.JSONDecodeError as json_e:
                logging.error(f"JSON decode error: {json_e}")
                powershell_output = powershell_response["Outputs"]
                worknote_content = f"Output is not valid JSON: {powershell_output}"
                error_occurred = True

            if isinstance(powershell_output, dict):
                if powershell_output.get("Status") == "Success":
                    additional_variables.update(powershell_output)
                    worknote_content = powershell_output.get("OutputMessage", "Execution Successful")
                else:
                    OutputMessage = powershell_output.get("OutputMessage", "")
                    ErrorMessage = powershell_output.get("ErrorMessage", "")
                    worknote_content = f"{OutputMessage}\n{ErrorMessage}"
                    error_occurred = True
            else:
                worknote_content = f"Unexpected output format: {powershell_output}"
                error_occurred = True
        else:
            worknote_content = powershell_response["ErrorMessage"]
            error_occurred = True

        logging.debug(f"Updated additional_variables: {additional_variables}")
        return additional_variables, worknote_content, error_occurred
    except Exception as e:
        raise RuntimeError(f"Error parsing PowerShell execution: {e}")
