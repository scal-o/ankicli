import pandas as pd
import pytest

from python.parseModule import (
    extract_properties,
    get_deck,
    get_lines,
    get_properties_metadata,
    get_tags,
    group_lines,
    parse_card,
)


def test_get_lines(mocker):
    # Mock the open function using pytest-mock
    mock_file_content = "line1\nline2\nline3"
    mock_open = mocker.mock_open(read_data=mock_file_content)
    mocker.patch("builtins.open", mock_open)

    # Test if get_lines reads all lines from a file
    result = get_lines("dummy_path")
    assert result == ["line1\n", "line2\n", "line3"]


def test_extract_properties():
    # Test if extract_properties correctly separates properties from other lines
    lines = [
        "---\n",
        "property1: value1\n",
        "property2: value2\n",
        "...\n",
        "content1\n",
        "content2\n",
    ]
    properties, content = extract_properties(lines)
    assert properties == [
        "---\n",
        "property1: value1\n",
        "property2: value2\n",
        "...\n",
    ]
    assert content == ["content1\n", "content2\n"]


def test_get_properties_metadata():
    # Test if get_properties_metadata correctly parses properties into a dictionary
    properties = ["---\n", "deck: test_deck\n", "tags: [tag1, tag2]\n", "...\n"]
    metadata = get_properties_metadata(properties)
    assert metadata == {"deck": "test_deck", "tags": ["tag1", "tag2"]}


def test_get_deck():
    # Test if get_deck correctly extracts the deck name
    metadata = {"deck": "test_deck"}
    deck = get_deck(metadata)
    assert deck == "test_deck"

    # Test if get_deck raises ValueError when deck is None
    with pytest.raises(ValueError):
        get_deck({})

    # Test if get_deck raises TypeError when deck is not a string
    with pytest.raises(TypeError):
        get_deck({"deck": 123})


def test_get_tags():
    # Test if get_tags correctly extracts the tags list
    metadata = {"tags": ["tag1", "tag2"]}
    tags = get_tags(metadata)
    assert tags == ["tag1", "tag2"]

    # Test if get_tags returns a list when tags is a string
    metadata = {"tags": "single_tag"}
    tags = get_tags(metadata)
    assert tags == ["single_tag"]

    # Test if get_tags raises TypeError when tags is not a list or string
    with pytest.raises(TypeError):
        get_tags({"tags": 123})


def test_group_lines():
    # Define a list of lines with various content
    lines = [
        "This is a regular line.\n",
        "Another regular line.\n",
        "Inline card content::example^1\n",  # Matches inline_card pattern
        "\n",  # Empty line
        "More regular text.\n",
        "Yet another line.\n",
        "\n",  # Another empty line
        "Final line with inline card::example^2\n",  # Matches inline_card pattern
    ]

    # Define the expected output
    expected_groups = [
        ["This is a regular line.\n", "Another regular line.\n"],
        ["Inline card content::example^1\n"],
        ["\n"],
        ["More regular text.\n", "Yet another line.\n"],
        ["\n"],
        ["Final line with inline card::example^2\n"],
    ]

    # Group lines using the function
    grouped_lines = group_lines(lines)

    # Compare the actual output to the expected output
    assert grouped_lines == expected_groups


def test_group_lines_no_matches():
    # Define a list of lines with no matches for inline_card or empty_line
    lines = ["Regular line 1.\n", "Regular line 2.\n", "Regular line 3.\n"]

    # Define the expected output
    expected_groups = [["Regular line 1.\n", "Regular line 2.\n", "Regular line 3.\n"]]

    # Group lines using the function
    grouped_lines = group_lines(lines)

    # Compare the actual output to the expected output
    assert grouped_lines == expected_groups


def test_group_lines_all_matches():
    # Define a list of lines where every line matches inline_card or empty_line
    lines = [
        "Inline card 1::example^1\n",
        "\n",
        "Inline card 2::example^2\n",
        "\n",
    ]

    # Define the expected output
    expected_groups = [
        ["Inline card 1::example^1\n"],
        ["\n"],
        ["Inline card 2::example^2\n"],
        ["\n"],
    ]

    # Group lines using the function
    grouped_lines = group_lines(lines)

    # Compare the actual output to the expected output
    assert grouped_lines == expected_groups


def test_parse_card_basic():
    # Define a list of lines for a basic card
    lines = [
        ">[!question]- What is the capital of France? #card\n",
        "> Paris\n",
        "<!--ID: 1-->\n",
    ]

    # Define the expected output
    expected_series = pd.Series(
        ["What is the capital of France?", "Paris", 1, False, "Basic", True],
        index=["front", "back", "id", "inline", "modelName", "is_card"],
    )

    # Parse the card using the function
    result = parse_card(lines)

    # Compare the actual output to the expected output
    pd.testing.assert_series_equal(result, expected_series)


def test_parse_card_inline():
    # Define a list of lines for an inline card
    lines = ["What is the capital of France?::Paris^1\n"]

    # Define the expected output
    expected_series = pd.Series(
        ["What is the capital of France?", "Paris", 1, True, "Basic", True],
        index=["front", "back", "id", "inline", "modelName", "is_card"],
    )

    # Parse the card using the function
    result = parse_card(lines)

    # Compare the actual output to the expected output
    pd.testing.assert_series_equal(result, expected_series)


def test_parse_card_inline_reverse():
    # Define a list of lines for an inline card
    lines = ["What is the capital of France?:::Paris^1\n"]

    # Define the expected output
    expected_series = pd.Series(
        [
            "What is the capital of France?",
            "Paris",
            1,
            True,
            "Basic (and reversed card)",
            True,
        ],
        index=["front", "back", "id", "inline", "modelName", "is_card"],
    )

    # Parse the card using the function
    result = parse_card(lines)

    # Compare the actual output to the expected output
    pd.testing.assert_series_equal(result, expected_series)


def test_parse_card_empty():
    # Test with return_empty set to True
    result = parse_card([], return_empty=True)

    # Define the expected output
    expected_series = pd.Series(
        ["", "", None, False, "Basic", False],
        index=["front", "back", "id", "inline", "modelName", "is_card"],
    )

    # Compare the actual output to the expected output
    pd.testing.assert_series_equal(result, expected_series)


def test_parse_card_no_id():
    # Define a list of lines for an incomplete card
    lines = [
        ">[!question]- What is the capital of France? #card\n",
        "> Paris\n",
    ]

    # Define the expected output
    expected_series = pd.Series(
        ["What is the capital of France?", "Paris", None, False, "Basic", True],
        index=["front", "back", "id", "inline", "modelName", "is_card"],
    )

    # Parse the card using the function
    result = parse_card(lines)

    # Compare the actual output to the expected output
    pd.testing.assert_series_equal(result, expected_series)


def test_parse_card_inline_no_id():
    # Define a list of lines for an inline card
    lines = ["What is the capital of France?::Paris\n"]

    # Define the expected output
    expected_series = pd.Series(
        ["What is the capital of France?", "Paris", None, True, "Basic", True],
        index=["front", "back", "id", "inline", "modelName", "is_card"],
    )

    # Parse the card using the function
    result = parse_card(lines)

    # Compare the actual output to the expected output
    pd.testing.assert_series_equal(result, expected_series)


def test_parse_card_mixed_content():
    # Define a list of lines with mixed content

    lines = [
        "Random text\n",
        ">[!question]- What is the capital of France? #card\n",
        "> Paris\n",
        "More random text\n",
    ]

    # Define the expected output
    expected_series = pd.Series(
        ["What is the capital of France?", "Paris", None, False, "Basic", True],
        index=["front", "back", "id", "inline", "modelName", "is_card"],
    )

    # Parse the card using the function
    result = parse_card(lines)

    # Compare the actual output to the expected output
    pd.testing.assert_series_equal(result, expected_series)
