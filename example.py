from pathlib import Path
from ankicli import noteModule2


def main():
    directory = Path(r"./vault")

    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"Directory {directory} does not exist or is not a directory.")

    for file in directory.glob("*.md"):
        print(file)
        nset = noteModule2.NoteSet.from_file(file)

        nset.check_deck()
        nset.check_notes()
        nset.upload_new_notes()
        nset.update_existing_notes()
        nset.upload_media()
        nset.save_file()

if __name__ == "__main__":
    main()
