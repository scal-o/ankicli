from pathlib import Path

import pytest

from python.img_plugin import im_list
from python.rendererModule import markdown

## Tests for the img plugin


def test_basic_inline_image():
    # Define a Markdown string with a single inline image
    md_text = "Here is an image: ![[image1.png]]"

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = '<p>Here is an image: <img src="image1.png"></p>\n'

    # Check if the output matches the expected HTML
    assert html_output == expected_html

    # Check if the image source is added to im_list
    expected_res = [{"filename": "image1.png", "path": Path("image1.png").absolute()}]
    assert im_list == expected_res

    # Clear im_list for the next test
    im_list.clear()


def test_multiple_inline_images():
    # Define a Markdown string with multiple inline images
    md_text = "Image 1: ![[image1.png]] and Image 2: ![[image2.png]]"

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = (
        '<p>Image 1: <img src="image1.png"> and Image 2: <img src="image2.png"></p>\n'
    )

    # Check if the output matches the expected HTML
    assert html_output == expected_html

    # Check if both image sources are added to im_list
    expected_res = [
        {"filename": "image1.png", "path": Path("image1.png").absolute()},
        {"filename": "image2.png", "path": Path("image2.png").absolute()},
    ]
    assert im_list == expected_res

    # Clear im_list for the next test
    im_list.clear()


def test_no_inline_images():
    # Define a Markdown string without inline images
    md_text = "This is a paragraph without any images."

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = "<p>This is a paragraph without any images.</p>\n"

    # Check if the output matches the expectedHTML
    assert html_output == expected_html

    # Check if im_list remains empty
    assert im_list == []


def test_image_not_found():
    # Define a Markdown string with a non-existing image
    md_text = "Image1: ![[non_existing_img.png]]"

    # Check that trying to render the Markdown as HTML raises a FileNotFoundError
    with pytest.raises(FileNotFoundError):
        markdown(md_text)
    