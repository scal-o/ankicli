import re
import copy
import os
"""Module to handle parsing of text files"""

# define a list of options used to compile the regular expressions throughout the module
precompiled = {
    "properties": "---",
    "deck": r"cards-deck: ([\w:\-_\s]+)",
    "tags": r"^- ([\w/]+)",
    "question": r"^>\[!question]-?\s*(.+)(#card)",
    "answer": r"^>",
    "id": r"<!--ID: (\d+)-->|\^(\d+)",
    "empty_line": r"(\s+)?\n",
    "image": r"!\[\[([\w\s\.]+)\]\]",
    "math": r"\$([^\s][^\$]+)\$",
    "math_block": r"\${2}([^\$]+)\${2}",
    "inline_card": r"-?(.+)::([^\^]+)\^?(\d+)?",
    "inline_reverse_card": r"-?(.+):::([^\^]+)\^?(\d+)?"
}

id_format = "^{}\n"
inline_id_format = "{} ^{}\n"


def get_lines(path):
    """Simple low-level function to read all lines from a file"""

    with open(path, mode="r", encoding="utf-8") as f:
        lines = list(f)
    return lines


def get_properties(lines: list) -> tuple[list, list]:
    """Function that retrieves all the lines that make up the yaml properties frontmatter"""

    # compiles the regex expression before using it
    properties_re = re.compile(precompiled["properties"])

    # gets initial and final indices of the yaml frontmatter
    properties_indexes = [i for i, j in enumerate(lines) if properties_re.search(j) is not None]
    properties_indexes[1] += 1
    # gets properties text from file lines
    properties = [j.strip() for i, j in enumerate(lines) if i in range(properties_indexes[0], properties_indexes[1])]

    return properties, properties_indexes


def get_deck(properties) -> str:

    # compile the regex expression before using it
    deck_re = re.compile(precompiled["deck"])

    # extract the deck from the yaml frontmatter
    deck = [deck_re.search(line)[1] for line in properties if deck_re.search(line) is not None]

    # if no deck name is defined, return none (or maybe default with a warning?)
    if len(deck) == 0:
        return None
    else:
        return deck[0]


def get_tags(properties) -> list:

    # compile the regex expression before using it
    tags_re = re.compile(precompiled["tags"])

    # extract the tags from the yaml frontmatter
    tags = [tags_re.search(line)[1].replace("/", "::") for line in properties if tags_re.search(line) is not None]

    return tags


def format_images(lines: list) -> tuple:
    """Function to format lines containing images, wrapping their references in HTML syntax.
    Returns a list of the formatted lines and a list of dictionaries containing the image information."""

    # compile the regex expression
    image_re = re.compile(precompiled["image"])

    # initialize lists
    images = []
    formatted_lines = []

    # format lines and append images filenames and paths to the images list
    for line in lines:
        for im in image_re.findall(line):
            images.append({"filename": im, "path": os.path.join(os.getcwd(), im)})
            line = line.replace("![[", "<img src=\"", 1).replace("]]", "\">", 1)
        formatted_lines.append(line)

    return formatted_lines, images


def format_math(lines: list) -> list:
    """Function to format lines containing math expressions, wrapping them in anki-mathjax HTML syntax."""

    # compile the regex expressions
    math_re = re.compile(precompiled["math"])
    math_block_re = re.compile(precompiled["math_block"])

    # initialize list
    formatted_lines = []

    # format lines
    for line in lines:

        for expr in math_block_re.findall(line):
            line = math_block_re.sub(f"<anki-mathjax block=true>{expr}</anki-mathjax>", line)

        for expr in math_re.findall(line):
            line = math_re.sub(f"<anki-mathjax>{expr}</anki-mathjax>", line)

        formatted_lines.append(line)

    return formatted_lines


def card_gen(lines, deck=None, tags=None):
    """Creates a generator object to iterate through the file lines and retrieve cards one by one, allowing the caller
    to modify the underlying lines list (for example by inserting the card id after uploading it)"""

    question_re = re.compile(precompiled["question"])
    answer_re = re.compile(precompiled["answer"])
    id_re = re.compile(precompiled["id"])
    empty_line_re = re.compile(precompiled["empty_line"])
    inline_re = re.compile(precompiled["inline_card"])
    inline_reverse_re = re.compile(precompiled["inline_reverse_card"])

    # create a standard dictionary to use as a template
    std_dict = {"Front": None, "Back": None, "id": None, "deckName": deck, "tags": tags}
    card_dict = copy.deepcopy(std_dict)

    for i, line in enumerate(lines):

        # inline card parser
        if (r := inline_reverse_re.search(line)) is not None:
            card_dict["modelName"] = "Basic (and reversed card)"
        else:
            r = inline_re.search(line)

        if r is not None:
            card_dict["Front"] = r.group(1).strip()
            card_dict["Back"] = r.group(2).strip()
            card_dict["id"] = int(r.group(3)) if r.group(3) is not None else None
            card_dict["inline"] = True
            yield card_dict, i
            card_dict = copy.deepcopy(std_dict)

        # normal card parser
        if (r := question_re.search(line)) is not None:
            card_dict["Front"] = r.group(1)
        elif answer_re.search(line) is not None:
            if card_dict["Back"] is None:
                card_dict["Back"] = line.strip(">")
            else:
                card_dict["Back"] += line.strip(">")
        elif (r := id_re.search(line)) is not None:
            card_dict["id"] = [int(group) for group in r.groups() if group is not None][0]
        elif empty_line_re.search(line) is not None:
            if card_dict["Front"] is not None and card_dict["Back"] is not None:
                card_dict["Back"] = card_dict["Back"].replace("\n", "<br />")
                yield card_dict, i-1
                card_dict = copy.deepcopy(std_dict)

    # repeat check at end of file
    if card_dict["Front"] is not None and card_dict["Back"] is not None:
        card_dict["Back"] = card_dict["Back"].replace("\n", "<br />")
        yield card_dict, i
        card_dict = copy.deepcopy(std_dict)


def insert_card_id(lines, index, id, inline=False) -> None:
    """Function to insert the card id in the lines of the file. Simple wrapper around .insert"""

    if inline:
        id_line = inline_id_format.format(lines[index].strip(), id)
        lines[index] = id_line
    else:
        id_line = id_format.format(id)
        lines.insert(index, id_line)


def sub_card_id(lines: list, old_id: int, new_id: int) -> None:
    """Function to change card id for a card that doesn't exist anymore and is being recreated."""

    for line in lines:
        if re.search(f"{old_id}", line):
            id_line = id_format.format(old_id)
            i = lines.index(id_line)
            lines[i] = id_format.format(new_id)
