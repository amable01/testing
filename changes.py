def parse_powershell_output(powershell_response: dict, additional_variables: dict):
    """
    Parse output from the PowerShell script and update additional_variables.
    Returns (updated_vars, worknote_content, error_occurred).
    """
    try:
        error_occurred = False
        worknote_content = ""

        if powershell_response["Status"] == "Success":
            powershell_output = powershell_response["Outputs"]

            # Check if the output is None or empty
            if powershell_output is None:
                worknote_content = "PowerShell script returned null output."
                error_occurred = True
                return additional_variables, worknote_content, error_occurred

            # Check if the output is already a dictionary
            if isinstance(powershell_output, dict):
                parsed_output = powershell_output
            elif isinstance(powershell_output, str):
                # Attempt to parse the output as JSON
                try:
                    parsed_output = json.loads(powershell_output)
                except json.JSONDecodeError as json_e:
                    logging.error(f"JSON decode error: {json_e}")
                    worknote_content = f"Output is not valid JSON: {powershell_output}"
                    error_occurred = True
                    return additional_variables, worknote_content, error_occurred
            else:
                worknote_content = f"Unexpected output type: {type(powershell_output)}"
                error_occurred = True
                return additional_variables, worknote_content, error_occurred

            if isinstance(parsed_output, dict):
                if parsed_output.get("Status") == "Success":
                    additional_variables.update(parsed_output)
                    worknote_content = parsed_output.get("OutputMessage", "Execution Successful")
                else:
                    OutputMessage = parsed_output.get("OutputMessage", "")
                    ErrorMessage = parsed_output.get("ErrorMessage", "")
                    worknote_content = f"{OutputMessage}\n{ErrorMessage}"
                    error_occurred = True
            else:
                worknote_content = f"Unexpected output format: {parsed_output}"
                error_occurred = True
        else:
            worknote_content = powershell_response["ErrorMessage"]
            error_occurred = True

        logging.debug(f"Updated additional_variables: {additional_variables}")
        return additional_variables, worknote_content, error_occurred
    except Exception as e:
        raise RuntimeError(f"Error parsing PowerShell execution: {e}")
