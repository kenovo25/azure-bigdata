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

        $InputFolderFiles = $FolderName + "/input/*"

        $FileList =  Get-AzureStorageBlob -Container $ContainerName -Blob $InputFolderFiles -Context $StorageAccount.Context

        Write-Output  "$($FileList.Count) file(s) to be checked for deletion from input folder."

        ForEach ($File in $FileList)
        {
            $FileName = Split-Path $File.Name -leaf
            If ($FileName –notmatch $FileRegex) 
            {
                $FolderFailedName = $FolderName + "/failed/" + $FileName
                $FileFailedExist = Get-AzureStorageBlob -Container $ContainerName -Blob $FolderFailedName -Context $StorageAccount.Context -ErrorAction SilentlyContinue
                if ($FileFailedExist)
                {
                    $copyState = Get-AzureStorageBlobCopyState -Blob $FolderFailedName -Container $ContainerName -Context $StorageAccount.Context -ErrorAction SilentlyContinue
                    if ($copyState.Status -eq "Success")
                    {
                        Write-Output "Copy of file $($File.Name) from input folder to $($FolderFailedName) finished. Deleting file from input folder "
                        Remove-AzureStorageBlob -Container $ContainerName -Blob $File.Name -Context $StorageAccount.Context
                    }
                    elseif (($copyState.Status -eq "Failed") -Or  ($copyState.Status -eq "Invalid") -Or ($copyState.Status -eq "Aborted"))
                    {
                        Write-Error "Error while copying file $($File.Name) from input folder to $($FolderFailedName) (copy status = $($copyState.Status)). File won't be deleted from input file since the next succeed copy."
                    }
                    else
                    {
                        Write-Output "Copy of file $($File.Name) from input folder to $($FolderFailedName) not finished. File won't be deleted from input file since the end of copy."
                    }                
                }
                else
                {
                    Write-Output "Copy of file $($File.Name) from input folder to $($FolderFailedName) not started. File won't be deleted from input file since the end of copy."
                }
            }
            Else
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
                $FolderValidatedName = $FolderName + "/validated/" + $OutputFileName


                $FileValidatedExist = Get-AzureStorageBlob -Container $ContainerName -Blob $FolderValidatedName -Context $StorageAccount.Context -ErrorAction SilentlyContinue
                if ($FileValidatedExist)
                {
                    $copyState = Get-AzureStorageBlobCopyState -Blob $FolderValidatedName -Container $ContainerName -Context $StorageAccount.Context -ErrorAction SilentlyContinue
                    if ($copyState.Status -eq "Success")
                    {
                        Write-Output "Copy of file $($File.Name) from input folder to $($FolderValidatedName) finished. Deleting file from input folder "
                        Remove-AzureStorageBlob -Container $ContainerName -Blob $File.Name -Context $StorageAccount.Context
                    }
                    elseif (($copyState.Status -eq "Failed") -Or  ($copyState.Status -eq "Invalid") -Or ($copyState.Status -eq "Aborted"))
                    {
                        Write-Error "Error while copying file $($File.Name) from input folder to $($FolderValidatedName) (copy status = $($copyState.Status)). File won't be deleted from input file since the next succeed copy."
                    }
                    else
                    {
                        Write-Output "Copy of file $($File.Name) from input folder to $($FolderValidatedName) not finished. File won't be deleted from input file since the end of copy."
                    }
                }
                else
                {
                    Write-Output "Copy of file $($File.Name) from input folder to $($FolderValidatedName) not started. File won't be deleted from input file since the end of copy."
                }
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
    
