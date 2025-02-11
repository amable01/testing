param (
    [string]$configFilePath = "input.json"
)

$result = @{
    Status        = ""
    OutputMessage = ""
    ErrorMessage  = ""
    UsersToBeAdded= ""
    OwnerEmail    = ""
    UniqueGroupName = ""
}

# Validate the config file path
if (-Not (Test-Path -Path $configFilePath)) {
    $result.ErrorMessage = "Config file not found: $configFilePath"
    $result.Status = "Error"
    $resultJson = $result | ConvertTo-Json
    Write-Output $resultJson
    exit
}

try {
    # Read and parse the JSON configuration file
    $inputData = Get-Content -Path $configFilePath | ConvertFrom-Json

    # Extract taskResponse and additionalVariables from the input data
    $taskResponse = $inputData.taskResponse
    $additionalVariables = $inputData.additionalVariables

    $response_variables = $taskResponse.result.description
    $splitted_variable = $response_variables.Split("`n")

    foreach ($variable_line in $splitted_variable) {
        $parts = $variable_line.Split(":", 2)
        if ($parts.Count -lt 2) { continue }
        $variable_key = $parts[0].Trim()
        $variable_value = $parts[1].Trim()
        if ($variable_key -eq "") { continue }
        if ($variable_key -eq "Select Users Email") { $result['UsersToBeAdded'] = $variable_value }
        if ($variable_key -eq "Security Group") { $result['UniqueGroupName'] = $variable_value }
        if ($variable_key -eq "Managed By User") { $result['OwnerEmail'] = $variable_value }
    }

    $result.Status = "Success"
    $result.OutputMessage = "Mandatory parameters are parsed successfully."
} catch {
    $result.ErrorMessage = "ErrorCode: " + $_.Exception.Message
    $result.Status = "Error"
}

$resultJson = $result | ConvertTo-Json
Write-Output $resultJson
