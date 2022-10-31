import requests
import re
import json
import pandas as pd
from urllib.parse import urlparse, parse_qs

entities = ["Candidate", "ClientContact", "ClientCorporation", "JobOrder", "JobSubmission", "Placement", "Lead",
            "Opportunity", "CorporateUser"]

saved_lists = {}


def validated_integer(prompt="", unit_name="", digits=""):
    while True:
        try:
            i = int(input(prompt))
            if digits == "":
                return i
            else:
                if len(str(i)) != digits:
                    print(f"Please enter a {digits} digit value.")
                else:
                    return i
        except ValueError:
            print(f"Please enter a valid {unit_name}")


def select_integer():
    while True:
        try:
            i = int(input())
            return i
        except ValueError:
            print(f'Please enter a number')


def numbered_list(items):
    i = 0
    for item in items:
        print(f'{i} - {item}')
        i += 1
    while True:
        choice = select_integer()
        if choice > len(items):
            print("Please choose a valid item.")
            continue
        else:
            return items[choice]


def select_yes_no(message=""):
    if message != "":
        print(message)
    while True:
        prompt = input("(Y)es/(N)o: ")
        prompt = prompt.lower()
        if 'y' in prompt:
            return True
        elif 'n' in prompt:
            return False


def get_rest_info():
    print("Paste a URL to parse, or leave blank to manually enter details")
    url_to_parse = input()
    if url_to_parse == "":
        swimlane = validated_integer("Swimlane (number only): ", 'swimlane', 2)
        corp_token = input("Corp Token: ")
        rest_object = {
            'BhRestToken': input("BhRestToken: "),
            'rest_url': f'https://rest{swimlane}.bullhornstaffing.com/rest-services/{corp_token}'
        }
        return rest_object
    else:
        # Extracts the corp token from the pasted URL
        match = re.findall("^([^/]*/){5}", url_to_parse)
        # Breaks down the URL into workable parts
        url_parts = urlparse(url_to_parse)
        # Extracting the parameters from the URL into a dictionary.
        params = parse_qs(url_parts.query)
        # Grabbing the rest token from the parameters dictionary.
        rest_token = str(params["BhRestToken"])
        # removing erroneous characters from dictionary value
        char_to_clean = ["[", "'", "]"]
        for i in char_to_clean:
            rest_token = rest_token.replace(i, "")
        # Building the URL with the parsed parts.
        rest_object = {
            'BhRestToken': rest_token,
            'rest_url': f'https://{url_parts.netloc}/rest-services/{match[-1]}'
        }
        for i in entities:
            if i in url_to_parse:
                print(f"URL is for {i}, proceed with this entity or choose another?")
                prompt = select_yes_no()
                if not prompt:
                    print("Please select entity: ")
                    entity = numbered_list(entities)
                    print(entity)
                elif prompt:
                    entity = i
                    print(entity)
                rest_object['entity'] = entity
        return rest_object


def query_builder():
    criteria = []
    query_string = "query="
    while True:
        criterion = input()
        # If there are no queries and a blank line is submitted.
        if criterion == "" and len(criteria) == 0:
            print("Please enter at least 1 criteria for a search.")
            continue
        # For the first item submitted to the list.
        elif criterion != "" and len(criteria) == 0:
            criteria.append(criterion)
            query_string = query_string + criterion
            print("Submit further items with AND or AND NOT prefix for relation to search.")
            print("e.g. AND NOT status:archive")
        elif criterion != "" and len(criteria) > 0:
            criteria.append(criterion)
            query_string = query_string + ' ' + criterion
        # The user is finished submitting items to the list
        elif criterion == "" and len(criteria) >= 1:
            print(f'Final query: {query_string}.')
            return query_string


def list_editor(items):
    i = 0
    for item in items:
        print(f'{i} - {item}')
    print("Enter the number of an item to edit:")
    while True:
        choice = select_integer()
        if choice > len(items):
            print("Number not in list, try again.")
            continue
        else:
            break
    print(f"Editing {items[choice]}")
    print("Please retype this value:")
    items[choice] = input()
    return items


def field_builder():
    fields = []
    field_string = "fields=id"
    while True:
        field = input()
        if field != "":
            fields.append(field)
        elif field == "":
            for i in fields:
                print(i)
        print("Proceed with current field list?")
        if select_yes_no():
            break
        else:
            fields = list_editor(fields)
    for i in fields:
        field_string = field_string + ',' + i
    return field_string


def request_handler(request, method):
    response = requests.request(method, request)
    if response.status_code == 200:
        json_response = json.loads(response.text)
        if json_response['count'] < json_response['total']:
            cumulative_data = json_response['data']
            while True:
                remaining = json_response['total'] - (json_response['start'] + json_response['count'])
                if remaining > 1:
                    count = 500
                    start = json_response['start'] + json_response['count']
                    list_breaker = f'&start={start}&count={count}'
                    further_request = request + list_breaker
                    response = requests.request(method, further_request)
                    json_response = json.loads(response.text)
                    for i in json_response['data']:
                        cumulative_data.append(i)
                else:
                    json_response['data'] = cumulative_data
                    return json_response
        else:
            return json_response
    else:
        print(f"Error: {response}")


def entity_search(entity):
    url = f"{rest_info['rest_url']}/search/{entity}?"
    print("What criteria are we searching for?")
    print("Enter each item one at a time, the first criteria must be inclusive.")
    print("e.g.: firstName:John")
    query = '&' + query_builder()
    print("What fields do you want returned?")
    print("Enter each item one at a time.")
    fields = field_builder()
    url = url + fields + query + '&BhRestToken=' + rest_info['BhRestToken']
    print(url)
    results = request_handler(url, 'get')
    print(f"There are {results['total']} results - print now?")
    if select_yes_no():
        for i in results['data']:
            print(i)
    print("Save to a list?")
    if select_yes_no():
        print("Please name this list:")
        list_name = input()
        saved_lists[list_name: results['data']]
        print(saved_lists)
    print("Export to CSV?")
    if select_yes_no():
        df = pd.read_json(json.dumps(results['data']))
        df.to_csv('csvfile.csv', encoding='utf-8', index=False)


actions = ["add", "search", "back"]

rest_info = get_rest_info()
if 'entity' not in rest_info:
    rest_info['entity'] = numbered_list(entities)
choice = numbered_list(actions)
if choice == 'search':
    entity_search(rest_info['entity'])






