"""
module defining a mistune plugin for math expressions
"""

# math patterns
BLOCK_MATHJAX_PATTERN = r"\$\$(?![ \t])(?P<mathjax_text_block>.+?)(?<![ \t])\$\$"
INLINE_MATHJAX_PATTERN = (
    r"(?<!\$)\$(?!\$)(?![ \t])(?P<mathjax_text_inline>.+?)(?<![ \t])(?<!\$)\$(?!\$)"
)


# inline math expression parsing function
def parse_inline_mathjax(inline, m, state):
    math_expr = m.group("mathjax_text_inline")
    state.append_token({"type": "inline_math", "raw": math_expr})

    # return end position of parsed text
    return m.end()


# inline math expression rendering function
def render_inline_mathjax(renderer, text):
    return f"<span><anki-mathjax>{text}</anki-mathjax></span>"


# block math expression parsing function
def parse_block_mathjax(inline, m, state):
    math_expr = m.group("mathjax_text_block")
    state.append_token({"type": "block_math", "raw": math_expr})

    # return end position of parsed text
    return m.end()


# inline image rendering function
def render_block_mathjax(renderer, text):
    return f"<div><anki-mathjax>{text}</anki-mathjax></div>"


# image plugin
def mathjax(md):
    md.inline.register("inline_math", INLINE_MATHJAX_PATTERN, parse_inline_mathjax, before="link")
    md.inline.register("block_math", BLOCK_MATHJAX_PATTERN, parse_block_mathjax, before="link")

    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("inline_math", render_inline_mathjax)
        md.renderer.register("block_math", render_block_mathjax)
