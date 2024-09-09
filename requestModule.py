import json
import requests
import os
import time

"""Module containing low-level request handlers for the ankiConnect HTTP server"""

localhost = "http://127.0.0.1"
PORT = "8765"
link = localhost + ":" + PORT


def check_connection(url=link):
    """Low level function to check connection to ankiConnect server"""

    # adds a check to the environment variable AnkiConnection to see if the connection has been checked in the last ten
    # seconds. If it is, assume it is still open and return True without further checks. This is done to avoid calling
    # the function 100 times in a matter of seconds when uploading a large amount of cards.
    if time.time() - float(os.environ.get("AnkiConnection", "0")) < 10:
        return True

    try:
        # checks connection to the http server by making a get request and checking its return value against the
        # hardcoded one
        r = requests.get(url=url)
        check_string = "AnkiConnect v.6"

        if r.text == check_string:
            os.environ["AnkiConnection"] = str(time.time())
            return True
        else:
            os.environ["AnkiConnection"] = "0"
            raise Exception(f"Connection to ankiConnect unsuccessful. Expected response: {check_string}.n"
                            f"Actual response: {r.text}")

    except Exception as er:
        os.environ["AnkiConnection"] = "0"
        print("The connection was refused from the server. Check that Anki is open and AnkiConnect is installed.")
        print(f"Exception: {er}")
        return False


def ensure_connectivity(func):
    """Decorator used to check connection before read/write operations"""
    def wrapper(*args, **kwargs):
        if check_connection() is True:
            if len(kwargs) == 0:
                return func(*args)
            else:
                return func(*args, **kwargs)
        else:
            print("Operation aborted.")
    return wrapper


def create_request(action, version, **kwargs):
    """Creates json like object containing all info necessary for the request"""
    return json.dumps({"action": action, "version": version, "params": kwargs})


def invoke_request(url, action, version, **kwargs):
    """Sends request to the ankiConnect HTTP server and returns the response object"""
    r = requests.get(url=url, data=create_request(action, version, **kwargs))
    return r


def check_result(response):
    """Checks that the result is valid and that no errors occurred"""

    if len(response) != 2:
        raise IndexError("Invalid response length")
    elif "error" not in response.keys():
        raise KeyError("Response is missing required error field")
    elif "result" not in response.keys():
        raise KeyError("Response is missing required result field")
    elif response["error"] is not None:
        raise Exception(f"Server returned error: {response["error"]}")


@ensure_connectivity
def request_action(action, url=link, version=6, **kwargs):
    """Higher level function that handles the whole connection process and returns the server response"""

    response = invoke_request(url, action, version, **kwargs).json()

    try:
        check_result(response)
    except KeyError as er:
        print(f"Error in request_action: {er}")
        response = {"result": None, "error": er}
    except IndexError as er:
        print(f"Error in request_action: {er}")
        response = {"result": None, "error": er}
    except Exception as er:
        print(f"Action '{action}' unsuccessful. Exception raised:")
        print(er)

    return response
