import requests
import json
from getpass import getpass
from urllib.parse import parse_qs
from os import system


def validated_integer(prompt, digits=0):
    print(prompt)
    while True:
        try:
            i = int(input())
            if digits == 0:
                return i
            else:
                if len(str(i)) != digits:
                    print(f"Please enter a {digits} digit value.")
                else:
                    return i
        except ValueError:
            print("Please enter a valid whole number.")
            
            
def print_list(items, numbered=True):
    i = 0
    for item in items:
        if numbered:
            print(f'{i} - {item}')
            i += 1
        else:
            print(item)


def select_yes_no(prompt=""):
    if prompt != "":
        print(prompt)
    while True:
        prompt = input("(Y)es/(N)o: ")
        prompt = prompt.lower()
        if 'y' in prompt:
            return True
        elif 'n' in prompt:
            return False
        print("Input not recognized, please try again.")
    
        
def choose_from_list(items):
    print_list(items)
    while True:
        try:
            choice = validated_integer("Pick an item:")
            return items[choice]
        except IndexError:
            print("Please choose a valid item.")


def validated_string(prompt, length=0):
    print(prompt)
    while True:
        user_input = input()
        if user_input != "":
            if length == 0:
                return user_input
            elif len(user_input) == int(length):
                return user_input
            print(f"Please enter a {length} character string. ")
        else:
            print("Please enter a value.")


def request_handler(request_url, method):
    i = 0
    while True:
        response = requests.request(method, request_url)
        print(f"{request_url} - {response}")
        if response.status_code == 200:
            return response
        elif "entityNotFound" in response.text:
            return response
        elif response.status_code == 503:
            print("Service unavailable - Failed to connect - Trying again...")
            i += 1
            if i == 10:
                print("10 Failures to connect. Aborting.")
                break
            continue
        else:
            if response.text:
                print(response.text)
            return response


def authenticate():
    def get_user_and_pass():
        username = validated_string("Please enter your API Username:")
        while True:
            password = getpass()
            if password != "":
                return f'username={username}&password={password}'
            print("Password can't be blank, try again.")

    def get_oauth():
        clientid = validated_string("Please enter your client ID: ")
        clientsecret = validated_string("Please enter your client secret: ")
        return clientid, clientsecret

    def get_datacenter():
        while True:
            swimlane = str(validated_integer("Please enter a swimlane", 2))
            if swimlane.startswith('4'):
                return "rest-east"
            elif swimlane.startswith('3'):
                return "rest-west"
            elif swimlane == "50":
                return "rest-west"
            elif swimlane == "60":
                return "rest-apac"
            elif swimlane == "66":
                return "rest-aus"
            elif swimlane == "29":
                return "rest-emea9"
            elif swimlane.startswith('2'):
                return "rest-emea"
            elif swimlane == "70":
                return "rest-ger"
            elif swimlane == "71":
                return "rest-fra"
            elif swimlane.startswith('9'):
                return "rest-emea9"
            print(f"Error: swimlane invalid, please try again.")

    datacenter = get_datacenter()

    rest_auth_url = f"https://{datacenter}.bullhornstaffing.com/oauth/"
    auth_url = rest_auth_url.replace('rest', 'auth')

    user_and_pass = get_user_and_pass()
    client_id, client_secret = get_oauth()

    redirect_uri = input("Please enter a redirect URI, leave blank for none: ")

    # TODO: Find out about State Value. https://bullhorn.github.io/Getting-Started-with-REST/
    while True:
        request_url = f"{auth_url}authorize?client_id={client_id}&response_type=code&action=Login&{user_and_pass}"
        if redirect_uri != "":
            request_url += f"&redirect_uri={redirect_uri}"
        response = request_handler(request_url, "get")
        if "Invalid credentials" in response.text:
            print("Invalid username or password, please try again:")
            user_and_pass = get_user_and_pass()
            continue
        parsed_response = parse_qs(response.url)
        auth_code = list(parsed_response.values())[0][0]
        request_url = f"{auth_url}token?grant_type=authorization_code&code={auth_code}" \
                      f"&client_id={client_id}&client_secret={client_secret}"
        if redirect_uri != "":
            request_url += f"&redirect_uri={redirect_uri}"
        response = request_handler(request_url, "post")
        if "invalid_client" in response.text:
            print("Invalid client ID/Secret - please try again: ")
            client_id, client_secret = get_oauth()
            continue
        break

    json_response = json.loads(response.text)
    request_url = f"https://{datacenter}.bullhornstaffing.com/rest-services/login?" \
                  f"version=*&access_token={json_response['access_token']}"
    response = request_handler(request_url, "post")
    json_response = json.loads(response.text)
    return json_response['BhRestToken'], json_response['restUrl']


class RestInfo:
    def __init__(self):
        choice = choose_from_list(["Parse URL", "Manually enter details", "Full REST Authentication"])
        if "Parse" in choice:
            self.parse_url()

        elif "Manually" in choice:
            self.manual_input()

        elif "Authentication" in choice:
            self.token, self.rest_url = authenticate()

        request_url = self.rest_url + f"entity/Candidate/1?fields=id&BhRestToken={self.token}"
        response = request_handler(request_url, "get")
        if "entityNotFound" in response.text or response.status_code == 200:
            print(f"{self.rest_url} - Connection validated")
        self.connection = True

    def parse_url(self):
        while True:
            url = input("Paste in URL: ")
            if "bullhornstaffing" not in url:
                print("Invalid link entered, please try again.")
            else:
                break

        parsed = parse_qs(url)
        if "BhRestToken" in parsed:
            self.token = str(parsed['BhRestToken']).strip("[]'")
        else:
            # TODO: Give option to paste another URL.
            print("BhRestToken not found in URL, enter manually now:")
            self.token = input()

        split_string = url.split('/')
        if split_string[3] == "core":
            corp_token = validated_string("Corp Token not recognized, please enter now: ", 6)
            split_string[2] = split_string[2].replace('cls', 'rest')
        else:
            corp_token = split_string[4]
        self.rest_url = "https://" + split_string[2] + "/rest-services/" + corp_token + "/"

    def manual_input(self):
        corp_token = (validated_string("Enter corp token: ", 6)).lower()
        swimlane = validated_integer("Please enter a swimlane", 2)
        self.rest_url = "https://rest" + str(swimlane) + ".bullhornstaffing.com/rest-services/" + corp_token + "/"
        self.token = input("Enter a BhRestToken: ")


rest_object = RestInfo()
wait = input("Done..")