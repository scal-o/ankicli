import pytest

from python.parseModule import get_lines, extract_properties, get_properties_metadata, get_deck, get_tags

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
    lines = ["---\n", "property1: value1\n", "property2: value2\n", "...\n", "content1\n", "content2\n"]
    properties, content = extract_properties(lines)
    assert properties == ["---\n", "property1: value1\n", "property2: value2\n", "...\n"]
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