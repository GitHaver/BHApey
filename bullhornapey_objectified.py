import requests
import json
from getpass import getpass
from urllib.parse import parse_qs
from os import system
import operator
import curses


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
    for i, item in enumerate(items, start=1):
        if numbered:
            print(f'{i} - {item}')
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
            system('cls')
            return items[(choice-1)]
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
        elif response.status_code == 401:
            print(response.text)
            rest_object.token = input(validated_string("BhRestToken invalid, please enter one now: "))
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


def curses_columned_list(list_win, item_list, items_per_column, item_highlighted, selected_items=[]):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    y = 1
    x = 0
    longest = 0
    first = True
    for i in item_list:
        if len(i) > longest:
            longest = len(i)
        if y < items_per_column:
            if first:
                y = 1
            else:
                y += 1
        else:
            x += longest + 3
            y = 1
            longest = 0
        if i == item_highlighted:
            list_win.addstr(y, x, i, curses.A_REVERSE)
        else:
            list_win.addstr(y, x, i)
        list_win.refresh()
        first = False
    string = ""


def cursed_list(item_list):
    stdscr = curses.initscr()
    screen_y, screen_x = stdscr.getmaxyx()
    stdscr.addstr(0, 0, "Choose your items. Arrow keys to move, enter to select, tab to proceed with currently selected items.")
    stdscr.addstr(1, 0, "Type in letters to filter the list.")
    stdscr.refresh()
    curses.noecho()

    list_win = curses.newwin((screen_y - 4), screen_x, 4, 0)
    list_win.keypad(True)
    win_y, win_x = list_win.getmaxyx()
    items_per_column = win_y - 1

    selected_list_win = curses.newwin(2, screen_x, 2, 0)

    highlight = 0
    printing_list = item_list
    curses_columned_list(list_win, printing_list, items_per_column, printing_list[highlight])

    string = ""
    selected_items = []
    while True:
        list_index = len(printing_list)-1

        key = list_win.getkey()
        if key == '\b':
            if string != "":
                string = string[:-1]
                highlight = 0

        elif key == '\n':
            if printing_list[highlight] in selected_items:
                selected_items.remove(printing_list[highlight])
            else:
                selected_items.append(printing_list[highlight])

        elif key == 'KEY_UP':
            highlight -= 1
            if highlight < 0:
                highlight = list_index

        elif key == 'KEY_DOWN':
            highlight += 1
            if highlight > list_index:
                highlight = 0

        elif key == 'KEY_LEFT':
            highlight -= items_per_column
            if highlight < 0:
                highlight = list_index

        elif key == 'KEY_RIGHT':
            highlight += items_per_column
            if highlight > list_index:
                highlight = 0

        elif key == '\t':
            list_win.clear()
            list_win.addstr(0, 0, "Press ENTER to return with the selected items"
                                  ", or any other key to continue choosing items. ")
            if list_win.getkey() == '\n':
                break

        else:
            string += key
            highlight = 0

        list_win.clear()
        list_win.addstr(0, 0, string)
        list_win.refresh()

        if string != "":
            printing_list = []
            for i in item_list:
                if string.lower() in i.lower():
                    printing_list.append(i)
        else:
            printing_list = item_list

        selected_list_win.clear()
        selected_list_win.addstr(0, 0, ', '.join(selected_items))
        selected_list_win.refresh()

        stdscr.refresh()
        curses_columned_list(list_win, printing_list, items_per_column, printing_list[highlight], selected_items)

    list_win.keypad(False)
    curses.echo()
    curses.endwin()


def query_builder(entity):
    criteria = []
    query_string = "query="
    # Downloading candidate metadata
    entity_metadata = Entity(entity)
    label_list = []
    for i in entity_metadata.fields:
        label_list.append(i.label)
    cursed_list(label_list)


class Entity:
    name = ""
    fields = []

    def __init__(self, entity):
        self.name = entity
        meta_url = f"{rest_object.rest_url}/meta/{entity}?fields=*&meta=full&BhRestToken={rest_object.token}"
        entity_metadata = request_handler(meta_url, "get")
        entity_metadata = json.loads(entity_metadata.text)
        optional_elements = ['label', 'dataType', 'type', 'required', 'options']
        for field in entity_metadata['fields']:
            if field['name'] == 'id':
                field['readOnly'] = False
            if 'readOnly' in field:
                if 'sortOrder' not in field:
                    field['sortOrder'] = 0
                if not field['readOnly']:
                    for element in optional_elements:
                        if element not in field:
                            field[element] = "N/A"
                    print()
                    self.fields.append(self.Field(field))
        self.fields = sorted(self.fields, key=operator.attrgetter('sortOrder'))

    class Field:
        def __init__(self, field_items):
            self.name = field_items['name']
            self.label = field_items['label']
            self.sortOrder = field_items['sortOrder']
            self.dataType = field_items['dataType']
            self.type = field_items['type']
            self.required = field_items['required']
            if 'options' in field_items:
                self.options = field_items['options']


class Search:
    def __init__(self, entity):
        url = f"{rest_object.rest_url}/search/{entity}"
        query_builder(entity)


rest_object = RestInfo()
results = Search("Candidate")
wait = input("Done..")
