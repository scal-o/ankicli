import requestModule
import modelModule
import deckModule
import parseModule
from dataclasses import dataclass, field, asdict
"""Module to handle note-related requests, like deck creation, deletion, etc"""


@dataclass
class Note:

    deckName: str
    modelName: str
    fields: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    id: int = field(default=None)

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

        result = requestModule.request_action("addNote", note=asdict(self))["result"]
        self.id = result

    @requestModule.ensure_connectivity
    def update(self):

        if self.get_deck() != self.deckName:
            self.change_deck()

        requestModule.request_action("updateNote", note=asdict(self))

    @classmethod
    def create_from_dict(cls, note_dict: dict):
        dn = note_dict["deckName"]
        mn = note_dict.get("modelName", "Basic")
        tags = note_dict["tags"]

        if "Front" in note_dict:
            f = {"Front": note_dict["Front"], "Back": note_dict["Back"]}
        else:
            f = {"Front": note_dict["fields"]["Front"]["value"],
                 "Back": note_dict["fields"]["Back"]["value"]}

        if "id" in note_dict:
            id = note_dict["id"]
        else:
            id = note_dict["noteId"]

        return cls(dn, mn, f, tags, id)


@dataclass
class NoteSet:

    deckName: str = field(default=None)
    commonTags: list = field(default=None)
    allNotes: list[Note] = field(default_factory=list)
    existingNotes: list[Note] = field(default_factory=list)
    newNotes: list[Note] = field(default_factory=list)
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
        nset.notes_last_lines = [nset.notes_last_lines[i] for i, j in enumerate(nset.allNotes) if j in nset.newNotes]

        # returns the fully instantiated object
        return nset

    @requestModule.ensure_connectivity
    def bulk_upload(self):
        """Method to upload all notes in bulk, reducing the overhead from calling each note's add_to_deck method"""

        # check that the deck exists, and if not, create it
        if not deckModule.deck_exists(self.deckName):
            deckModule.create_deck(self.deckName)

        # add notes in bulk
        result = requestModule.request_action("addNotes", notes=[asdict(note) for note in self.newNotes])["result"]

        # check that all the notes could be created successfully
        # if some notes could not be added, retrieve the error messages and insert the errors in the result list
        if None in result:
            print("Some notes could not be added to the collection.")
            notes = [asdict(note) for note in self.newNotes]
            errors = requestModule.request_action("canAddNotesWithErrorDetail", notes=notes)["result"]
            for i in range(len(result)):
                if result[i] is None:
                    result[i] = errors[i]["error"]

        # save the ids or errors of the notes to the file
        for i in range(0, len(self.newNotes)):
            self.newNotes[i].id = result[i]
            # move the last line of the current note down for as many lines as the note number to account for the newly
            # added line (as each newly created card adds a single line for its id)
            self.notes_last_lines[i] += i
            # save the id alongside the note
            parseModule.insert_card_id(self.file_lines, self.notes_last_lines[i], result[i])

        # change deck to already existing notes from a different deck
        self.bulk_change_deck()

        # update already existing notes (no bulk method implemented in ankiConnect yet)
        for note in self.updatableNotes:
            note.update()

        # sort the notes
        self.sort_notes()

        # overwrites the file with the new lines (with the ids after every card)
        # this should not be very dangerous as we're only inserting new lines and not deleting any, but might need some
        # more thinking before the stable version
        with (open("prova.md", mode="w", encoding="utf-8")) as f:
            f.writelines(self.file_lines)

    def sort_notes(self):
        """Method to divide already existing notes from new notes"""
        self.existingNotes = [note for note in self.allNotes if note.id is not None]
        self.newNotes = [note for note in self.allNotes if note.id is None]

    @property
    def updatableNotes(self) -> list[Note]:
        """Property that returns a list of all the notes that need to be updated. Runs a notesInfo query on the http
        server and compares each note from existingNots with the queried notes"""

        # gathers all ids of the existing notes
        ids = [note.id for note in self.existingNotes]

        # queries the database to get a list of dictionary, where each dict represents a note
        queried_notes = requestModule.request_action("notesInfo", notes=ids)["result"]
        for dic in queried_notes:
            dic.setdefault("deckName", self.deckName)

        # creates the Note objects from the databases
        queried_notes = [Note.create_from_dict(obj) for obj in queried_notes]

        # compares the already existing notes with the ones created from the query and compares them, adding the ones
        # that differ to the list
        upNotes = [note for note, qnote in zip(self.existingNotes, queried_notes) if note != qnote]

        # returns the list of notes that need to be updated
        return upNotes

    @property
    def wrongDeckNotes(self) -> list[int]:
        """Property that returns a list of the ids of the notes that need to change deck.
        Runs a getDecks query on the http server and returns ids of all the notes in decks different from the one
        defined in the noteSet deckName attribute"""

        # gathers all ids of the existing notes
        ids = [note.id for note in self.existingNotes]

        # queries the database to get a dictionary: {deck: [note ids]}
        decks_dict = requestModule.request_action("getDecks", cards=ids)["result"]

        # instantiates an empty list
        wrongDeck  = []

        # for every key in the dictionary that is different from the one defined in the noteSet deckName attribute,
        # add the items of its list to the wrongDeck list
        for key in list(decks_dict):
            if key != self.deckName:
                wrongDeck.extend(decks_dict[key])

        # return the list of the ids of the notes that need to change deck
        return wrongDeck

    def bulk_change_deck(self) -> None:
        """Method to change deck to all the notes that need to do so."""
        requestModule.request_action("changeDeck", cards=self.wrongDeckNotes, deck=self.deckName)



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
