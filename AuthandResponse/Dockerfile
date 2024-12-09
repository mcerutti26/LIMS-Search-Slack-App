FROM public.ecr.aws/lambda/python:3.9

# Install the function's dependencies using file requirements.txt
COPY ../requirements.txt  .
RUN  pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY ../app.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "app.lambda_handler" ]