import copy
import os
import re
import numpy as np
import pandas as pd

"""Module to handle parsing of text files"""

# define a list of options used to compile the regular expressions throughout the module
precompiled = {
    "properties": "---",
    "deck": r"cards-deck: ([\w:\-_\s]+)",
    "tags": r"^- ([\w/]+)",
    "question": r"^>\[!question]-?\s*(.+)(#card)",
    "answer": r"^>(.*)(?<!\#card)$",
    "id": r"<!--ID: (\d+)-->|\^(\d+)",
    "empty_line": r"^(\s+)?\n",
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


def extract_properties(lines: list) -> tuple[list, list]:
    """Function that extracts the lines that make up the yaml frontmatter from the file lines.
    Returns a list containing the properties lines and another one containing the other file lines."""

    # compile the regex
    properties_re = re.compile(precompiled["properties"])

    # get yaml frontmatter indices
    indexes = [i for i, j in enumerate(lines) if properties_re.search(j) is not None]
    indexes[1] += 1

    # extract properties from lines
    properties = lines[:indexes[1]]
    lines = lines[indexes[1]:]

    return properties, lines


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


def scrape_images(line: str) -> list:
    """Function to scrape all the image names and paths from the provided lines.
    Returns a list of dictionary, with keys 'filename' and 'path'."""

    # compile the regex expression
    image_re = re.compile(precompiled["image"])
    images = []

    # TODO fix path when image is not in the same dir as the script
    # scrape image names and paths from text
    for im in image_re.findall(line):
        images.append({"filename": im, "path": os.path.join(os.getcwd(), im)})

    return images


def format_images(text: str) -> str:
    """Function to format lines containing images, wrapping their references in HTML syntax.
    Returns a list of the formatted lines and a list of dictionaries containing the image information."""

    # compile the regex expression
    image_re = re.compile(precompiled["image"])

    # format lines
    if image_re.search(text):
        text = text.replace("![[", "<img src=\"", 1).replace("]]", "\">", 1)

    return text


def format_math(text: str) -> str:
    """Function to format lines containing math expressions, wrapping them in anki-mathjax HTML syntax."""

    # compile the regex expressions
    math_re = re.compile(precompiled["math"])
    math_block_re = re.compile(precompiled["math_block"])

    # format lines
    for expr in math_block_re.findall(text):
        text = math_block_re.sub(f"<anki-mathjax block=true>{expr}</anki-mathjax>", text)

    for expr in math_re.findall(text):
        text = math_re.sub(f"<anki-mathjax>{expr}</anki-mathjax>", text)

    return text


def group_lines(lines: list) -> list[list]:
    """Takes a single list as argument and returns a list of lists, each containing some lines that could contain card
    information (or empty lines)."""
    full_text = []
    text = []

    inline_re = re.compile(precompiled["inline_card"])
    empty_line_re = re.compile(precompiled["empty_line"])

    for line in lines:
        if inline_re.search(line) or empty_line_re.search(line):
            if len(text) != 0:
                full_text.append(text)
                text = list()

            full_text.append([line])
        else:
            text.append(line)

    if len(text) != 0:
        full_text.append(text)

    return full_text


def parse_card(lines: list, return_empty=False) -> pd.Series:
    """Returns a pandas.Series object corresponding to a single card. The Series object has the following fields
    (indexes): front, back, id, inline, model."""

    question_re = re.compile(precompiled["question"])
    answer_re = re.compile(precompiled["answer"])
    id_re = re.compile(precompiled["id"])
    empty_line_re = re.compile(precompiled["empty_line"])
    inline_re = re.compile(precompiled["inline_card"])
    inline_reverse_re = re.compile(precompiled["inline_reverse_card"])

    index_names = ["front", "back", "id", "inline", "modelName", "is_card"]

    # create the base return values
    front = ""
    back = ""
    id = None
    inline = False
    model = "Basic"
    is_card = False

    if return_empty:
        return pd.Series([front, back, id, inline, model, is_card], index=index_names)

    for line in lines:

        # inline card parser
        if (r := inline_reverse_re.search(line)) is not None:
            model = "Basic (and reversed card)"
        else:
            r = inline_re.search(line)

        if r is not None:
            front = r.group(1).strip()
            back = r.group(2).strip()
            id = int(r.group(3)) if r.group(3) is not None else None
            inline = True
            is_card = True
            return pd.Series([front, back, id, inline, model, is_card], index=index_names)

        # normal card parser
        if (r := question_re.search(line)) is not None:
            front = r.group(1)
            is_card = True
        elif answer_re.search(line) is not None:
            if back is None:
                back = line.strip(">")
            else:
                back += line.strip(">")
        elif (r := id_re.search(line)) is not None:
            id = [int(group) for group in r.groups() if group is not None][0]
        elif empty_line_re.search(line) is not None:
            if front is not None and back is not None:
                back = back.replace("\n", "<br />")
                return pd.Series([front, back, id, inline, model, is_card], index=index_names)
    # repeat check at end of file
    if front is not None and back is not None:
        back = back.replace("\n", "<br />")

    return pd.Series([front, back, id, inline, model, is_card], index=index_names)


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


def insert_card_id(series: pd.Series) -> list[str]:
    """Function to insert or modify the card id in the text lines of the dataframe entry."""

    # precompile id regex
    id_re = re.compile(precompiled["id"])

    # create sub line
    if np.isnan(series.id):
        sub = ""
    else:
        sub = f"^{series.id}"

    # deepcopy text list to avoid modifying the original by mistake
    lines = copy.deepcopy(series.text)

    # retrieve last line of text from the series
    line = lines.pop()

    # three cases:
    # - the regex returns a match in the text -> sub the match with the new id
    # - no match and the card is an inline type -> sub \n in line with id + \n
    # - no match and no inline -> append new line with id
    if id_re.search(line):
        line = id_re.sub(f"{sub}", line)
    elif series.inline is True:
        line = re.sub("\n", f"{sub}\n", line)
    else:
        line = line + f"{sub}\n"

    # put the modified line in its original place
    lines.append(line)

    # return text lines
    return lines


def insert_card_id2(lines, index, id, inline=False) -> None:
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
