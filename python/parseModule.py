import copy
import logging
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

"""Module to handle parsing of text files"""

# set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(name)s::%(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)


# define a list of options used to compile the regular expressions throughout the module
precompiled = dict(
    properties="^---$|^...$",
    question=r"^>\[!question]-?\s*(.+)(#card)",
    answer=r"^>(.*)(?<!\#card)$",
    id=r"<!--ID: (\d+)-->|\^(\d+)\n",
    empty_line=r"^(\s+)?\n",
    image=r"!\[\[([\w\s\.]+)\]\]",
    math=r"\$(?! |\.)([^\$]+)\$",
    math_block=r"\${2}([^\$]+)\${2}",
    inline_card=r"-?(.+)::([^\^]+)\^?(\d+)?",
    inline_reverse_card=r"-?(.+):::([^\^]+)\^?(\d+)?"
)

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


def get_properties_metadata(properties: list) -> dict:
    """Function that takes the properties yaml frontmatter as input and returns a dictionary 
    containing the file's metadata as key-value pairs."""

    # join file lines as a single string
    prop_string = "".join(properties[:-1])
    
    # read file metadata
    d = yaml.safe_load(prop_string)

    return d


def get_deck(metadata: dict) -> str:
    """Wrapper around dict.get to extract deck name from file metadata."""
    
    deck = metadata.get("deck", None)
    
    # return deck name as a string, raise an Exception in case of failure
    if isinstance(deck, str):
        return deck

    elif deck is None:
        raise ValueError(
            "\nError in reading the yaml frontmatter:\n"
            f"expected 'deck' as Str, got {None}\n"
        )

    else:
        raise TypeError(
            "\nError in reading the yaml frontmatter:\n"
            f"expected 'deck' as Str, got {type(deck)}\n"
            )
        
    


def get_tags(metadata: dict) -> list:
    """Wrapper around dict.get to extract tag list from file metadata."""

    tags = metadata.get("tags", list())

    # try to return a list of tags, raise an Exception in case of failure
    if isinstance(tags, list):
        return tags

    elif isinstance(tags, str):
        return [tags]

    else:
        raise TypeError(
            "\nError in reading the yaml frontmatter:\n"
            f"expected 'tags' as Str or List, got {type(tags)}\n"
            )


def scrape_images(line: str, filepath: str) -> list:
    """Function to scrape all the image names and paths from the provided lines.
    Returns a list of dictionary, with keys 'filename' and 'path'."""

    # compile the regex expression
    image_re = re.compile(precompiled["image"])
    images = []

    # scrape image names and paths from text
    for im in image_re.findall(line):

        # create image Path obj
        im_path = Path(im)

        # check the image path and make sure it exists
        if im_path.absolute().exists():
            im_path = im_path.absolute()
        else:
            # if the absolute path doesn't point to an object, try building it from the text file location
            file_dir = Path(filepath).parent.absolute()
            possible_path = file_dir/im_path
            if possible_path.exists():
                im_path = possible_path
            else:
                logger.warning(f"Unable to find absolute path for file {im_path}. Returning relative path instead")

        # append image information to list
        im_path = str(im_path)
        images.append({"filename": im, "path": im_path})

    return images


def format_images(text: str) -> str:
    """Function to format lines containing images, wrapping their references in HTML syntax.
    Returns a list of the formatted lines and a list of dictionaries containing the image information."""

    # compile the regex expression
    image_re = re.compile(precompiled["image"])

    # format lines
    for expr in image_re.findall(text):
        text = image_re.sub(f"<img src=\"{expr}\">", text, count=1)

    return text


def format_math(text: str) -> str:
    """Function to format lines containing math expressions, wrapping them in anki-mathjax HTML syntax."""

    # compile the regex expressions
    math_re = re.compile(precompiled["math"])
    math_block_re = re.compile(precompiled["math_block"])

    # format lines
    for expr in math_block_re.findall(text):
        text = math_block_re.sub(rf"<anki-mathjax block=true>{repr(expr)[1:-1]}</anki-mathjax>", text, count=1)

    for expr in math_re.findall(text):
        text = math_re.sub(rf"<anki-mathjax>{repr(expr)[1:-1]}</anki-mathjax>", text, count=1)

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
    (indexes): front, back, id, inline, modelName, is_card."""

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
            front = r.group(1).strip()
            is_card = True
        elif answer_re.search(line) is not None:
            if back is None:
                back = line.strip(">").strip()
            else:
                back += line.strip(">").strip()
        elif (r := id_re.search(line)) is not None:
            id = [int(group) for group in r.groups() if group is not None][0]
        elif empty_line_re.search(line) is not None:
            if front is not None and back is not None:
                return pd.Series([front, back, id, inline, model, is_card], index=index_names)

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

    # if the card is inline, adjust the sub so that subbing the id with the empty str doesn't ruin line ordering
    if series.inline is True:
        sub = sub + "\n"

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
        line = re.sub("\n", f"{sub}", line)
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
