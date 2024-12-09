import json
import urllib3
import base64
from urllib import parse as urlparse
from AWSHelper import get_aws_parameter


def lambda_handler(event, context):
    # Create a connection pool manager. Connection pooling allows us to reuse existing connections to a server,
    # rather than creating a new one every time we want to send a request. This can greatly increase the efficiency
    # and speed of our requests.
    htttp = urllib3.PoolManager()
    funcurl = 'https://qvjd3lagn1.execute-api.us-east-2.amazonaws.com/Prod/query'
    # Check that the request came from a Slack user in the company Slack workspace
    teamID = dict(urlparse.parse_qsl(base64.b64decode(str(event['body'])).decode('ascii')))['team_id']
    groSlackTeamID = get_aws_parameter('groSlackTeamID')
    if teamID == groSlackTeamID:
        # Invoke the LIMSQuery Lambda function via the funcurl
        # After 0.1s, the request will fail, but the try/except block will proceed to the return statement.
        # It is necessary to respond to Slack within 3s of a slash command or user message, otherwise an error message
        # appears in Slack.
        try:
            r1 = htttp.request("POST", funcurl, body=event['body'], headers={"Content-Type": "application/json"},
                               timeout=0.1)
        except urllib3.exceptions.TimeoutError:
            pass
        # The json returned to Slack will be posted to the user as an ephimeral message
        return json.dumps({'text': 'Search command received. Check the LGSearch app for your results.'})
    # If the request came from outside of the company Slack workspace, do not trigger the next Lambda
    else:
        return {
        'statusCode': 400
    }