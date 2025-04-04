from unittest.mock import patch

import pytest
from src.anki_api.requestModule import (
    check_connection,
    check_result,
    create_request,
    ensure_connectivity,
    invoke_request,
    request_action,
)


# Mock the environment variable for testing
@pytest.fixture(autouse=True)
def setup_environment():
    with patch.dict("os.environ", {"AnkiConnection": "0"}):
        yield


def test_check_connection_success(requests_mock):
    # Mock the AnkiConnect server response
    requests_mock.get("http://127.0.0.1:8765", text="AnkiConnect v.6")

    # Test the connection check
    assert check_connection() is True


def test_check_connection_failure(requests_mock):
    # Mock the AnkiConnect server response with an incorrect value
    requests_mock.get("http://127.0.0.1:8765", text="Incorrect response")

    # Test the connection check
    assert check_connection() is False


def test_ensure_connectivity_decorator():
    @ensure_connectivity
    def dummy_function():
        return "Success"

    with patch("src.anki_api.requestModule.check_connection", return_value=True):
        assert dummy_function() == "Success"

    with patch("src.anki_api.requestModule.check_connection", return_value=False):
        assert dummy_function() is None


def test_create_request():
    # Test creating a request
    request_data = create_request("testAction", 6, param1="value1", param2="value2")
    expected_data = '{"action": "testAction", "version": 6, "params": {"param1": "value1", "param2": "value2"}}'

    assert request_data == expected_data


def test_invoke_request(requests_mock):
    # Mock the AnkiConnect server response
    requests_mock.get(
        "http://127.0.0.1:8765", json={"result": "Success", "error": None}
    )

    # Test invoking a request
    response = invoke_request("http://127.0.0.1:8765", "testAction", 6, param1="value1")
    assert response.json() == {"result": "Success", "error": None}


def test_check_result_valid():
    # Test with a valid response
    response = {"result": "Success", "error": None}
    check_result(response)  # Should pass without raising an exception


def test_check_result_missing_error():
    # Test with a response missing the 'error' field
    response = {"result": "Success", "eror": None}
    with pytest.raises(KeyError, match="Response is missing required error field"):
        check_result(response)


def test_check_result_missing_result():
    # Test with a response missing the 'result' field
    response = {"reslt": "Success", "error": None}
    with pytest.raises(KeyError, match="Response is missing required result field"):
        check_result(response)


def test_check_result_invalid_length():
    # Test with a response of invalid length
    response = {"result": "Success"}
    with pytest.raises(IndexError, match="Invalid response length"):
        check_result(response)


def test_check_result_non_null_error():
    # Test with a response where 'error' is not None
    response = {"result": None, "error": "Server error"}
    with pytest.raises(Exception, match="Server returned error: Server error"):
        check_result(response)


def test_request_action_success(requests_mock):
    # Mock the AnkiConnect server response
    requests_mock.get(
        "http://127.0.0.1:8765", json={"result": "Success", "error": None}
    )

    # Test the full request action
    # Use path to simulate active AnkiConnect server
    with patch("src.anki_api.requestModule.check_connection", return_value=True):
        response = request_action("testAction", param1="value1")

    assert response == {"result": "Success", "error": None}


def test_request_action_invalid_response(requests_mock):
    # Mock an invalid response
    requests_mock.get("http://127.0.0.1:8765", json={"result": "Success"})

    # Test the full request action with an invalid response
    # Use path to simulate active AnkiConnect server
    with patch("src.anki_api.requestModule.check_connection", return_value=True):
        response = request_action("testAction", param1="value1")

    assert response["error"] is not None
    assert isinstance(response["error"], IndexError)


def test_request_action_invalid_result(requests_mock):
    # Mock an invalid response
    requests_mock.get("http://127.0.0.1:8765", json={"reslt": "Success", "error": None})

    # Test the full request action with an invalid response
    # Use path to simulate active AnkiConnect server
    with patch("src.anki_api.requestModule.check_connection", return_value=True):
        response = request_action("testAction", param1="value1")

    assert response["error"] is not None
    assert isinstance(response["error"], KeyError)


def test_request_action_invalid_error(requests_mock):
    # Mock an invalid response
    requests_mock.get("http://127.0.0.1:8765", json={"result": "Success", "eror": None})

    # Test the full request action with an invalid response
    # Use path to simulate active AnkiConnect server
    with patch("src.anki_api.requestModule.check_connection", return_value=True):
        response = request_action("testAction", param1="value1")

    assert response["error"] is not None
    assert isinstance(response["error"], KeyError)


def test_request_action_server_error(requests_mock):
    # Mock a server error response
    requests_mock.get(
        "http://127.0.0.1:8765", json={"result": None, "error": "Server error"}
    )

    # Test the full request action with a server error
    # Use path to simulate active AnkiConnect server
    with patch("src.anki_api.requestModule.check_connection", return_value=True):
        response = request_action("testAction", param1="value1")

    assert response["error"] is not None
    assert isinstance(response["error"], Exception)
