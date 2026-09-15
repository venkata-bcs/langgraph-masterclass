from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# State: every field the nodes below read from or write to.
class SentenceMetrics(TypedDict):
    sentence: str
    uppercase_words_count: int
    lowercase_words_count: int
    first_word: str
    last_word: str


# Node 1: count how many words are fully UPPERCASE.
def count_uppercase_words(state: SentenceMetrics) -> dict:
    words = state["sentence"].split()
    uppercase_count = sum(1 for word in words if word.isupper())
    return {"uppercase_words_count": uppercase_count}


# Node 2: count how many words are fully lowercase.
def count_lowercase_words(state: SentenceMetrics) -> dict:
    words = state["sentence"].split()
    lowercase_count = sum(1 for word in words if word.islower())
    return {"lowercase_words_count": lowercase_count}


# Node 3: pull out the first word of the sentence.
def find_first_word(state: SentenceMetrics) -> dict:
    words = state["sentence"].split()
    return {"first_word": words[0]}


# Node 4: pull out the last word of the sentence.
def find_last_word(state: SentenceMetrics) -> dict:
    words = state["sentence"].split()
    return {"last_word": words[-1]}


# Graph: four single-purpose nodes, wired one after the other.
builder = StateGraph(SentenceMetrics)
builder.add_node("count_uppercase_words", count_uppercase_words)
builder.add_node("count_lowercase_words", count_lowercase_words)
builder.add_node("find_first_word", find_first_word)
builder.add_node("find_last_word", find_last_word)

builder.add_edge(START, "count_uppercase_words")
builder.add_edge("count_uppercase_words", "count_lowercase_words")
builder.add_edge("count_lowercase_words", "find_first_word")
builder.add_edge("find_first_word", "find_last_word")
builder.add_edge("find_last_word", END)

graph = builder.compile()

# Invoke: run the graph on a sample sentence and print each computed metric.
result = graph.invoke(
    {
        "sentence": "LangGraph makes STATE explicit and EASY to follow",
        "uppercase_words_count": 0,
        "lowercase_words_count": 0,
        "first_word": "",
        "last_word": "",
    }
)

print(f"Sentence: {result['sentence']!r}")
print(f"Uppercase words: {result['uppercase_words_count']}")
print(f"Lowercase words: {result['lowercase_words_count']}")
print(f"First word: {result['first_word']}")
print(f"Last word: {result['last_word']}")
