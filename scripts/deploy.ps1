param(
    [string]$StackName='air-guardian-pilot', [string]$Region='ap-south-1',
    [string]$Profile='', [string]$ExpectedAccount='',
    [string]$ParametersFile='deployment/pilot.parameters.yaml', [switch]$BuildOnly,
    [switch]$UseBuiltArtifacts
)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed ($LASTEXITCODE)" }
}
if ($Profile) { $env:AWS_PROFILE=$Profile }
$env:AWS_DEFAULT_REGION=$Region
if (-not $BuildOnly) {
    $identity = & aws sts get-caller-identity --region $Region --output json
    if ($LASTEXITCODE) { throw 'Authenticate with aws login, then rerun this script.' }
    $account = ($identity | ConvertFrom-Json).Account
    if ($ExpectedAccount -and $account -ne $ExpectedAccount) { throw 'Authenticated account does not match ExpectedAccount.' }
    Write-Host "Deploying to AWS account $account in $Region"
}
if (-not $UseBuiltArtifacts) {
    Invoke-Checked python @('scripts/run_cloud_tests.py')
    Invoke-Checked python @('scripts/package_cloud.py')
    Invoke-Checked sam @('validate','--lint','--template-file','template.yaml','--region',$Region)
    Invoke-Checked docker @('info','--format','{{.ServerVersion}}')
    Invoke-Checked sam @('build','--use-container','--template-file','template.yaml')
} else {
    Invoke-Checked sam @('validate','--lint','--template-file','.aws-sam/build/template.yaml','--region',$Region)
    Invoke-Checked docker @('info','--format','{{.ServerVersion}}')
}
$runtimePath = (Resolve-Path '.aws-sam/build/ApiFunction').Path
Invoke-Checked docker @('run','--rm','--platform','linux/arm64','--entrypoint','python',
    '-v',"${runtimePath}:/var/task:ro",'public.ecr.aws/lambda/python:3.12',
    '-c','import cloud.api, cloud.pipeline, cloud.notifications, pywebpush, cryptography; print("ARM64 runtime imports passed")')
if ($BuildOnly) { return }
Invoke-Checked sam @('deploy','--template-file','.aws-sam/build/template.yaml',
    '--stack-name',$StackName,'--region',$Region,'--resolve-s3','--capabilities','CAPABILITY_IAM',
    '--no-fail-on-empty-changeset','--parameter-overrides',"file://$ParametersFile")
Invoke-Checked python @('scripts/package_cloud.py','--stack',$StackName,'--region',$Region)
$stack = & aws cloudformation describe-stacks --stack-name $StackName --region $Region --output json
if ($LASTEXITCODE) { throw 'Cannot read deployed stack outputs.' }
$outputs = @{}
($stack | ConvertFrom-Json).Stacks[0].Outputs | ForEach-Object { $outputs[$_.OutputKey]=$_.OutputValue }
if ($outputs.WebBucketName -and $outputs.DistributionId) {
    Invoke-Checked aws @('s3','sync','dist',"s3://$($outputs.WebBucketName)",'--cache-control','no-cache','--region',$Region)
    Invoke-Checked aws @('cloudfront','create-invalidation','--distribution-id',$outputs.DistributionId,'--paths','/*')
} else {
    Write-Host 'Backend deployed. Public hosting awaits CloudFront account verification. Serve dist on localhost:5191 for live-backend testing.'
}
& python scripts/verify_deployment.py --stack $StackName --region $Region
if ($LASTEXITCODE -ne 0) { Write-Host 'Stack deployment succeeded; rollout checks remain pending. See the verification report.' }
if ($outputs.DistributionId) {
    Write-Host "Published $($outputs.Website)/cloud.html. Sign up and verify the administrator email before school bootstrap."
} else {
    Write-Host "Live backend test origin: $($outputs.Website)/cloud.html. Public hosting is pending."
}
