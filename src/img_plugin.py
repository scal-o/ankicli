"""
module defining a mistune plugin for inline images
"""

from pathlib import Path

im_list = []

# inline image pattern
INLINE_IMG_PATTERN = r"!\[\[(?P<img_src>[\w\s\.]+)\]\]"


def find_image_data(filename: str) -> dict:
    """Function to find image filename and path.
    Returns a dictionary with keys 'filename' and 'path'."""

    # create image Path obj
    filepath = Path(filename)

    # check that the image exists in the current directory
    if filepath.absolute().exists():
        filepath = filepath.absolute()
    else:
        raise FileNotFoundError(
            "\nError in parsing:\n",
            f"file '{filepath}' does not exist in the current working directory.\n",
        )

    return {"filename": str(filename), "path": filepath}


# inline image parsing function
def parse_inline_img(inline, m, state):
    img_src = m.group("img_src")
    state.append_token({"type": "inline_img", "raw": img_src})

    # create a dict containing image filename and path
    img_dict = find_image_data(img_src)

    # append image source to list
    im_list.append(img_dict)

    # return end position of parsed text
    return m.end()


# inline image rendering function
def render_inline_img(renderer, text):
    return f'<img src="{text}">'


# image plugin
def img(md):
    md.inline.register("inline_img", INLINE_IMG_PATTERN, parse_inline_img, before="link")

    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("inline_img", render_inline_img)
