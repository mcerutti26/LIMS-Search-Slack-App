# How to take a Python Directory from Code to a Lambda Function:
## Pre-requisites:
#### Applications
Docker, AWS CLI, and AWS SAM CLI
#### Python Directory
app.py, template.yaml, Dockerfile, and requirements.txt

## Step 1 - Authenticate Docker with AWS
`aws ecr get-login-password --region <yourregion> | docker login --username AWS --password-stdin <accountID>.dkr.ecr.<yourregion>.amazonaws.com`

## Step 2 - Create a Docker Image
Open a terminal window
Change to the python directory which composes your function
`C:\Users\MarkCerutti\PycharmProjects\LIMS-Search-Slack-App> cd .\LIMSQuery\`

Build the docker image

`docker build -t lims_search_image .`

Tag the docker image as "latest"

`docker tag lims_search_image:latest <accountID>.dkr.ecr.<yourregion>.amazonaws.com/lims_search_image:latest`

## Step 3 - Create an AWS ECR (Elastic Container Registry), if one does not already exist
`aws ecr create-repository --repository-name lims_search_image --region <yourregion>`

## Step 4 - Push the local Docker Image to the AWS ECR
`docker push <accountID>.dkr.ecr.<yourregion>.amazonaws.com/lims_search_image`

## Step 5 - Deploy New AWS Resources via a Template.yaml file
AWS resources can be built via the AWS CLI and a template.yaml file that includes the specific deployment instructions.

`sam deploy --template-file template.yaml --stack-name lims_search-stack --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --image-repository <accountID>.dkr.ecr.<yourregion>.amazonaws.com/lims_search_image`