def search_notes(db_manager, keyword):
    print(f"Searching for '{keyword}'...")
    all_notes = db_manager.get_all_notes()
    results = [note for note in all_notes if keyword.lower() in note['name'].lower()]
    return results