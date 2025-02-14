param (
    [string]$jsonObject,
    [string]$additionalVariables
)

$result = @{
    Status            = ""
    OutputMessage     = ""
    ErrorMessage      = ""
    Userstobeadded    = ""
    OwnerEmail        = ""
    uniquegroupname   = ""
}

try {
    $response_variables = $SCTASK_RESPONSE.description
    $splitted_variable = $response_variables.split("`n")

    foreach ($variable_line in $splitted_variable) {
        $variable_key = $variable_line.split(":")[0].trim()
        $variable_value = $variable_line.split(":")[1].trim()

        if ($variable_key -eq "") {
            continue
        }

        if ($variable_key -eq "Select Users Email") {
            $result['Userstobeadded'] = $variable_value
        }
        if ($variable_key -eq "Security Group") {
            $result['uniquegroupname'] = $variable_value
        }
        if ($variable_key -eq "Managed By User") {
            $result['OwnerEmail'] = $variable_value
        }
    }

    $result.Status = "Success"
    $result.OutputMessage = "Mandatory parameters are parsed successfully."
}
catch {
    $result.ErrorMessage = "ErrorCode: " + $_.Exception.Message
    $result.Status = "Error"
}

$result | ConvertTo-Json -Compress










async def run_script(script_path: str, inputs: dict) -> dict:
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
            - Outputs: Parsed outputs from the script (if available)
            - ErrorMessage: Any error message encountered
    """
    if not os.path.exists(script_path):
        error_msg = f"Script file not found: {script_path}"
        logging.error(error_msg)
        return {"Status": "Error", "Outputs": None, "ErrorMessage": error_msg}

    ext = os.path.splitext(script_path)[1].lower()

    try:
        if ext in [".py", ".js"]:
            interpreter = "python" if ext == ".py" else "node"
            inputs_json = json.dumps(inputs)
            command = [interpreter, script_path, inputs_json]
        elif ext == ".ps1":
            command = ["powershell", "-File", script_path]
            for key, value in inputs.items():
                command.extend([f"-{key}", str(value)])
        else:
            error_msg = f"Unsupported script file type: {ext}"
            logging.error(error_msg)
            return {"Status": "Error", "Outputs": None, "ErrorMessage": error_msg}

        logging.info(f"Executing command: {' '.join(command)}")
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        stdout_decoded = stdout.decode().strip().replace('\r\n', ' ')
        stderr_decoded = stderr.decode().strip().replace('\r\n', ' ')

        if process.returncode == 0:
            try:
                outputs = json.loads(stdout_decoded)
            except json.JSONDecodeError:
                outputs = stdout_decoded
            return {"Status": "Success", "Outputs": outputs, "ErrorMessage": ""}
        else:
            logging.error(f"Script execution error: {stderr_decoded}")
            return {"Status": "Error", "Outputs": None, "ErrorMessage": stderr_decoded}

    except Exception as e:
        logging.error(f"Exception occurred during script execution: {e}")
        return {"Status": "Error", "Outputs": None, "ErrorMessage": str(e)}















def parse_powershell_output(powershell_response: dict, additional_variables: dict):
    """
    Parse output from the PowerShell script and update additional_variables.
    Returns (updated_vars, worknote_content, error_occurred).
    """
    try:
        error_occurred = False
        worknote_content = ""

        if powershell_response["Status"] == "Success":
            powershell_output = powershell_response.get("Outputs")

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
                    additional_variables.update({
                        "Userstobeadded": parsed_output.get("Userstobeadded", ""),
                        "uniquegroupname": parsed_output.get("uniquegroupname", ""),
                        "OwnerEmail": parsed_output.get("OwnerEmail", "")
                    })
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
