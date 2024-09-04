import parseModule
import pandas as pd
from dataclasses import dataclass, field


@dataclass
class NoteSet:

    # file info (if any)
    file_path: str = field(default=None)

    @classmethod
    def from_file(cls, path: str):
        """Method to instantiate a NoteSet object from a text file"""

        # create class instance
        nset = cls()

        # save file path info
        nset.file_path = path

        # retrieve file lines and properties
        lines = parseModule.get_lines(path)
        properties, lines = parseModule.extract_properties(lines)

        # assign deckName and common tags as found in the yaml frontmatter (properties)
        nset.deckName = parseModule.get_deck(properties)
        nset.tags = parseModule.get_tags(properties)

        # group file lines and create pandas.Series and pandas.DataFrame
        grouped_lines = parseModule.group_lines(lines)
        grouped_lines = pd.Series(grouped_lines)
        grouped_lines = pd.DataFrame(grouped_lines, columns=["text"])

        # create and fill pandas.DataFrame with the card information
        df = grouped_lines.text.apply(parseModule.parse_card)
        df = pd.concat([grouped_lines, df], axis=1)

        # add properties to the DataFrame
        properties = pd.Series([properties])
        properties = pd.DataFrame(properties, columns=["text"])
        tmp_prop = properties.text.apply(parseModule.parse_card, return_empty=True)
        properties = pd.concat([properties, tmp_prop], axis=1)

        df = pd.concat([properties, df])

        # scrape images from file lines
        fr_im = df.front.apply(parseModule.scrape_images)
        bk_im = df.back.apply(parseModule.scrape_images)
        images = fr_im + bk_im
        images = [im for im_list in images for im in im_list]
        nset.media = images

        # format front and back of cards
        df[["front", "back"]] = df[["front", "back"]].map(parseModule.format_images)
        df[["front", "back"]] = df[["front", "back"]].map(parseModule.format_math)

        df[["front", "back"]] = df[["front", "back"]].map(parseModule.format_images)
        df[["front", "back"]] = df[["front", "back"]].map(parseModule.format_math)

        # # save cards df
        nset.df = df

        # return instantiated NoteSet
        return nset
