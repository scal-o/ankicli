import copy
import requestModule
import modelModule
import deckModule
import parseModule
from dataclasses import dataclass, field
"""Module to handle note-related requests, like deck creation, deletion, etc"""


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
    def change_deck(self, deckName=None):
        if deckName is None:
            deckName = self.deckName
        requestModule.request_action("changeDeck", cards=[self.id], deck=deckName)

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
            f = {"Front": note_dict["fields"]["Front"]["value"],
                 "Back": note_dict["fields"]["Back"]["value"]}

        if "id" in note_dict:
            id = note_dict["id"]
        else:
            id = note_dict["noteId"]

        return cls(dn, mn, f, tags, id, inline)


@dataclass
class NoteSet:

    deckName: str = field(default=None)
    commonTags: list = field(default=None)
    allNotes: list[Note] = field(default_factory=list)
    existingNotes: list[Note] = field(default_factory=list)
    newNotes: list[Note] = field(default_factory=list)
    updatableNotes: list[Note] = field(default_factory=list)
    deletedNotes: list[Note] = field(default_factory=list)
    wrongDeckNotes: list[Note] = field(default_factory=list)
    errorNotes: list[Note] = field(default_factory=list)
    notes_last_lines: list[int] = field(default_factory=list)
    file_lines: list[str] = field(default_factory=list)

    # AUTOMATIC METHODS ================================================================================================

    @classmethod
    def create_noteset_from_file(cls, file):
        """Method to instantiate a noteset object from a text file"""

        # instantiate class object
        nset = cls()

        # retrieve properties and lines from the file
        nset.file_lines = parseModule.get_lines(file)
        properties = parseModule.get_properties(nset.file_lines)

        # assign deck and tags to the correct attributes
        nset.deckName = parseModule.get_deck(properties)
        nset.commonTags = parseModule.get_tags(properties)

        # iterate all the cards through the card generator
        for card, index in parseModule.card_gen(nset.file_lines, nset.deckName, nset.commonTags):
            nset.allNotes.append(Note.create_from_dict(card))
            nset.notes_last_lines.append(index)

        # sort in the various lists
        nset.sort_notes()
        nset.sort_last_lines()
        # returns the fully instantiated object
        return nset

    @requestModule.ensure_connectivity
    def bulk_upload(self):
        """Method to upload all notes in bulk, reducing the overhead from calling each note's add_to_deck method"""

        # # deck check =================================================================================================
        # check that the deck exists, and if not, create it
        if not deckModule.deck_exists(self.deckName):
            deckModule.create_deck(self.deckName)

        # # add new notes ==============================================================================================
        # add notes in bulk and return note ids and errors
        result = self.add_notes_return_errors_and_ids(self.newNotes)
        inline_counter = -1
        # save the ids or errors of the notes to the file
        for i in range(0, len(self.newNotes)):
            self.newNotes[i].id = result[i]

            # update inline counter if the note is inline
            inline = self.newNotes[i].inline
            if inline:
                inline_counter += 1

            # move the last line of the current note down for as many lines as the note number to account for the newly
            # added line (as each newly created card adds a single line for its id)
            self.notes_last_lines[i] += i - inline_counter
            # save the id alongside the note
            parseModule.insert_card_id(self.file_lines, self.notes_last_lines[i], result[i], inline)

        # # existing notes =============================================================================================
        # change deck to already existing notes from a different deck
        self.bulk_change_deck()

        # update already existing notes (no bulk method implemented in ankiConnect yet)
        for note in self.updatableNotes:
            note.update()

        # adds notes from the deletedNotes list in bulk
        result = self.add_notes_return_errors_and_ids(self.deletedNotes)

        # save the ids or errors of the notes to the file
        for i in range(0, len(self.deletedNotes)):
            parseModule.sub_card_id(self.file_lines, self.deletedNotes[i].id, result[i])
            self.deletedNotes[i].id = result[i]

        # # sort notes =================================================================================================
        self.sort_notes()
        self.sort_last_lines()

        # # save file ==================================================================================================
        # overwrites the file with the new lines (with the ids after every card)
        # this should not be very dangerous as we're only inserting new lines and not deleting any, but might need some
        # more thinking before the stable version
        with (open("prova.md", mode="w", encoding="utf-8")) as f:
            f.writelines(self.file_lines)

    def sort_notes(self):
        """Method to divide already existing notes from new notes"""
        self.existingNotes = [note for note in self.allNotes if note.id is not None]
        self.newNotes = [note for note in self.allNotes if note.id is None]

        self.sort_existing_notes()

    def sort_last_lines(self) -> None:
        """Method to purge newly created notes' lines from last lines"""
        self.notes_last_lines = [self.notes_last_lines[i] for i, j in enumerate(self.allNotes) if j in self.newNotes]

    @requestModule.ensure_connectivity
    def sort_existing_notes(self) -> None:
        """Function that sorts existing notes, creating:
        - the list of all notes that need to be updated (updatableNotes)
        - the list of all notes that have been deleted and need to be created again (deletedNotes)
        - the list of all notes that were found in the wrong deck
         Works by running a notesInfo/getDecks query on the http server and comparing each note from existingNotes with
         the queried notes."""

        # # update errorNotes ==========================================================================================

        # puts the notes with errors in their ids in a separate list
        indexes = []
        for i, note in enumerate(self.existingNotes):
            if not isinstance(note.id, int):
                self.errorNotes.append(note)
                indexes.append(i)

        for i in reversed(indexes):
            self.existingNotes.pop(i)

        # print a warning message if the errorNotes list is not empty
        if len(self.errorNotes) != 0:
            print("Some notes were not read properly, or returned an error while being added to the deck.")
            print(self.errorNotes)

        # # update updatableNotes and deletedNotes =====================================================================
        # resets the notes lists
        self.updatableNotes = []
        self.deletedNotes = []

        # gathers all ids of the existing notes
        ids = [note.id for note in self.existingNotes]

        # queries the database to get a list of dictionary, where each dict represents a note
        queried_notes = requestModule.request_action("notesInfo", notes=ids)["result"]

        # adds the deckName field to every dictionary returned by the query
        for dic in queried_notes:
            dic.setdefault("deckName", self.deckName)

        # creates the Note objects from the databases, and setting the element value to None for notes that don't exist
        queried_notes = [Note.create_from_dict(obj) if len(obj) != 1 else None for obj in queried_notes]

        # finds all notes that could not be found in any deck and moves them to the deletedNotes list, while adding the
        # notes that differ from the queried ones (and as such need to be updated) to the upNotes list
        indexes = []
        for index, zipped in enumerate(zip(self.existingNotes, queried_notes)):

            note, qnote = zipped

            if qnote is None:
                self.deletedNotes.append(note)
                indexes.append(index)
            elif note != qnote:
                self.updatableNotes.append(note)

        for i in reversed(indexes):
            self.existingNotes.pop(i)
            queried_notes.pop(i)
            ids.pop(i)  # remove id from ids to reuse same list later

        # print a warning message if the deletedNotes list is not empty
        if len(self.deletedNotes) != 0:
            print("Some notes could not be found in the current deck. "
                  "They have been added again and their ids have been updated.")
            print(self.deletedNotes)

        # # update wrongDeckNotes ======================================================================================
        # resets note list
        self.wrongDeckNotes = []

        # queries the database to get a dictionary: {deck: [note ids]}
        decks_dict = requestModule.request_action("getDecks", cards=ids)["result"]

        # for every key in the dictionary that is different from the one defined in the noteSet deckName attribute,
        # add the items of its list to the wrongDeck list
        for key in list(decks_dict):
            if key != self.deckName:
                self.wrongDeckNotes.extend(decks_dict[key])

        # print a warning message if the wrongDeckNotes list is not empty
        if len(self.wrongDeckNotes) != 0:
            print("Some notes were found in a different deck. They have been moved to the current deck.")
            print(self.wrongDeckNotes)

    @requestModule.ensure_connectivity
    def bulk_change_deck(self) -> None:
        """Method to change deck to all the notes that need to do so."""
        requestModule.request_action("changeDeck", cards=self.wrongDeckNotes, deck=self.deckName)

    @requestModule.ensure_connectivity
    def add_notes_return_errors_and_ids(self, note_list: list[Note]) -> list:
        """Method to request note addition and return new notes ids and errors when present"""

        # add notes in bulk
        result = requestModule.request_action("addNotes", notes=[note.to_dict() for note in note_list])["result"]

        # check that all the notes could be created successfully
        # if some notes could not be added, retrieve the error messages and insert the errors in the result list
        if None in result:
            print("Some notes could not be added to the collection.")
            notes = [note.to_dict() for note in note_list]
            errors = requestModule.request_action("canAddNotesWithErrorDetail", notes=notes)["result"]
            for i in range(len(result)):
                if result[i] is None:
                    result[i] = errors[i]["error"]

        # return the list of ids and errors
        return result

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
