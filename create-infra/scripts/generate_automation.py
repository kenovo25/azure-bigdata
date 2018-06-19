#!/bin/env python

# recreates the resource for a Azure Automation (1.0) Arm deployment 
# from resources that were grabbed (manually) from the portal

from sys import stdout;
from os import listdir;
from os.path import isfile, join, basename, splitext;
from datetime import datetime, timedelta

import sys
import getopt
import json
import uuid
import copy

def main():

  try: 
     opts, args = getopt.getopt(sys.argv[1:], '', ['automation_name=', 'location=', 'client_id=', 'tenant=', 'subscription_id=', 'certificate_base64=', 'certificate_thumbprint=', 'storage_account='])
  except getopt.GetOptError:
    usage()
    print("here")
    sys.exit(2)

  for opt, arg in opts:
    if opt in ('--automation_name'):
      automation_name = arg
    elif opt in ('--location'):
      location = arg
    elif opt in ('--client_id'):
      client_id = arg
    elif opt in ('--tenant'):
      tenant = arg
    elif opt in ('--subscription_id'):
      subscription_id = arg
    elif opt in ('--certificate_base64'):
      certificate_base64 = arg
    elif opt in ('--certificate_thumbprint'):
      certificate_thumbprint = arg
    elif opt in ('--storage_account'):
      storage_account = arg
    else:
      print("there") 
      usage()
      sys.exit(2)
	  
  arm_resources = [] 
  
  #inject connection
  #arm_resources.append(azureAutomationCertificate(location, certificate_base64, certificate_thumbprint, automation_name))
  #arm_resources.append(azureAutomationConnection(location, certificate_thumbprint, automation_name, client_id, tenant, subscription_id))

  #inject runbooks
  arm_resources.append(azureAutomationRunbook("verifyAndCopy", location, automation_name, storage_account))
  arm_resources.append(azureAutomationRunbook("deleteFromInputFolder", location, automation_name, storage_account))
  arm_resources.append(azureAutomationRunbook("deleteFromValidatedFolder", location, automation_name, storage_account))

  #inject shedules
  schedules = listdir("../automation/schedules")
  for schedule in schedules:
    # we start every verify&copy at 19.00pm
    # every deleteInput job will be scheduled at 19.05pm
    # every deleteValidated job will be scheduled at 23.00pm
    startDate = datetime.now()
    #Add one day if deployment is made after 19 PM
    if (datetime.strftime(startDate,"%H:%M:%S") > "19:00:00"):
      startDate = datetime.now() + timedelta(days=1)
    schedule_path = join("../automation/schedules", schedule)
    if(isfile(schedule_path)):
      schedule_resource = json.load(open(schedule_path))
      schedule_resource['apiVersion'] = "2015-10-31"
      schedule_resource['name'] = "scheduler" + splitext(basename(schedule))[0] + "_verify"
      schedule_resource['type'] = "schedules"
      if 'comments' in schedule_resource:
        del(schedule_resource['comments'])
      schedule_resource['location'] = location
      if 'properties' in schedule_resource:
        schedule_resource['properties']['startTime'] = startDate.strftime("%Y-%m-%dT19:00:00")
      schedule_resource['dependsOn'] = ["Microsoft.Automation/automationAccounts/" + automation_name]
      arm_resources.append(schedule_resource)

      schedule_resource_deleteInput = copy.deepcopy(schedule_resource)
      schedule_resource_deleteInput['name'] = "scheduler" + splitext(basename(schedule))[0] + "_deleteInput"
      schedule_resource_deleteInput['properties']['startTime'] = startDate.strftime("%Y-%m-%dT20:00:00")
      arm_resources.append(schedule_resource_deleteInput)

      schedule_resource_deleteValidated = copy.deepcopy(schedule_resource)
      schedule_resource_deleteValidated['name'] = "scheduler" + splitext(basename(schedule))[0] + "_deleteValidated"
      schedule_resource_deleteValidated['properties']['startTime'] = startDate.strftime("%Y-%m-%dT23:00:00")
      arm_resources.append(schedule_resource_deleteValidated)

  #inject modules
  modules = listdir("../automation/modules_conf")
  for module in modules:
    module_path = join("../automation/modules_conf", module)
    if(isfile(module_path)):
      module_resource = json.load(open(module_path))
      module_resource['name'] = automation_name + "/" + module_resource['name']
      module_resource['properties']['contentLink']['uri'] = "https://" + storage_account + ".blob.core.windows.net/scripts/modules/" + module_resource['properties']['contentLink']['uri']

      dependencies = get_module_dependencies(module_resource, automation_name)
      module_resource['dependsOn'] = list(dependencies)
      arm_resources.append(module_resource)


  #inject jobSchedules which link a runbook and a schedule
  jobSchedules = listdir("../automation/jobSchedules")
  for jobSchedule in jobSchedules:
    jobSchedule_path = join("../automation/jobSchedules", jobSchedule)
    if(isfile(jobSchedule_path)):
      jobSchedule_resource = json.load(open(jobSchedule_path))
      jobSchedule_resource['apiVersion'] = "2015-10-31"
      jobSchedule_resource['name'] = str(uuid.uuid4())
      jobSchedule_resource['type'] = "jobSchedules"
      if 'comments' in jobSchedule_resource:
        del(jobSchedule_resource['comments'])
      jobSchedule_resource['location'] = location
      dependencies = get_jobSchedule_dependencies(jobSchedule_resource, automation_name)
      dependencies.add('Microsoft.Automation/automationAccounts/' + automation_name)
      jobSchedule_resource['dependsOn'] = list(dependencies)
      arm_resources.append(jobSchedule_resource)

  json.dump(arm_resources, stdout)



def usage():
    print("TODO")
 
def azureAutomationCertificate(location, certificate_base64, certificate_thumbprint, automation_name):
  return json.loads(
'''{
    "name": "AzureRunAsCertificate",
    "apiVersion": "2015-10-31",
    "type": "certificates",
    "location": "''' + location + '''",
    "properties": {
        "type": "AzureDataLakeStore",
        "base64Value": "''' + certificate_base64 + '''",
        "thumbprint": "''' + certificate_thumbprint + '''",
        "isExportable": false
    },
    "dependsOn": [
        "Microsoft.Automation/automationAccounts/''' + automation_name + '''"
    ]
}'''
)

def azureAutomationConnection(location, certificate_thumbprint, automation_name, client_id, tenant, subscription_id):
  return json.loads(
'''{
    "name": "AzureRunAsConnection",
    "apiVersion": "2015-10-31",
    "type": "connections",
    "location": "''' + location + '''",
    "properties": {
        "connectionType": {
            "name": "AzureServicePrincipal"
        },
        "fieldDefinitionValues": {
            "applicationId": "''' + client_id + '''",
            "tenantId": "''' + tenant + '''",
            "certificateThumbprint": "''' + certificate_thumbprint + '''",
            "SubscriptionId": "''' + subscription_id + '''"
        }
    },
    "dependsOn": [
        "Microsoft.Automation/automationAccounts/''' + automation_name + '''"
    ]
}'''
)

def azureAutomationRunbook(runbookName, location, automation_name, storage_account):
  return json.loads(
'''{
    "name": "''' + runbookName + '''",
    "type": "runbooks",
    "apiVersion": "2015-10-31",
    "location": "''' + location + '''",
    "dependsOn": [
        "Microsoft.Automation/automationAccounts/''' + automation_name + '''"
    ],
    "properties": {
        "runbookType": "PowerShell",
        "logProgress": false,
        "logVerbose": false,
        "description": "''' + runbookName + '''",
        "publishContentLink": {
            "uri": "https://''' + storage_account + '''.blob.core.windows.net/scripts/runbooks/''' + runbookName + '''.ps1",
            "version": "1.0.0.0"
        }
    }
}'''
)

def get_jobSchedule_dependencies(dataset, automation_name):
  return_value = set()

  if 'properties' not in dataset:
    return return_value;
  if 'runbook' not in dataset['properties']:
    return return_value;
  if 'schedule' not in dataset['properties']:
    return return_value;

  if 'name' in dataset['properties']['runbook']:
    return_value.add("Microsoft.Automation/automationAccounts/" + automation_name + "/runbooks/" + dataset['properties']['runbook']['name'])
  if 'name' in dataset['properties']['schedule']:
    return_value.add("Microsoft.Automation/automationAccounts/" + automation_name + "/schedules/" + dataset['properties']['schedule']['name'])

  return return_value;


def get_module_dependencies(module, automation_name):
  return_value = set()

  return_value.add("Microsoft.Automation/automationAccounts/" + automation_name)  
  for depend in module['dependsOn']:
    return_value.add("Microsoft.Automation/automationAccounts/" + automation_name + "/modules/" + depend)
  return return_value;


main()


