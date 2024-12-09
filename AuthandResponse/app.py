import json
import urllib3


def lambda_handler(event, context):
    # Create a connection pool manager. Connection pooling allows us to reuse existing connections to a server,
    # rather than creating a new one every time we want to send a request. This can greatly increase the efficiency
    # and speed of our requests.
    htttp = urllib3.PoolManager()
    funcurl = 'https://qvjd3lagn1.execute-api.us-east-2.amazonaws.com/Prod/query'
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
