from __future__ import annotations
import copy
import logging
import re
import json
import requestModule
import modelModule
import deckModule
import parseModule
from dataclasses import dataclass, field
"""Module to handle note-related requests, like deck creation, deletion, etc"""


def write_to_error_log(notes: list, file="error_log.txt"):

    with open(file, "a") as f:

        f.writelines([f"\n{json.dumps(note.to_dict())}" for note in notes])


@dataclass
class Note:

    deckName: str
    modelName: str
    fields: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    id: int = field(default=None)
    inline: bool = field(default=False)

    def __post_init__(self):
        if not modelModule.model_exists(self.modelName):
            raise ValueError(f"Model {self.modelName} doesn't exist.")

        if not modelModule.check_model_fields(self.modelName, list(self.fields.keys())):
            raise ValueError(f"The provided fields ({self.fields.keys()}) are different from the ones specified"
                             f" for the {self.modelName} model.")

    @requestModule.ensure_connectivity
    def get_deck(self):
        result = requestModule.request_action("getDecks", cards=[self.id])["result"]
        return list(result)[0]

    @requestModule.ensure_connectivity
    def change_deck(self, deck_name=None):
        if deck_name is None:
            deck_name = self.deckName
        requestModule.request_action("changeDeck", cards=[self.id], deck=deck_name)

    @requestModule.ensure_connectivity
    def add_to_deck(self):

        if not deckModule.deck_exists(self.deckName):
            deckModule.create_deck(self.deckName)

        result = requestModule.request_action("addNote", note=self.to_dict())["result"]
        self.id = result

    @requestModule.ensure_connectivity
    def update(self):

        if self.get_deck() != self.deckName:
            self.change_deck()

        requestModule.request_action("updateNote", note=self.to_dict())

    def to_dict(self) -> dict:
        """Alternative to dataclasses.asdict (doesn't include inline field)."""

        d = {
            "deckName": self.deckName,
            "modelName": self.modelName,
            "fields": copy.deepcopy(self.fields),
            "tags": copy.deepcopy(self.tags),
            "id": self.id
        }

        return d

    @classmethod
    def create_from_dict(cls, note_dict: dict):
        dn = note_dict["deckName"]
        mn = note_dict.get("modelName", "Basic")
        tags = note_dict["tags"]
        inline = note_dict.get("inline", False)

        if "Front" in note_dict:
            f = {"Front": note_dict["Front"], "Back": note_dict["Back"]}
        else:
            try:
                f = {"Front": note_dict["fields"]["Front"]["value"],
                     "Back": note_dict["fields"]["Back"]["value"]}
            except TypeError:
                f = {"Front": note_dict["fields"]["Front"],
                     "Back": note_dict["fields"]["Back"]}

        if "id" in note_dict:
            note_id = note_dict["id"]
        else:
            note_id = note_dict["noteId"]

        return cls(dn, mn, f, tags, note_id, inline)


@dataclass
class NoteSet:

    deckName: str = field(default=None)
    commonTags: list = field(default=None)

    allNotes: list[Note] = field(default_factory=list)
    existingNotes: list[Note] = field(default_factory=list)
    newNotes: list[Note] = field(default_factory=list)
    errorNotes: list[Note] = field(default_factory=list)

    notes_last_lines: list[int] = field(default_factory=list)
    new_notes_last_lines: list[int] = field(default_factory=list)
    file_lines: list[str] = field(default_factory=list)
    file_properties: list[str] = field(default_factory=list)
    file_text: list[str] = field(default_factory=list)
    file_name: str = field(default=None)
    images: list[dict] = field(default_factory=list)

    # AUTOMATIC METHODS ================================================================================================

    @classmethod
    def create_noteset_from_file(cls, file) -> NoteSet:
        """Method to instantiate a noteset object from a text file"""

        # instantiate class object
        nset = cls()
        nset.file_name = file

        # retrieve properties and lines from the file
        nset.file_lines = parseModule.get_lines(file)
        properties, properties_indexes = parseModule.get_properties(nset.file_lines)

        # assign deck and tags to the correct attributes
        nset.deckName = parseModule.get_deck(properties)
        nset.commonTags = parseModule.get_tags(properties)

        # separate file properties and text using the properties indexes
        nset.file_properties = nset.file_lines[properties_indexes[0]:properties_indexes[1]]
        nset.file_text = nset.file_lines[properties_indexes[1]:]

        # format images and math expressions
        nset.file_text = parseModule.format_math(nset.file_text)
        nset.file_text, nset.images = parseModule.format_images(nset.file_text)

        # iterate all the cards through the card generator
        for card, index in parseModule.card_gen(nset.file_text, nset.deckName, nset.commonTags):
            nset.allNotes.append(Note.create_from_dict(card))
            nset.notes_last_lines.append(index)

        # sort in the various lists
        nset.sort_notes()
        nset.sort_last_lines()
        # returns the fully instantiated object
        return nset

    @requestModule.ensure_connectivity
    def update_new_notes(self) -> None:
        """Method to update new notes, running all the tests etc."""

        # # finding errors and repairing notes =========================================================================

        # retrieves notes that cannot be added to the deck for some reason
        error_notes, non_error_notes = self.find_error_notes(self.newNotes)
        error_notes = self.repair_duplicated_notes(error_notes)

        self.newNotes = non_error_notes

        # if some notes returned an error, move them to the self.errorNotes list and remove them from self.newNotes
        if len(error_notes) != 0:
            logging.error("\nSome of the new notes could not be added to the deck."
                          "\nWriting error log...")
            self.errorNotes.extend(error_notes)
            write_to_error_log(error_notes)

        # # adding new notes to the deck ===============================================================================
        # might be worth to move this part in its own method and just call it from here

        # add notes and return note ids
        notes_ids = self.add_notes(self.newNotes)
        inline_counter = -1

        # sort self.notes_last_lines (as we might have removed some notes from newNotes)
        self.sort_last_lines()

        # save the ids
        for i, note in enumerate(self.newNotes):

            # assign ids
            note.id = notes_ids[i]

            # update inline counter if the note is inline
            inline_counter = inline_counter + 1 if note.inline else inline_counter

            # move the last line of the current note down for as many lines as the note number to account for the newly
            # added line (as each newly created card adds a single line for its id)
            self.new_notes_last_lines[i] += i - inline_counter
            # save the id alongside the note
            parseModule.insert_card_id(self.file_text, self.new_notes_last_lines[i], notes_ids[i], note.inline)

    @requestModule.ensure_connectivity
    def update_existing_notes(self) -> None:
        """Method to update all existing notes, running tests etc."""

        # # take care of deleted notes =================================================================================

        # retrieve notes that have been deleted and try to repair them
        deleted_notes, self.existingNotes = self.find_deleted_notes(self.existingNotes)
        error_notes = self.repair_deleted_notes(deleted_notes)

        # if some notes returned an error, move them to the self.errorNotes list and remove them from self.newNotes
        if len(error_notes) != 0:
            logging.error("\nSome of the deleted notes could not be added to the deck."
                          "\nWriting error log...")
            self.errorNotes.extend(error_notes)
            write_to_error_log(error_notes)

        # # take care of notes in the wrong deck =======================================================================

        # retrieve notes that are in the wrong deck and try to repair them
        wrong_deck_notes = self.find_wrong_deck_notes(self.existingNotes)
        self.repair_wrong_deck_notes(wrong_deck_notes)

        # # take care of notes that need to be updated =================================================================

        # retrieve notes that need to be updated
        updatable_notes = self.find_updatable_notes(self.existingNotes)

        # update all notes
        for note in updatable_notes:
            note.update()

    @staticmethod
    @requestModule.ensure_connectivity
    def find_error_notes(notes_to_check: list[Note]) -> tuple[list[Note], list[Note]]:
        """Method to check that all the notes in newNotes can be added to the deck.
        Returns a tuple of lists: one of the notes that can be added, and one for the notes for which an error was
        returned."""

        logging.info("\nLooking for error notes")

        # create a list of note dictionaries
        notes = [note.to_dict() for note in notes_to_check]
        # query the server for potential errors
        errors = requestModule.request_action("canAddNotesWithErrorDetail", notes=notes)["result"]

        # initialize empty lists
        error_notes = []
        non_error_notes = []

        # for every note in the list, check if the server returned an error and add it to the right list
        for note, error in zip(notes_to_check, errors):

            if error["canAdd"] is False:
                note.id = error["error"]
                error_notes.append(note)
            elif error["canAdd"] is True:
                non_error_notes.append(note)

        return error_notes, non_error_notes

    @staticmethod
    def filter_duplicate_notes(error_notes: list[Note]) -> tuple[list[Note], list[Note]]:
        """Method that filters the notes in error_notes and returns the duplicate ones.
        Returns a tuple with the updated error_notes and duplicate_notes list."""

        logging.info("\nLooking for duplicate notes")

        # simply iter in the error_notes list and find the notes for which the error message contains "duplicate"
        duplicate_notes = [note for note in error_notes if re.search("duplicate", note.id)]
        error_notes = [note for note in error_notes if note not in duplicate_notes]

        return duplicate_notes, error_notes

    @staticmethod
    def find_duplicate_ids(duplicate_notes: list[Note]) -> list[int]:
        """Method that queries the server to retrieve duplicate notes ids."""

        logging.info("\nRetrieving duplicate notes ids")

        # retrieve the front field of the notes, which will be used as the querz
        front = [note.fields["Front"] for note in duplicate_notes]

        # initialize note ids list
        note_ids = []

        # query the server for the duplicate notes ids
        # will raise an Exception if not all the notes could be found
        # exception handling in outer scope?
        for query in front:
            result = requestModule.request_action("findNotes", query=query)["result"]
            note_ids.append(result[0])

        return note_ids

    @requestModule.ensure_connectivity
    def repair_duplicated_notes(self, error_notes: list[Note]) -> list[Note]:
        """Method that tries to repair broken notes (e.g. duplicate notes that don't have an id in the origin file)."""

        logging.info("\nRepairing duplicate notes")

        # retrieve duplicate notes and ids from the error notes
        duplicate_notes, error_notes = self.filter_duplicate_notes(error_notes)
        duplicate_ids = self.find_duplicate_ids(duplicate_notes)

        # set inline counter to -1 to add ids to the right lines
        inline_counter = -1

        # for every duplicate note, save its id in the Note obj and add it to the file lines
        for i, note in enumerate(duplicate_notes):
            note.id = duplicate_ids[i]

            # update inline counter if the note is inline
            inline_counter = inline_counter + 1 if note.inline else inline_counter

            # move the last line of the current note down for as many lines as the duplicate note number to account for
            # the newly added lines
            index = self.newNotes.index(note)
            self.new_notes_last_lines[index] += i - inline_counter

            # save the id
            parseModule.insert_card_id(self.file_text, self.new_notes_last_lines[index], note.id, note.inline)

        return error_notes

    @requestModule.ensure_connectivity
    def find_deleted_notes(self, notes_to_check: list[Note]) -> tuple[list[Note], list[Note]]:
        """Method that checks that all the notes in existingNotes actually exist in the server."""

        # gathers all ids of the existing notes
        note_ids = [note.id for note in notes_to_check]

        # queries the database to get a list of dictionary, where each dict represents a note
        queried_notes = requestModule.request_action("notesInfo", notes=note_ids)["result"]

        # adds the deckName field to every dictionary returned by the query
        for dic in queried_notes:
            dic.setdefault("deckName", self.deckName)

        # creates the Note objects from the databases, and setting the element value to None for notes that don't exist
        queried_notes = [Note.create_from_dict(obj) if len(obj) != 1 else None for obj in queried_notes]

        # initialize lists
        deleted_notes = []
        remaining_notes = []

        # finds all notes that could not be found in any deck and moves them to the deletedNotes list, while adding the
        # notes that differ from the queried ones (and as such need to be updated) to the upNotes list
        for note, qnote in zip(self.existingNotes, queried_notes):
            if qnote is None:
                deleted_notes.append(note)
            else:
                remaining_notes.append(note)

        return deleted_notes, remaining_notes

    @requestModule.ensure_connectivity
    def repair_deleted_notes(self, deleted_notes: list[Note]) -> list[Note]:
        """Method that tries to repair deleted notes i.e. notes that have an id that does not exist on the server.
        Returns a list of the notes that could not be repaired."""

        logging.info("\nRepairing deleted notes")

        # check if all the deleted notes can be added to the deck
        error_notes, deleted_notes = self.find_error_notes(deleted_notes)
        duplicate_notes, error_notes = self.filter_duplicate_notes(error_notes)

        # initialize list and then fill it with the duplicate note ids (queried from the server)
        duplicate_ids = []
        if len(duplicate_notes) != 0:
            duplicate_ids = self.find_duplicate_ids(duplicate_notes)

        # filter deleted notes to only keep the non-duplicate and non-error ones
        deleted_ids = self.add_notes(deleted_notes)

        # creates the lists to iter on
        notes = duplicate_notes + deleted_notes
        note_ids = duplicate_ids + deleted_ids

        # for every note (both duplicated and deleted) change the id in the file lines and then in the note obj
        for note_id, note in zip(note_ids, notes):
            parseModule.sub_card_id(self.file_text, note.id, note_id)
            note.id = note_id

        return error_notes

    @requestModule.ensure_connectivity
    def find_wrong_deck_notes(self, notes_to_check: list[Note]) -> list[Note]:
        """Method to retrieve a list of cards that are in the wrong deck."""

        # retrieve note ids
        note_ids = [note.id for note in notes_to_check]
        # queries the database to get a dictionary: {deck: [note ids]}
        decks_dict = requestModule.request_action("getDecks", cards=note_ids)["result"]

        # initialize note list
        wrong_deck_notes = []

        # for every key in the dictionary that is different from the one defined in the noteSet deckName attribute,
        # add the items of its list to the wrongDeck list
        for key in list(decks_dict):
            if key != self.deckName:
                wrong_deck_notes.extend([note for note in notes_to_check if note.id in decks_dict[key]])

        return wrong_deck_notes

    @requestModule.ensure_connectivity
    def repair_wrong_deck_notes(self, wrong_deck_notes: list[Note]) -> None:
        """Method to move notes in the right deck."""

        # export notes as dictionaries
        notes = [note.to_dict() for note in wrong_deck_notes]

        # change notes' deck
        requestModule.request_action("changeDeck", cards=notes, deck=self.deckName)

    @requestModule.ensure_connectivity
    def find_updatable_notes(self, notes_to_check: list[Note]) -> list[Note]:
        """Method to find out which of the provided notes should be updated."""

        # gathers all ids of the existing notes
        note_ids = [note.id for note in notes_to_check]

        # queries the database to get a list of dictionary, where each dict represents a note
        queried_notes = requestModule.request_action("notesInfo", notes=note_ids)["result"]

        # adds the deckName field to every dictionary returned by the query
        for dic in queried_notes:
            dic.setdefault("deckName", self.deckName)

        # creates the Note objects from the databases, and setting the element value to None for notes that don't exist
        queried_notes = [Note.create_from_dict(obj) if len(obj) != 1 else None for obj in queried_notes]

        # initialize empty list
        updatable_notes = []
        # finds all notes that could not be found in any deck and moves them to the deletedNotes list, while adding the
        # notes that differ from the queried ones (and as such need to be updated) to the upNotes list
        for note, qnote in zip(notes_to_check, queried_notes):

            if note != qnote:
                updatable_notes.append(note)

        return updatable_notes

    @requestModule.ensure_connectivity
    def upload_media(self) -> None:
        """Method to upload media to anki"""

        # upload every image to the media folder
        for im in self.images:
            requestModule.request_action("storeMediaFile", filename=im["filename"], path=im["path"])

    def save_lines(self) -> None:
        """Method to save the updated lines to the file."""

        # check that the file name is available in the NoteSet attributes
        if not self.file_name:
            raise Exception("Method only available when the NoteSet object has been created from a file using the "
                            "NoteSet.create_from_file class method")

        # update file lines
        self.file_lines = self.file_properties + self.file_text

        # overwrite the file with the new lines
        # this should not be very dangerous as we're only inserting new lines and not deleting any, but might need some
        # more thinking before the stable version
        with (open(self.file_name, mode="w", encoding="utf-8")) as f:
            f.writelines(self.file_lines)

    def sort_notes(self) -> None:
        """Method to divide already existing notes from new notes"""
        non_error_notes = [note for note in self.allNotes if note not in self.errorNotes]
        self.existingNotes = [note for note in non_error_notes if note.id is not None]
        self.newNotes = [note for note in non_error_notes if note.id is None]

    def sort_last_lines(self) -> None:
        """Method to purge newly created notes' lines from last lines"""
        self.new_notes_last_lines = [self.notes_last_lines[i]
                                     for i, j in enumerate(self.allNotes)
                                     if j in self.newNotes]

    @staticmethod
    @requestModule.ensure_connectivity
    def add_notes(note_list: list[Note]) -> list[int]:
        """Method to add notes in bulk."""

        # add notes
        result = requestModule.request_action("addNotes", notes=[note.to_dict() for note in note_list])["result"]

        # return note ids
        return result

    @requestModule.ensure_connectivity
    def check_deck(self) -> None:
        """Method to check that the NoteSet deck exists in the server and to create it if it does not."""

        if not deckModule.deck_exists(self.deckName):
            deckModule.create_deck(self.deckName)

    # MANUAL METHODS ===================================================================================================
    # def _add_note(self, note: Note) -> None:
    #
    #     self.allNotes.append(note)
    #
    #     if note.id is None:
    #         self.newNotes.append(note)
    #     else:
    #         self.existingNotes.append(note)
    #
    #
    #
    # @requestModule.ensure_connectivity
    # def upload_all_notes(self):
    #     for note in self.existingNotes:
    #         note.update()
    #     for note in self.newNotes:
    #         note.add_to_deck()
    #
    #     self.sort_notes()
