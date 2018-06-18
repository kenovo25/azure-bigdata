Param(
 [Parameter(Mandatory= $true)]
 [string]$FolderName,
 [Parameter(Mandatory= $true)]
 [string]$FileRegex,
 [Parameter(Mandatory= $true)]
 [string]$ContainerName,
 [Parameter(Mandatory= $true)]
 [string]$FileExtension,
 [Parameter(Mandatory= $true)]
 [int]$SEQPosition,
 [Parameter(Mandatory= $true)]
 [int]$SEQMaxSize
)

    try
    {
        $Conn = Get-AutomationConnection -Name AzureRunAsConnection
        $AzureRMAccount= Add-AzureRMAccount -ServicePrincipal -Tenant $Conn.TenantID `
        -ApplicationId $Conn.ApplicationID -CertificateThumbprint $Conn.CertificateThumbprint
       
	    $StorageResource = Find-AzureRmResource -TagName 'type_name'  -TagValue 'storageAccount'
        
        $StorageAccount = Get-AzureRmStorageAccount -ResourceGroupName $StorageResource.ResourceGroupName
        $StorageAccount
        $InputFolderFiles = $FolderName + "/input/*"

        $FileList =  Get-AzureStorageBlob -Container $ContainerName -Blob $InputFolderFiles -Context $StorageAccount.Context

        Write-Output  "$($FileList.Count) file(s) to be checked, renamed and copied."

        ForEach ($File in $FileList)
        {
            $FileName = Split-Path $File.Name -leaf

            If ($FileName –notmatch $FileRegex) 
            {
               Write-Error  "$($FileName) doesn't respect the file naming convention"
               $OuputName = $FolderName + "/failed/" + $FileName
               Write-Output "Starting to copy file $($FileName) to $($OuputName) at $(Get-Date)"
               $StartCopy = Start-AzureStorageBlobCopy -ICloudBlob $File.ICloudBlob -DestBlob  $OuputName -DestContainer $ContainerName -Context $StorageAccount.Context -Force             
            }
            else
            {
                if ($SEQMaxSize -ne 0)
                {
                    $SEQ = $FileName.split('_')[$SEQPosition].split('.')[0]
                    $NumberOfZeroToAdd = $SEQMaxSize - $SEQ.length
                    $OutputSEQ = "$('0' * $NumberOfZeroToAdd)$($SEQ)"
                    $OutputFileName = $FileName -replace "$($SEQ).$($FileExtension)", "$($OutputSEQ).$($FileExtension)"
                }
                else
                {
                  $OutputFileName = $FileName  
                }
                $OuputName = $FolderName + "/validated/" + $OutputFileName


                Write-Output "Starting to copy file $($FileName) to $($OuputName) at $(Get-Date)"
                $StartCopy = Start-AzureStorageBlobCopy -ICloudBlob $File.ICloudBlob -DestBlob  $OuputName -DestContainer $ContainerName -Context $StorageAccount.Context -Force
            }
        }
    }
    catch 
    {
        if (!$Conn)
        {
            $ErrorMessage = "Connection Not Found"
            throw $ErrorMessage
        }  
        else
        {
            Write-Error -Message $_.Exception
            throw $_.Exception
        }
    }
    
