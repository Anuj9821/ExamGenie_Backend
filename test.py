from duckduckgo_search import DDGS

def get_duckduckgo_context(topic):
    ddgs = DDGS()
    results = ddgs.text(topic, max_results=15)
    if not results:
        return "No results found."
    snippets = [res['body'] for res in results if 'body' in res]
    return "\n".join(snippets)

# Example usage
topic = "regression analysis"
print(f"📌 Topic: {topic}")
print("🧠 Context:\n", get_duckduckgo_context(topic))
