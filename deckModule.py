import requestModule
"""Module to handle deck-related requests, like deck creation, deletion, etc"""


@requestModule.ensure_connectivity
def deck_exists(name):
    """Low level function to check if a deck already exists for the current anki user"""
    deck_names = requestModule.request_action("deckNames")["result"]

    if name in deck_names:
        return True
    else:
        return False


@requestModule.ensure_connectivity
def get_deck_cards_n(name):
    """Low level function to retrieve the number of cards for a given deck"""

    if deck_exists(name):
        result = requestModule.request_action("getDeckStats", decks=[name])["result"]
        if len(result) != 1:
            raise Exception(f"Multiple decks found. Deck IDS: {result.keys()}")
        else:
            for i in result.values():
                n = i["total_in_deck"]
                return n
    else:
        print(f"Deck '{name}' does not exist.")
        return None


@requestModule.ensure_connectivity
def create_deck(name):
    """Function to create a new deck for the current anki user"""

    if deck_exists(name):
        print(f"Deck '{name}' already exists.")
        return None
    else:
        result = requestModule.request_action("createDeck", deck=name)["result"]

    if result is None:
        print("Deck creation unsuccessful.")
    else:
        print(f"Deck creation successful. Deck ID: {result}")


@requestModule.ensure_connectivity
def delete_deck(name, force=False):
    """Function to delete a deck for the current user"""

    if not deck_exists(name):
        print(f"Deck '{name}' does not exist.")
        return None

    cards_n = get_deck_cards_n(name)

    if cards_n != 0 and force is False:
        print(f"Deck '{name}' is not empty. To delete it, call this function with force=True")
    else:
        requestModule.request_action("deleteDecks", decks=[name], cardsToo=True)
