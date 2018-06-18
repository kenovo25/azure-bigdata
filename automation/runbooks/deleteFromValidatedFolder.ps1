Param(
 [Parameter(Mandatory= $true)]
 [string]$FolderName,
 [Parameter(Mandatory= $true)]
 [string]$ContainerName,
 [Parameter(Mandatory= $true)]
 [string]$ADLSFolder
)

    try
    {
        
        $Conn = Get-AutomationConnection -Name AzureRunAsConnection
        $AzureRMAccount= Add-AzureRMAccount -ServicePrincipal -Tenant $Conn.TenantID `
        -ApplicationId $Conn.ApplicationID -CertificateThumbprint $Conn.CertificateThumbprint
       
	    $StorageResource = Find-AzureRmResource -TagName 'type_name'  -TagValue 'storageAccount'
        $StorageAccount = Get-AzureRmStorageAccount -ResourceGroupName $StorageResource.ResourceGroupName

        $ValidatedFolderFiles = $FolderName + "/validated/*"
        $FileList =  Get-AzureStorageBlob -Container $ContainerName -Blob $ValidatedFolderFiles -Context $StorageAccount.Context
		
		Write-Output  "$($FileList.Count) file(s) to be checked for deletion from validated folder."
		
		if ($FileList.Count -gt 0)
		{
			$ADLSResource = Find-AzureRmResource -TagName 'type' -TagValue 'dataLakeStore'
			
			# normaly the DF pipes use the startTime of their slice to create the folder in ADLS 
			# so on a day d, a DF activity copy a file from a vaidated blob into ALDS within a (d-1) folder
			# because the slice is from d-1 to d
			# so this delete runbook should check the validated blob vs a (d-1) folder and perhaps a (d-2) and (d-3) one 
			$day_1 = (get-date (get-date).AddDays(-1) -format 'yyyy/MM/dd')
			$day_2 = (get-date (get-date).AddDays(-2) -format 'yyyy/MM/dd')
			$day_3 = (get-date (get-date).AddDays(-3) -format 'yyyy/MM/dd')
			
			$ADLSPath_1 = '/PCISData/' + $ADLSFolder + '/Input/' + $day_1 + '/00'
			$ADLSPath_2 = '/PCISData/' + $ADLSFolder + '/Input/' + $day_2 + '/00'
			$ADLSPath_3 = '/PCISData/' + $ADLSFolder + '/Input/' + $day_3 + '/00'

            $ADLSFirstFolder = Test-AzureRmDataLakeStoreItem -Account $ADLSResource.Name -Path $ADLSPath_1

            # if there's authorization issues, the error is not catched by the try/catch
            # so we test if this boolean is null to see if there's an issue in the connection
            # $ADLSFirstFolder True : the folder exists
            # $ADLSFirstFolder False : the folder doesn't exists
            # $ADLSFirstFolder null : there's an issue
            if (!$ADLSFirstFolder){
                Write-Output "Error : $($ADLSFirstFolder)"
                $ErrorMessage = "Access Forbidden"
                throw $ErrorMessage
            }
            elseif ($ADLSFirstFolder){
                $ADLSlist_1 = Get-AzureRmDataLakeStoreChildItem -Account $ADLSResource.Name -Path $ADLSPath_1
            }

            # For each file in the Validated folder we search if it exists in ADLS
			ForEach ($File in $FileList)
			{
				$found = $FALSE
				$FileName = Split-Path $File.Name -leaf
                # if the file exists in the first ADLS folder tested, we stop here
                # else we look in the second ADLS folder, and so on
				if ($ADLSlist_1.Name -contains $FileName)
				{				
					$found = $TRUE
					$ADLSPath = $ADLSPath_1
				}
				else {
					if (Test-AzureRmDataLakeStoreItem -Account $ADLSResource.Name -Path $ADLSPath_2)
					{
						$ADLSlist_2 = Get-AzureRmDataLakeStoreChildItem -Account $ADLSResource.Name -Path $ADLSPath_2
					}
					if ($ADLSlist_2.Name -contains $FileName)
					{				
						$found = $TRUE
						$ADLSPath = $ADLSPath_2
					}
					else {
						if (Test-AzureRmDataLakeStoreItem -Account $ADLSResource.Name -Path $ADLSPath_3)
						{
							$ADLSlist_3 = Get-AzureRmDataLakeStoreChildItem -Account $ADLSResource.Name -Path $ADLSPath_3
							if ($ADLSlist_3.Name -contains $FileName)
							{				
								$found = $TRUE
								$ADLSPath = $ADLSPath_3
							}
						}
					}
				}
				
				if ($found) {
					Write-Output "Deleting file $($File.Name) from validated folder because it was found on ADLS in $($ADLSPath)."
					Remove-AzureStorageBlob -Container $ContainerName -Blob $File.Name -Context $StorageAccount.Context
				}
				else {
					Write-Output "File $($File.Name) from validated folder not removed because it wasn't found on ADLS in $($ADLSPath_1) nor in $($ADLSPath_2) nor in $($ADLSPath_3)."
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
    
