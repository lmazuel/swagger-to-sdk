[![Build Status](https://travis-ci.org/azuresdk/swagger-to-sdk.svg?branch=master)](https://travis-ci.org/azuresdk/swagger-to-sdk)
[![Coverage Status](https://coveralls.io/repos/github/azuresdk/swagger-to-sdk/badge.svg?branch=master)](https://coveralls.io/github/azuresdk/swagger-to-sdk?branch=master)

The SwaggerToSDK script is the automation script launched at each commit on any Swagger files to provide:
- Testing against SDK language
- Automatic PR on each language SDK

This is Python 3.6 only.

This works is still in progress and move fast. We'll do our best to keep this page up-to-date.

# Configuration file swagger_to_sdk.json

This is a configuration which MUST be at the root of the repository you wants to generate.

```json
{
  "$schema": "https://raw.githubusercontent.com/azuresdk/swagger-to-sdk/master/swagger_to_sdk_config.schema.json",
  "meta": {
    "after_scripts": [
      "gofmt -w ./services/"
    ],
    "version":"0.2.0",
    "autorest_options": {
      "license-header": "MICROSOFT_MIT_NO_VERSION",
      "payload-flattening-threshold": 2,
      "python": "",
      "azure-arm": true,
      "sdkrel:python-sdks-folder": "."
    },
    "envs": {
      "sdkrel:SCRIPTPATH": "./scripts"
    },
    "advanced_options": {
      "clone_dir": "./src/github.com/Azure/azure-sdk-for-go"
    },
    "wrapper_filesOrDirs": [],
    "delete_filesOrDirs": [
      "credentials.py",
      "exceptions.py"
    ],
    "generated_relative_base_directory": "*client"
  },
  "projects": {
    "authorization": {
      "autorest_options": {
        "input-file": "arm-authorization/2015-07-01/swagger/authorization.json",
        "namespace": "azure.mgmt.authorization",
        "package-version": "0.30.0"
      },
      "output_dir": "azure-mgmt-authorization/azure/mgmt/authorization",
      "build_dir": "azure-mgmt-authorization"
    },
    "recoveryservicesbackup": {
      "markdown": "arm-recoveryservicesbackup/readme.md",
      "generated_relative_base_directory": "Generated/Python/azure/mgmt/recoveryservicesbackup",
      "output_dir":  "azure-mgmt-recoveryservicesbackup/azure/mgmt/recoveryservicesbackup",
      "build_dir": "azure-mgmt-recoveryservicesbackup"
    }
  }
}
```

## Meta

### version
The version must be 0.2.0.

## after_scripts

List of commands to execute after the generation is done. Will be executed in the order of the list. Current working directory will be the cloned path. See also "envs" node.

## autorest_options
An optional dictionary of options you want to pass to Autorest. This will be passed in any call, but can be override by "autorest_options" in each data.
Note that you CAN'T override "--output-folder" which is filled contextually.
All options prefixed by "sdkrel:" can be a relative path that will be solved against SDK folder before being sent to Autorest.

## envs
Environment variables for after_scripts.
All options prefixed by "sdkrel:" can be a relative path that will be solved against SDK folder before being sent to the scripts.

## advanced_options

### clone_dir
Add more layers of folders to clone the repo, if necessary. Right now, useful for Go only. "sdkrel:" will consider this as the final folder path.

## wrapper_filesOrDirs
An optional list of files/directory to keep when we generate new SDK. This support a Bash-like wildcard syntax (i.e. '*/myfile?.py').
This applies to every Swagger files.

## delete_filesOrDirs
An optional list of files/directory to delete from the generated SDK. This support a Bash-like wildcard syntax (i.e. '*/myfile?.py')
This applies to every Swagger files.

## generated_relative_base_directory
If the data to consider generated by Autorest are not directly in the root folder. For instance, if Autorest generates a networkclient folder
and you want to consider this folder as the root of data. This parameter is applied before 'delete_filesOrDirs', consider it in your paths.
This applies to every Swagger files.

## Projects

It's a dict where keys are a project id. The project id has no constraint, but it's recommended to use namespace style, like
"datalake.store.account" to provide the best flexibility for the --project parameter.

Values are:

### markdown
This is an optional parameter which specificy the Autorest MD file path for this project. This is relative to the rest-folder paramter.

### autorest_options
A dictionary of options you want to pass to Autorest. This will override parameter from "autorest_options" in "meta" node.
Note that you CAN'T override "--output-folder" which is filled contextually.

## wrapper_filesOrDirs
An optional list of files/directory to keep when we generate new SDK. This support a Bash-like wildcard syntax (i.e. '*/myfile?.py').
This is added with the list in "meta", this NOT override it.

## delete_filesOrDirs
An optional list of files/directory to delete from the generated SDK. This support a Bash-like wildcard syntax (i.e. '*/myfile?.py')
This is added with the list in "meta", this NOT override it.

## generated_relative_base_directory
If the data to consider generated by Autorest are not directly in the root folder. For instance, if Autorest generates a networkclient folder
and you want to consider this folder as the root of data.  This parameter is applied before 'delete_filesOrDirs', consider it in your paths.
This replace the same parameter in "meta" if both are provided.

## output_dir
This is the folder in your SDK repository where you want to put the generated files.

## build_dir

This is an optional folder where to put metadata about the generation (Autorest version, date of generation, etc.). This can be used
by our monitoring system to detect package that needs an update. Be sure this folder is unique in the entire file, to avoid
overwritting a file from another project.
