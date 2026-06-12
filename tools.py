import wikipedia

def get_live_wiki_details(query):
    try:
        wikipedia.set_lang("en")

        page = wikipedia.page(
            query,
            auto_suggest=False
        )

        return page.summary[:8000]

    except Exception as e:
        return f"WIKI_ERROR: {str(e)}"