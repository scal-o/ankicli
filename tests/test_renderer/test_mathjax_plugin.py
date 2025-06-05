import mistune
from ankicli.renderer.mathjax_plugin import mathjax

# Initialize the Mistune Markdown instance with the math plugin
renderer = mistune.HTMLRenderer()
markdown = mistune.Markdown(renderer=renderer)
markdown.use(mathjax)

## Tests for the math plugin


def test_no_math():
    # Define a Markdown string without math expressions
    md_text = "This is a paragraph without any math expressions, but with some dollar signs like this 3$ and this $$."

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = "<p>This is a paragraph without any math expressions, but with some dollar signs like this 3$ and this $$.</p>\n"

    # Check if the output matches the expected HTML
    assert html_output == expected_html


def test_invalid_dollar_sequences():
    # Define a Markdown string with an invalid math expression ($$ left, $ right)
    md_text = "This is a paragraph with an invalid math expression: $$E=mc^2$."

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = (
        "<p>This is a paragraph with an invalid math expression: $$E=mc^2$.</p>\n"
    )

    # Check if the output matches the expected HTML
    assert html_output == expected_html


def test_invalid_spaces():
    # Define a Markdown string with an invalid math expression (spaces after / before $)
    md_text1 = "This is a paragraph with an invalid math expression: $$ E=mc^2$$."
    md_text2 = "This is a paragraph with an invalid math expression: $$E=mc^2 $$."
    md_text3 = "This is a paragraph with an invalid math expression: $ E=mc^2$."
    md_text4 = "This is a paragraph with an invalid math expression: $E=mc^2 $."

    # Render the Markdown to HTML
    html_output1 = markdown(md_text1)
    html_output2 = markdown(md_text2)
    html_output3 = markdown(md_text3)
    html_output4 = markdown(md_text4)

    # Define the expected HTML output
    expected_html1 = (
        "<p>This is a paragraph with an invalid math expression: $$ E=mc^2$$.</p>\n"
    )
    expected_html2 = (
        "<p>This is a paragraph with an invalid math expression: $$E=mc^2 $$.</p>\n"
    )
    expected_html3 = (
        "<p>This is a paragraph with an invalid math expression: $ E=mc^2$.</p>\n"
    )
    expected_html4 = (
        "<p>This is a paragraph with an invalid math expression: $E=mc^2 $.</p>\n"
    )

    # Check if the output matches the expected HTML
    assert html_output1 == expected_html1
    assert html_output2 == expected_html2
    assert html_output3 == expected_html3
    assert html_output4 == expected_html4


def test_basic_inline_math():
    # Define a Markdown string with a single inline math expression
    md_text = "Here is an inline math expression: $E=mc^2$."

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = "<p>Here is an inline math expression: <span><anki-mathjax>E=mc^2</anki-mathjax></span>.</p>\n"

    # Check if the output matches the expected HTML
    assert html_output == expected_html


def test_multiple_inline_math():
    # Define a Markdown string with multiple inline math expressions
    md_text = "First expression: $E=mc^2$ and second expression: $a^2 + b^2 = c^2$."

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = "<p>First expression: <span><anki-mathjax>E=mc^2</anki-mathjax></span> and second expression: <span><anki-mathjax>a^2 + b^2 = c^2</anki-mathjax></span>.</p>\n"

    # Check if the output matches the expected HTML
    assert html_output == expected_html


def test_basic_block_math():
    # Define a Markdown string with a single block math expression
    md_text = "Here is a block math expression:$$E=mc^2$$"

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = "<p>Here is a block math expression:<div><anki-mathjax>E=mc^2</anki-mathjax></div></p>\n"

    # Check if the output matches the expected HTML
    assert html_output == expected_html


def test_multiple_block_math():
    # Define a Markdown string with multiple block math expressions
    md_text = "First block:$$E=mc^2$$Second block:$$a^2 + b^2 = c^2$$"

    # Render the Markdown to HTML
    html_output = markdown(md_text)

    # Define the expected HTML output
    expected_html = (
        "<p>First block:"
        "<div><anki-mathjax>E=mc^2</anki-mathjax></div>"
        "Second block:"
        "<div><anki-mathjax>a^2 + b^2 = c^2</anki-mathjax></div></p>\n"
    )

    # Check if the output matches the expected HTML
    assert html_output == expected_html
