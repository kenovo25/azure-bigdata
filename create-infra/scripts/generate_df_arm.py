#!/usr/bin/env python

# recreates the resource for a Azure dataafactory (1.0) Arm deployment 
# from resources that were grabbed (manually) from the portal

from sys import stdout;
from os import listdir;
from os.path import isfile, join;

import sys
import getopt
import json

def main():

  try: 
     opts, args = getopt.getopt(sys.argv[1:], '', ['datafactory_name=', 'datalake_store_name=', 'client_id=', 'secret=', 'subscription_id=', 'tenant=', 'datalake_store_resource_group_name=', 'datalake_analytics_name=', 'datalake_analytics_resource_group_name=', 'sqlserver_name=', 'sqlserver_catalog=', 'sqldatabase_as_name=', 'sqlserver_password=', 'storage_account_name=', 'storage_account_key=', 'startTime=', 'endTime=', 'isPaused=','sqlserver_username='])
  except getopt.GetOptError:
    usage()
    print("here")
    sys.exit(2)

  for opt, arg in opts:
    if opt in ('--datafactory_name'):
      datafactory_name = arg
    elif opt in ('--datalake_store_name'):
      datalake_store_name = arg
    elif opt in ('--client_id'):
      client_id = arg
    elif opt in ('--secret'):
      secret = arg
    elif opt in ('--subscription_id'):
      subscription_id = arg
    elif opt in ('--tenant'):
      tenant = arg
    elif opt in ('--datalake_store_resource_group_name'):
      datalake_store_resource_group_name = arg
    elif opt in ('--datalake_analytics_name'):
      datalake_analytics_name = arg
    elif opt in ('--datalake_analytics_resource_group_name'):
      datalake_analytics_resource_group_name = arg
    elif opt in ('--sqlserver_name'):
      sqlserver_name = arg
    elif opt in ('--sqlserver_catalog'):
      sqlserver_catalog = arg
    elif opt in ('--sqldatabase_as_name'):
      sqldatabase_as_name = arg
    elif opt in ('--sqlserver_password'):
      sqlserver_password = arg
    elif opt in ('--storage_account_name'):
      storage_account_name = arg
    elif opt in ('--storage_account_key'):
      storage_account_key = arg
    elif opt in ('--startTime'):
      startTime = arg
    elif opt in ('--endTime'):
      endTime = arg
    elif opt in ('--sqlserver_username'):
      sqlserver_username = arg
    elif opt in ('--isPaused'):
      isPaused = arg
      
    else:
      print("there") 
      usage()
      sys.exit(2)

    #if (datafactory_name is None) or (datalake_store_name is None):
    #  print("and also here") 
    #  usage()
    #  sys.exit(2)
    

  arm_resources = [] 
  # read all the files of the datasets directory

  # inject the linkedservices
  # contrary to pipelines and datasets, linkedservices cannot 
  # be taken as-is as they depend from the environment 

  arm_resources.append(azureSqlDatabase("SqlLinkedService",datafactory_name, sqlserver_name, sqldatabase_as_name, sqlserver_password,sqlserver_username))
  arm_resources.append(azureStorageLinkedService("StorageLinkedService", datafactory_name, storage_account_name, storage_account_key))
 
  # inject the datasets by reading the directory where they are stored
  datasets = listdir("../datafactory/datasets")
  for dataset in datasets:
    dataset_path = join("../datafactory/datasets", dataset)
    if(isfile(dataset_path)):
      dataset_resource = json.load(open(dataset_path))
      dataset_resource['apiVersion'] = "2015-10-01"
      dataset_resource['type'] = "datasets"
      dependencies = get_dataset_dependencies(dataset_resource)
      dependencies.add('Microsoft.DataFactory/datafactories/' + datafactory_name)
      dataset_resource['dependsOn'] = list(dependencies)
      arm_resources.append(dataset_resource)

   
  # inject the pipeline by reading the directory where they are stored
  pipelines = listdir("../datafactory/pipelines")
  for pipeline in pipelines:
    pipeline_path = join("../datafactory/pipelines", pipeline)
    if(isfile(pipeline_path)):
      pipeline_resource = json.load(open(pipeline_path))
      pipeline_resource['apiVersion'] = "2015-10-01"
      pipeline_resource['type'] = "datapipelines"
      if 'properties' in pipeline_resource:
        if 'hubName' in pipeline_resource['properties']:
           del(pipeline_resource['properties']['hubName'])
        if 'start' in pipeline_resource['properties']:
           pipeline_resource['properties']['start']= startTime
        if 'end' in pipeline_resource['properties']:
           pipeline_resource['properties']['end']= endTime
        if 'isPaused' in pipeline_resource['properties']:
           pipeline_resource['properties']['isPaused']= isPaused
      dependencies = get_pipeline_dependencies(pipeline_resource)
      dependencies.add('Microsoft.DataFactory/datafactories/' + datafactory_name)
      pipeline_resource['dependsOn'] = list(dependencies)
      arm_resources.append(pipeline_resource)

  json.dump(arm_resources, stdout)


def usage():
    print("TODO")



# get the linkedservice whoe the pipeline depends in order to 
# inject them into the dependsOn of the arm deployment
def get_dataset_dependencies(dataset):
   return_value = set()

   if 'properties' in dataset:
     if 'linkedServiceName' in dataset['properties']:
       return_value.add ( dataset['properties']['linkedServiceName'] )
   return return_value;

# get the datasets and linkedservice whoe the pipeline depends
# in order to inject them into the dependsOn of the arm deployment
def get_pipeline_dependencies(dataset):
   return_value = set()

   if 'properties' not in dataset:
     return return_value;

   if 'activities' not in dataset['properties']:
     return return_value;

   for activity in dataset['properties']['activities']:
      if 'linkedServiceName' in activity:
         return_value.add(activity['linkedServiceName'])

      if 'typeProperties' in activity:
         if 'scriptLinkedService' in activity['typeProperties']:
            return_value.add(activity['typeProperties']['scriptLinkedService'])
           
         if 'redirectIncompatibleRowSettings' in activity['typeProperties']:
            if 'linkedServiceName' in activity['typeProperties']['redirectIncompatibleRowSettings']:
               return_value.add(activity['typeProperties']['redirectIncompatibleRowSettings']['linkedServiceName'])

      if 'inputs' in activity:
         for input in activity['inputs']: 
            if 'name' in input:
               return_value.add(input['name'])

      if 'outputs' in activity:
         for output in activity['outputs']: 
            if 'name' in output:
               return_value.add(output['name'])

   return return_value;


def azureDataLakeAnalyticsLinkedService(linked_service_name, datafactory_name, 
  datalake_analytics_name, client_id, secret, subscription_id, tenant, 
  datalake_analytics_resource_group_name):
   return json.loads(
'''{
    "name": "''' + linked_service_name + '''",
    "apiVersion": "2015-10-01",
    "type": "linkedservices",
    "properties": {
        "type": "AzureDataLakeAnalytics",
        "typeProperties": {
            "accountName": "''' + datalake_analytics_name + '''",
            "servicePrincipalId": "''' + client_id + '''",
            "servicePrincipalKey": "''' + secret + '''",
            "tenant": "''' + tenant + '''",
            "subscriptionId": "''' + subscription_id + '''",
            "resourceGroupName": "'''+ datalake_analytics_resource_group_name + '''"
        }
    },
    "dependsOn": [
        "Microsoft.DataFactory/datafactories/''' + datafactory_name + '''"
    ]
}'''
)


def azureStorageLinkedService(linked_service_name, datafactory_name, 
   storage_account_name, storage_account_key):
   return json.loads(
'''{
    "name": "''' + linked_service_name + '''",
    "apiVersion": "2015-10-01",
    "type": "linkedservices",
    "properties": {
        "description": "Azure Storage linked service",
        "type": "AzureStorage",
        "typeProperties": {
            "connectionString": "DefaultEndpointsProtocol=https;AccountName=''' + storage_account_name + ''';AccountKey=''' + storage_account_key + ''';EndpointSuffix=core.windows.net"
        }
    },
    "dependsOn": [
        "Microsoft.DataFactory/datafactories/''' + datafactory_name + '''"
    ]
}'''
)





def azureDataLakeStoreLinkedService(linked_service_name, datafactory_name,
   datalake_store_name, client_id , secret, subscription_id, tenant, 
   datalake_store_resource_group_name):

   return json.loads(
'''{
    "name": "''' + linked_service_name + '''",
    "apiVersion": "2015-10-01",
    "type": "linkedservices",
    "properties": {
        "description": "Azure dataLake Store linked service",
        "type": "AzureDataLakeStore",
        "typeProperties": {
            "dataLakeStoreUri": "adl://''' + datalake_store_name + '''.azuredatalakestore.net",
            "servicePrincipalId": "''' + client_id + '''",
            "servicePrincipalKey": "''' + secret + '''",
            "tenant": "''' + tenant + '''",
            "subscriptionId": "''' + subscription_id + '''",
            "resourceGroupName": "''' + datalake_store_resource_group_name + '''"
        }
    },
    "dependsOn": [
        "Microsoft.DataFactory/datafactories/''' + datafactory_name + '''"
    ]
}''')

def azureSqlDatabase(linked_service_name, datafactory_name, 
   sqlserver_name, sqlserver_catalog, sqlserver_password, sqlserver_username):
   return json.loads(
'''{
    "name": "''' + linked_service_name + '''",
    "apiVersion": "2015-10-01",
    "type": "linkedservices",
    "properties": {
        "description": "",
        "type": "AzureSqlDatabase",
        "typeProperties": {
            "connectionString": "Data Source=tcp:''' + sqlserver_name + '''.database.windows.net,1433;Initial Catalog=''' + sqlserver_catalog + ''';Integrated Security=False;User ID=''' + sqlserver_username+ '''@''' + sqlserver_name + '''.database.windows.net;Password=''' + sqlserver_password + ''';Connect Timeout=30;Encrypt=True"
        }
    },
    "dependsOn": [
        "Microsoft.DataFactory/datafactories/''' + datafactory_name + '''"
    ]
}'''
)

main()

#dans les pipelines :
#
#  reference aux linkedServices
#    properties.activities[].typeProperties.scriptLinkedService
#    properties.activities[].typeProperties.redirectIncompatibleSettings.linkedServiceName
#    properties.activities[].linkedServiceName
#
#   reference aux datasets
#     properties.activities[].inputs.name
#     properties.activities[].outputs.name
#
#dans les datasets
#
#  reference aux linkedServices
##    properties.linkedServiceName


