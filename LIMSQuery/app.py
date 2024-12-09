import urllib3
from LabGuruAPI import Collections, Session, Box
from urllib import parse as urlparse
import base64
from slack_sdk import WebClient
import pymysql
import json
from AWSHelper import get_aws_secret, get_aws_parameter


def edit_well_numbering(input_data, tot_wells):
    """
    When looking at a gridded plate or box, well locations can be:
        Alphanumeric = A1, A2, B1
        Row Numbered = 1, 2, 13
        Column Numbered = 1, 9, 2
    ^96 well (8x12) examples

    This function flips row numbers to alphanumeric
    :param input_data: integer for the row numbered well position
    :param tot_wells: integer for the total number of well positions in the plate or box
    :return: the alphanumeric name of the well position
    """
    if tot_wells == 96:
        # Create a dictionary for the alphanumeric row names
        rowname = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H'}
        # Based on the input numbering type, calculate the row number and column number
        rownum = ((input_data - 0.1) // 12) + 1
        colnum = (input_data % 12)
        if colnum == 0:
            colnum = 12
        output_data = rowname[int(rownum)] + str(int(colnum))
        return output_data
    elif tot_wells == 384:
        # Create a dictionary for the alphanumeric row names
        rowname = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L',
                   13: 'M', 14: 'N', 15: 'O', 16: 'P'}
        # Based on the input numbering type, calculate the row number and column number
        rownum = ((input_data - 0.1) // 24) + 1
        colnum = (input_data % 24)
        if colnum == 0:
            colnum = 24
        output_data = rowname[int(rownum)] + str(int(colnum))
        return output_data
    elif tot_wells == 81:
        # Create a dictionary for the alphanumeric row names
        rowname = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H', 9: 'I'}
        # Based on the input numbering type, calculate the row number and column number
        rownum = ((input_data - 0.1) // 9) + 1
        colnum = (input_data % 9)
        if colnum == 0:
            colnum = 9
        output_data = rowname[int(rownum)] + str(int(colnum))
        return output_data
    else:
        return


def locatestocks(item: str, SESSION):
    """
    A function for querying the LabGuru LIMS (Lab Information Management System) for item locations based on a search
    term.
    For example, 'GRO17-0001' would be a search term. This string would result in a corresponding strain in the LabGuru
    LIMS with associated stocks. The stocks with locations specifically in our shared general storage locations will
    have storage information relayed back to the Slack user.

    :param item: string variable for an item to search for in the LIMS
    :param SESSION: an object that is used to interface with the LabGuru REST API
    :return: the string and url results of the LIMS search to be later formed into a Slack message
    """
    # Search all Collections in LabGuru LIMS for items with a name matching the search string
    hit = Collections.from_name(item)
    # If a match is found, hit will not be None.
    if hit:
        pass
    # If no matches are found, try some common search string errors
    # For example, try multiple different years from 17-24
    elif 'GRO' in item and 'p' not in item:
        for year in range(17, 25):
            item = 'GRO' + str(year) + '-' + item[-4:]
            hit = Collections.from_name(item)
            # If still no matches are found, break
            if hit:
                break
    # Try various antibiotic resistance codes
    if not hit:
        for antibiotic in ['A', 'C', 'K', 'S', 'T', 'Z']:
            item = 'pGRO-' + antibiotic + item[-4:]
            hit = Collections.from_name(item)
            # If still no matches are found, break
            if hit:
                break
    # Define what is a desired storage name prefix based on the Collection item type
    hittype = hit.class_display_name
    if 'Strain' in hittype:
        # List of all stocks associated with the searched Collection item
        stocklist = hit.get_stocks()
        # List of all desired locations to send back to the Slack user
        loclist = []
        for cur_stock in stocklist:
            try:
                cur_box = SESSION.get_object(Box, cur_stock.storage.id).name
                # For a strain search, only Boxes with names that contain GLY- or AGS- are desired
                if 'GLY-' in cur_box or 'AGS-' in cur_box:
                    box_url = cur_stock.storage_box().web_url
                    loclist.append('<' + box_url + '|Box: ' + cur_box + '>, Well: ' + str(
                        edit_well_numbering(cur_stock.location_in_box, 96)))
            # Some Boxes in the LabGuru LIMS may not have all attributes correctly defined
            except AttributeError:
                pass
        return loclist, hit.web_url, item
    elif 'Plasmid' in hittype:
        stocklist = hit.get_stocks()
        loclist = []
        for cur_stock in stocklist:
            try:
                cur_box = SESSION.get_object(Box, cur_stock.storage.id).name
                # For a plasmid search, only Boxes with names that contain PLA- are desired
                if 'PLA-' in cur_box:
                    box_url = cur_stock.storage_box().web_url
                    loclist.append('<' + box_url + '|Box: ' + cur_box + '>, Well: ' + str(
                        edit_well_numbering(cur_stock.location_in_box, 96)))
            # Some Boxes in the LabGuru LIMS may not have all attributes correctly defined
            except (AttributeError, KeyError):
                pass
        return loclist, hit.web_url, item
    elif hittype in ['Primers', 'Synthesized dsDNAs', 'PCR Products']:
        stocklist = hit.get_stocks()
        loclist = []
        for cur_stock in stocklist:
            cur_box = cur_stock.storage_box().name
            box_url = cur_stock.storage_box().web_url
            # For Primers, Syn dsDNA, or PCR Products, all stock locations are desired by the Slack user and
            # the number of well positions of the Boxes is not locked at 96.
            if cur_stock.storage.cols == 12:
                loclist.append('<' + box_url + '|Box: ' + cur_box + '>, Well: ' + str(
                    edit_well_numbering(cur_stock.location_in_box, 96)))
            elif cur_stock.storage.cols == 24:
                loclist.append('<' + box_url + '|Box: ' + cur_box + '>, Well: ' + str(
                    edit_well_numbering(cur_stock.location_in_box, 384)))
            elif cur_stock.storage.cols == 9:
                loclist.append('<' + box_url + '|Box: ' + cur_box + '>, Well: ' + str(
                    edit_well_numbering(cur_stock.location_in_box, 81)))
            else:
                loclist.append('<' + box_url + '|Box: ' + cur_box + '>')
        return loclist, hit.web_url, item
    elif hit:
        return [], hit.web_url, item
    else:
        return [], '', item


def handler(event, context):
    # Retrieve and store labguru access token for future api requests
    SESSION = Session(token=json.loads(get_aws_secret("LGAPI_2024", "us-east-2"))['token'])
    SESSION.login()
    # Get the SLACK_BOT_TOKEN from the environment variables.
    # This token is used to authenticate our app with Slack's servers.
    slack_token = get_aws_parameter('/slackBotTokens/LGSearch')
    # Create a client connection to Slack API with the provided token.
    # This client allows us to interact with Slack's Web API, which enables actions like sending a message, creating a channel, upload a file, etc.
    client = WebClient(token=slack_token)
    # Create a connection pool manager.
    # Connection pooling allows us to reuse existing connections to a server, rather than creating a new one every time we want to send a request.
    # This can greatly increase the efficiency and speed of our requests.
    htttp = urllib3.PoolManager()

    # Take the input event from Slack and decode it
    # The except case is for non-Slack initiated runs

    # Decode the event payload from Slack to extract the following
    # Time that the Slack slash command was sent
    request_datetime = event['requestContext']['requestTime']
    # String contents of the Slack message
    searchstring = dict(urlparse.parse_qsl(base64.b64decode(str(event['body'])).decode('ascii')))['text']
    # URL to send Slack a 200 response to confirm the slash command was received
    respurl = dict(urlparse.parse_qsl(base64.b64decode(str(event['body'])).decode('ascii')))['response_url']
    # Slack ID for the user that sent the slash command
    userid = dict(urlparse.parse_qsl(base64.b64decode(str(event['body'])).decode('ascii')))['user_id']
    # Slack Username for the user that sent the slash command
    username = dict(urlparse.parse_qsl(base64.b64decode(str(event['body'])).decode('ascii')))['user_name']

    # Interpret the string as a list of items to be searched
    searchlist = searchstring.replace('and', '')
    searchlist = searchlist.replace(' ', '')
    searchlist = searchlist.split(',')

    # Send a POST API request to Slack confirming that the slash command was received without error
    # If a 200 response is not received within 3s, the user is informed that there was an error with the command
    r1 = htttp.request("POST", respurl, fields={'status': 200})

    # Pull AWS RDS Configuration Info
    search_db_secret = json.loads(get_aws_secret('lgsearchdblogin', 'us-east-2'))
    endpoint = search_db_secret['host']
    dbusername = search_db_secret['username']
    dbpassword = search_db_secret['password']
    database_name = 'LGSearchUsage'

    # Connect to the MySQL AWS RDS and log the query
    connection = pymysql.connect(host=endpoint, user=dbusername, passwd=dbpassword, db=database_name)
    cursor = connection.cursor()
    # Note that using %s as a placeholder for variables followed by cursor.execute() helps to prevent SQL Injection
    # attacks by quote-escaping string values for the variables pulled from the Slack data
    dbcommandstring = "INSERT INTO LGSearches (user_name, time_stamp, searched_string) VALUES (%s, %s, %s)"
    cursor.execute(dbcommandstring, (username, request_datetime, searchstring))
    connection.commit()

    # Open up a Slack chat between the LIMS search application and the user
    dmchat = client.conversations_open(users=[userid])
    dmchatid = dmchat.data['channel'].get('id')
    # Check the conversation history between the user and the app
    history = client.conversations_history(channel=dmchatid)
    # If it is the user's first message, send a welcome message with instructions
    if len(history['messages']) == 0:
        welcomeresp = client.chat_postMessage(channel=dmchatid,
                                              text='Hello, thank you for using the LGSearch application. To perform a '
                                                   'search type `/lgfind` followed by the LabGuru item(s) you would '
                                                   'like to locate. When searching for multiple items, '
                                                   'please separate each item by a comma.\nIf you have any questions, '
                                                   'encounter any bugs, or have a wishlist of features, '
                                                   'please DM Mark Cerutti directly.')
    # Message the user that the search has started
    searchingresp = client.chat_postMessage(channel=dmchatid, text="Searching for *" + searchstring + "* in LabGuru.")

    n = 0
    # Locate the stocks and get the url of the LG item you searched for
    # Iterate through the list of queries from the original slash command
    for item in searchlist:
        # locatestocks extracts the necessary LIMS data to send back to the user
        cur_stock, searchstring_url, hitstring = locatestocks(item, SESSION)
        # Format the final results Slack message based on the results
        if len(cur_stock) > 0:
            # hyperlinked message of the searched item
            outputMessage = "<" + searchstring_url + "|" + hitstring + ">" + " was found at"
            # threaded message of the hyperlinked box and position where the searched item can be found
            for stocks in cur_stock:
                outputMessage += "\n>" + stocks
        # Could not find any matches for the searched item in the LIMS
        elif len(cur_stock) == 0 and searchstring_url == '':
            outputMessage = "I could not find *" + item + "*. Please, confirm that your search term exactly matches an LG item name and commas are used to separate item names when searching multiple items at once."
        # Found the searched item in the LIMS but no appropriate stocks
        elif len(cur_stock) == 0 and searchstring_url != '':
            outputMessage = "I could not find stocks for " + "<" + searchstring_url + "|" + hitstring + ">" + "."
        else:
            outputMessage = "Unknown Search Error"

        # For the first search result, replace the "Searching for..." message
        # For the later search results on a set of queries, send the search results as new messages
        history = client.conversations_history(channel=dmchatid)
        if n == 0:
            # Extract the "Searching for..." timestamp from Slack
            searchingts = history.data['messages'][0]['ts']
            editmessage = client.chat_update(channel=dmchatid, ts=searchingts, text=outputMessage)
        else:
            writemessage = client.chat_postMessage(channel=dmchatid, text=outputMessage)
        n += 1
    return {
        'statusCode': 200
    }
