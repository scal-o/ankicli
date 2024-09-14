import sys
import deckModule
import parseModule
import pandas as pd
import numpy as np
import logging
from requestModule import request_action

# set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

debug_handler = logging.StreamHandler(stream=sys.stdout)
debug_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(name)s::%(levelname)s - %(message)s')
debug_handler.setFormatter(formatter)

logger.addHandler(debug_handler)


class NoteSet:

    def __init__(self):
        self.deckName = None
        self.tags = None
        self.file_path = None
        self.media = None
        self.df = None

    @classmethod
    def from_file(cls, path: str):
        """Method to instantiate a NoteSet object from a text file"""

        logger.info(f"Instantiating NoteSet from file: {path}\n")

        # create class instance
        nset = cls()

        # save file path info
        nset.file_path = path

        # retrieve file lines and properties
        logger.debug("Reading file lines\n")
        lines = parseModule.get_lines(path)
        properties, lines = parseModule.extract_properties(lines)

        # assign deckName and common tags as found in the yaml frontmatter (properties)
        logger.debug("Parsing deck and tags info from file yaml frontmatter\n")
        strip_props = [line.strip() for line in properties]

        nset.deckName = parseModule.get_deck(strip_props)
        nset.tags = parseModule.get_tags(strip_props)

        # group file lines and create pandas.Series and pandas.DataFrame
        grouped_lines = parseModule.group_lines(lines)
        grouped_lines = pd.Series(grouped_lines)
        grouped_lines = pd.DataFrame(grouped_lines, columns=["text"])

        # create and fill pandas.DataFrame with the card information
        logger.debug("Parsing cards from file lines\n")
        df = grouped_lines.text.apply(parseModule.parse_card)
        df = pd.concat([grouped_lines, df], axis=1)

        # add properties to the DataFrame
        properties = pd.Series([properties])
        properties = pd.DataFrame(properties, columns=["text"])
        tmp_prop = properties.text.apply(parseModule.parse_card, return_empty=True)
        properties = pd.concat([properties, tmp_prop], axis=1)

        df = pd.concat([properties, df], ignore_index=True)

        # scrape images from file lines
        logger.debug("Scraping images from file lines\n")
        fr_im = df.front.apply(parseModule.scrape_images)
        bk_im = df.back.apply(parseModule.scrape_images)
        images = fr_im + bk_im
        images = [im for im_list in images for im in im_list]
        nset.media = images

        # format front and back of cards
        logger.debug("Formatting front and back text\n")
        df[["front", "back"]] = df[["front", "back"]].map(parseModule.format_images)
        df[["front", "back"]] = df[["front", "back"]].map(parseModule.format_math)

        df[["front", "back"]] = df[["front", "back"]].map(parseModule.format_images)
        df[["front", "back"]] = df[["front", "back"]].map(parseModule.format_math)

        # create field column
        logger.debug("Creating fields column\n")
        df.loc[df["is_card"] == True, "fields"] = df.apply(lambda x: {"Front": x.front, "Back": x.back}, axis=1)

        # add tags and deck info to cards
        logger.debug("Adding tags and deck info\n")
        df["tags"] = np.empty((len(df.index), 0)).tolist()
        df.tags.apply(lambda x: x.extend(nset.tags))
        df["deckName"] = nset.deckName

        # # save cards df
        nset.df = df

        # return instantiated NoteSet
        logger.info("NoteSet instantiated\n")
        return nset

    def check_deck(self) -> None:
        """Method to check that the NoteSet deck exists in the server and create it if it does not."""

        logger.debug("Checking deck\n")
        if not deckModule.deck_exists(self.deckName):
            deckModule.create_deck(self.deckName)

    def repair_errors(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Method to find and repair possible errors that may arise when uploading cards to Anki."""

        logger.info("Finding and repairing errors\n")

        # copy original dataframe
        df = self.df.copy()

        # find out which notes may produce an error
        e_df = self.find_error_notes(df)

        # repair any duplicated notes
        dup_df = self.repair_duplicate_notes(e_df)

        # update repaired notes in the df
        df.update(dup_df)

        # drop repaired notes from the error df
        # kinda complex to do an anti-join tbh
        e_df.drop(e_df.index[e_df.index.isin(dup_df.index)], inplace=True)
        e_df = e_df.loc[~e_df.index.isin(dup_df.index)]

        return df, e_df

    @staticmethod
    def find_error_notes(df: pd.DataFrame) -> pd.DataFrame:
        """Method to check that all the new notes can be added to the deck."""

        logger.info("Looking for error notes\n")

        # filter dataframe to only keep card rows that don't have an id
        logger.debug("Creating anki query\n")
        e_df = df.loc[(df["is_card"] == True) & (df["id"].isna())].copy()

        # create query for the anki server
        e_ddf = e_df[["deckName", "modelName", "fields", "tags", "id"]]
        e_list = e_ddf.to_dict(orient="index")
        e_list = list(e_list.values())

        # launch queries and gather results
        logger.debug("Querying anki for possible errors in the cards\n")
        e_list = request_action("canAddNotesWithErrorDetail", notes=e_list)["result"]

        logger.debug("Extracting error cards\n")
        e_df["error"] = [el.get("error") for el in e_list]
        e_df.dropna(subset=["error"], inplace=True)

        return e_df

    @staticmethod
    def repair_duplicate_notes(e_df):
        """Method to repair eventual duplicate notes"""

        logger.info("Repairing duplicate notes\n")

        # filter error notes keeping the duplicate ones
        logger.debug("Filtering duplicate notes from other errors\n")
        dup_df = e_df.loc[e_df["error"] == "cannot create note because it is a duplicate"].copy()

        # return the empty dataframe if no duplicate notes were found
        if len(dup_df.index) == 0:
            return dup_df

        # gather front of the cards and use them as queries to retrieve card ids from anki
        logger.debug("Creating anki query\n")
        dup_front = dup_df["front"].to_list()

        # launch query and gather results
        logger.debug("Querying anki for the missing ids\n")
        dup_ids = [request_action("findNotes", query=el)["result"][0] for el in dup_front]

        # insert card id in the id column and add it/sub it in the text column
        logger.debug("Inserting ids into the cards' text")
        dup_df["id"] = dup_ids
        dup_df["text"] = dup_df.apply(parseModule.insert_card_id, axis=1)

        # return the dataframe with the repaired cards
        return dup_df.drop(["error"], axis=1)
