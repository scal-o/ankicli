import re
import copy
"""Module to handle parsing of text files"""


def get_lines(path):
    with open(path, mode="r", encoding="utf-8") as f:
        lines = list(f)
    return lines


def get_properties(lines: list, properties_re="---") -> list:
    """Function that retrieves all the lines that make up the yaml properties frontmatter"""

    # compiles the regex expression before using it
    properties_re = re.compile(f"{properties_re}")

    properties = [i for i, j in enumerate(lines) if properties_re.search(j) is not None]
    properties = [j.strip() for i, j in enumerate(lines) if i in range(properties[0], properties[1])]

    return properties


def get_deck(properties, deck_re="cards-deck") -> str:

    # compile the regex expression before using it
    deck_re = re.compile(rf"{deck_re}: ([\w:\s]+)")

    # extract the deck from the yaml frontmatter
    deck = [deck_re.search(line)[1] for line in properties if deck_re.search(line) is not None][0]

    return deck


def get_tags(properties) -> list:

    # compile the regex expression before using it
    tags_re = re.compile(r"^- ([\w/]+)")

    # extract the tags from the yaml frontmatter
    tags = [tags_re.search(line)[1].replace("/", "::") for line in properties if tags_re.search(line) is not None]

    return tags


def get_cards(lines) -> list[dict]:

    question_re = re.compile(r"^>\[!question]-?\s*(.+)(#card)")
    answer_re = re.compile(r"^>")
    id_re = re.compile(r"<!--ID: (\d+)-->")
    empty_line_re = re.compile(r"(\s+)?\n")

    card_list = []
    std_dict = {"Front": None, "Back": None, "id": None}

    card_dict = copy.deepcopy(std_dict)

    for line in lines:
        if question_re.search(line) is not None:
            card_dict["Front"] = question_re.search(line).group(1)
        elif answer_re.search(line) is not None:
            if card_dict["Back"] is None:
                card_dict["Back"] = line.strip(">")
            else:
                card_dict["Back"] += line.strip(">")
        elif id_re.search(line) is not None:
            card_dict["id"] = id_re.search(line).group(1)
        elif empty_line_re.search(line) is not None:
            if card_dict["Front"] is not None and card_dict["Back"] is not None:
                card_dict["Back"] = card_dict["Back"].replace("\n", "<br />")
                card_list.append(card_dict)
                card_dict = copy.deepcopy(std_dict)

    return card_list
