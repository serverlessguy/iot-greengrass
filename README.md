## Prerequisites

1. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) installed and configured with access to an AWS Account.
1. [Python3](https://www.python.org/downloads/) and [pip](https://pip.pypa.io/en/latest/installation/). The most recent version of Python includes pip.
1. [Greengrass Development Kit (GDK) CLI](https://github.com/aws-greengrass/aws-greengrass-gdk-cli)
    * To install the GDK CLI:
    ```
    pip3 install git+https://github.com/aws-greengrass/aws-greengrass-gdk-cli.git@v1.6.1
    ```
    * Run `gdk --version` to check if the GDK CLI is successfully installed.

## Installation

### Create GreengrassV2TokenExchangeRole

1. Change to the "iot-greengrass" directory:
```
cd iot-greengrass
```
2. Deploy the "iam.yaml" to create the GreengrassV2TokenExchangeRole. Note that the "iam.yaml" file does not create the IAM Policy named "GreengrassV2TokenExchangeRoleAccess". That policy is generated automatically, and attached to the IAM Role named "GreengrassV2TokenExchangeRole", after the first Greengrass core device is created.
```
aws cloudformation deploy --template-file iam.yaml --stack-name greengrass-v2-token-exchange-role-stack --capabilities CAPABILITY_NAMED_IAM
```

### Setup Greengrass Device

1. Deploy the "template.yaml". Update MyIp to match your public IPv4 address.
```
aws cloudformation deploy --template-file template.yaml --stack-name demo-greengrass-stack --tags AppName=demo-greengrass --parameter-overrides MyIp=0.0.0.0/32 --capabilities CAPABILITY_IAM
```
2. Here is an overview of what this CloudFormation stack provisions:
    * S3 bucket and IAM Policy to access S3.
    * IAM Policy that allows Greengrass devices to provision themselves.
    * IoT Thing Group. When Greengrass is installed on a device, it associates the device with this Thing Group.
    * EC2 Instance (Debian Linux, arm64, t4g.nano) that acts as an IoT Greengrass device.
        * Instance role and profile
        * Key pair (rsa, ppk)
        * Security Group with SSH access
        * UserData script:
            * Update/upgrade installed packages
            * Install unzip and JDK
            * Download and install Greengrass
            * Reboot instance
    * IoT Greengrass Deployment to configure the aws.greengrass.Nucleus JVM options to optimize for a low memory device and aws.greengrass.LogManager to configure CloudWatch logging.
3. Query the output from the CloudFormation stack:
```
aws cloudformation describe-stacks --stack-name demo-greengrass-stack --query 'Stacks[0].Outputs'
```
4. Copy the output value ThingGroupARN for later use when deploying the Greengrass Lambda function component.
5. (Optional) Connect to instance with an SSH client(eg: PuTTy) to confirm Greengrass installation.
    * Retrieve the EC2 keypair from the SSM Parameter Store (eg: /ec2/keypair/key-{KeyId}) and create a "keypair.ppk" file with the private key material.
    * PuTTy configuration:
        * Connection > SSH > Auth: Browse to the "keypair.ppk" file.
        * Connection > Data > Auto-login username: admin
        * Session > Host Name: Public DNS of EC2 instance (eg: ec2-0.0.0.0.compute-1.amazonaws.com)
    * Watch the deployment occur on the EC2 instance by monitoring the log:
    ```
    sudo tail -n 50 -F /greengrass/v2/logs/greengrass.log
    ```
    * Verify the aws.greengrass.Nucleus component configuration update with the following command:
    ```
    sudo cat /greengrass/v2/config/effectiveConfig.yaml | grep jvmOptions
    ```
6. Go to [Greengrass Core Devices](https://us-east-1.console.aws.amazon.com/iot/home?region=us-east-1#/greengrass/v2/cores) in the AWS Management Console to verify that the EC2 instance is registered as a Greengrass device before proceeding with the installation process. It may take a few minutes after the EC2 instance is launched to see it registered as a Greengrass device.

### Create LocalPubSub Component

1. Change to the "iot-greengrass/LocalPubSub" directory:
```
cd LocalPubSub
```
2. Install dependencies (eg: awsiotsdk) locally and package with zip file before deploying to Greengrass device:
```
pip3 install -t ./dependencies awsiotsdk
```
3. Note the Run command in the "recipe.yaml" file, it tells Python where to look for dependencies (eg: PYTHONPATH):
```
PYTHONPATH={artifacts:decompressedPath}/com.example.LocalPubSub/dependencies
```
4. Update the "gdk-config.json" configuration file:
    * Update the author.
    * Update the S3 bucket prefix (eg: demo-greengrass). If you deployed the "template.yaml" above, an S3 bucket will already exist (bucket name format: {Bucket-Prefix}-{Region}-{AccountId}), so the `gdk component publish` command below will not need to create a new bucket.
    * Update the region (eg: us-east-1).
    * Update the gdk_version (eg: 1.6.1): `gdk --version`
5. Build the artifacts and recipes of the component:
```
gdk component build
```
6. Publish a new version of the component in your AWS account:
```
gdk component publish
```

### Deploy LocalPubSub Component

1. List Greengrass components:
```
aws greengrassv2 list-components
```
2. Copy the componentVersion of the com.example.LocalPubSub (eg: 1.0.0).
3. Update the "deployment.json" configuration file:
    * Update the targetArn to match the ThingGroupARN from the original CloudFormation output. You should only need to update the Region and AccountId.
    * Update the componentVersion of the com.example.LocalPubSub if needed. Refer to the Greengrass components list from a previous step.
4. Create a new Greengrass Deployment:
```
aws greengrassv2 create-deployment --cli-input-json file://deployment.json
```
5. Monitor the deployment from the IoT [Greengrass Deployment console](https://us-east-1.console.aws.amazon.com/iot/home?region=us-east-1#/greengrass/v2/deployments) to verity it completes successfully.
6. View com.example.LocalPubSub logs on the EC2 instance:
```
sudo tail -n 50 -F /greengrass/v2/logs/com.example.LocalPubSub.log
```

### Create IoTPubSub Component

1. Change to the "iot-greengrass/IoTPubSub" directory:
```
cd ../IoTPubSub
```
2. Install dependencies (eg: awsiotsdk) locally and package with zip file before deploying to Greengrass device:
```
pip3 install -t ./dependencies awsiotsdk
```
3. Note the Run command in the "recipe.yaml" file, it tells Python where to look for dependencies (eg: PYTHONPATH):
```
PYTHONPATH={artifacts:decompressedPath}/com.example.IoTPubSub/dependencies
```
4. Update the "gdk-config.json" configuration file:
    * Update the author.
    * Update the S3 bucket prefix (eg: demo-greengrass). If you deployed the "template.yaml" above, an S3 bucket will already exist (bucket name format: {Bucket-Prefix}-{Region}-{AccountId}), so the `gdk component publish` command below will not need to create a new bucket.
    * Update the region (eg: us-east-1).
    * Update the gdk_version (eg: 1.6.1): `gdk --version`
5. Build the artifacts and recipes of the component:
```
gdk component build
```
6. Publish a new version of the component in your AWS account:
```
gdk component publish
```

### Deploy IoTPubSub Component

1. List Greengrass components:
```
aws greengrassv2 list-components
```
2. Copy the componentVersion of the com.example.IoTPubSub (eg: 1.0.0).
3. Update the "deployment.json" configuration file:
    * Update the targetArn to match the ThingGroupARN from the original CloudFormation output. You should only need to update the Region and AccountId.
    * Update the componentVersion of the com.example.IoTPubSub if needed. Refer to the Greengrass components list from a previous step.
4. Create a new Greengrass Deployment:
```
aws greengrassv2 create-deployment --cli-input-json file://deployment.json
```
5. Monitor the deployment from the IoT [Greengrass Deployment console](https://us-east-1.console.aws.amazon.com/iot/home?region=us-east-1#/greengrass/v2/deployments) to verity it completes successfully.
6. View com.example.IoTPubSub logs on the EC2 instance:
```
sudo tail -n 50 -F /greengrass/v2/logs/com.example.IoTPubSub.log
```

### MQTT Test

1. From the [MQTT test client](https://us-east-1.console.aws.amazon.com/iot/home?region=us-east-1#/test) in the AWS IoT Management Console, subscribe to all topics using #.
2. Publish any message to the topic "demo-greengrass/request".
3. If everything worked, you should see a message in the "demo-greengrass/response" topic.

## Monitoring and Debugging the Component

If there are any issues, you can monitor the deployment and the component itself on the Greengrass core device in the following logs:

1. Greengrass Core Log:
```
sudo tail -n 50 -F /greengrass/v2/logs/greengrass.log
```
2. Greengrass Component Log:
```
sudo tail -n 50 -F /greengrass/v2/logs/{COMPONENT_NAME}.log
```