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
        f = {"Front": note_dict["Front"], "Back": note_dict["Back"]}
        tags = note_dict["tags"]
        id = note_dict["id"]

        return cls(dn, mn, f, tags, id)




@dataclass
class NoteSet:

    deckName: str = field(default=None)
    commonTags: list = field(default=None)
    allNotes: list[Note] = field(default_factory=list)
    existingNotes: list[Note] = field(default_factory=list)
    newNotes: list[Note] = field(default_factory=list)

    @requestModule.ensure_connectivity
    def add_note(self, note: Note) -> None:

        self.allNotes.append(note)

        if note.id is None:
            self.newNotes.append(note)
        else:
            self.existingNotes.append(note)

    def create_notes_from_file(self, file):

        lines = parseModule.get_lines(file)
        properties = parseModule.get_properties(lines)
        self.deckName = parseModule.get_deck(properties)
        self.commonTags = parseModule.get_tags(properties)

        cards = parseModule.get_cards(lines)
        for card in cards:
            card.setdefault("deckName", self.deckName)
            card.setdefault("tags", self.commonTags)

        self.allNotes = [Note.create_from_dict(card) for card in cards]
        self.sort_notes()

    def sort_notes(self):
        self.existingNotes = [note for note in self.allNotes if note.id is not None]
        self.newNotes = [note for note in self.allNotes if note.id is None]

    @requestModule.ensure_connectivity
    def upload_all_notes(self):
        for note in self.existingNotes:
            note.update()
        for note in self.newNotes:
            note.add_to_deck()

        self.sort_notes()




    # @requestModule.ensure_connectivity
    # def upload_set(self):
    #     pass
