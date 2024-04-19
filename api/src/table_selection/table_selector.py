import json
import openai
import time

from openai import OpenAI, APIConnectionError
from typing import List
from sentence_transformers import SentenceTransformer

from config import OPENAI_KEY
from table_selection.table import *
from utils.similarity_search import get_similar_tables
from utils.few_shot_examples import get_few_shot_example_messages
from utils.preprocessors.text import extract_text_from_markdown_triple_backticks

def _get_table_selection_message_with_descriptions(table_manager, table_names: List[str] = None):

    response_part = """
        {
            "explanation": "",
            "table": ""
        }
        """

    message = (
        f"""
        You are an expert data analyst. 
        You are given a question from a user, and a list of tables you are able to query. 
        Select the most relevant table that could contain the data to answer the user's question:

        ---------------------\n
        {table_manager.get_table_schemas(table_names)}
        ---------------------\n

        Your response should be in JSON format with:

            - "explanation": one to two sentence comment explaining why the chosen table is relevant goes here, double checking it exists in the list provided before.
            - "table": The name of the selected table, the most relevant one to answer the question.

        Response format:

        ```
        {response_part}
        ```

        """
    )

    return message


def _get_table_selection_messages() -> List[str]:
    """
    
    """
    default_messages = []
    default_messages.extend(get_few_shot_example_messages(mode = "table_selection"))
    return default_messages


def get_relevant_tables_from_database(natural_language_query, embedding_model = 'multi-qa-MiniLM-L6-cos-v1', content_limit = 1) -> List[str]:
    """
    Returns a list of the top k table names (matches the embedding vector of the NLQ with the stored vectors of each table)
    """
    model = SentenceTransformer(embedding_model) # 384
    vector = model.encode([natural_language_query])

    results = get_similar_tables(vector, content_limit=content_limit)

    return list(results)


def get_relevant_tables_from_lm(natural_language_query, table_manager, table_list = None, model = "gpt-4") -> List[str]:
    """
    Identify relevant tables for answering a natural language query via LM
    """
    max_attempts = 5
    attempts = 0

    content = _get_table_selection_message_with_descriptions(table_manager, table_list)

    messages = [{
        "role": "system",
        "content": content
    }]

    messages.append({
        "role": "user",
        "content": natural_language_query
    })

    client = OpenAI(api_key=OPENAI_KEY)
    
    while attempts < max_attempts:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
               # response_format={"type": "json_object"},
                )
        except APIConnectionError as e:
            print(f"OpenAI API request failed to connect: {e}")
        else:
            break
        attempts += 1
        time.sleep(1)

    output_text = response.choices[0].message.content
    print("\nChatGPT response:", output_text)
    tables_json_str = extract_text_from_markdown_triple_backticks(output_text)
    table_list = json.loads(tables_json_str).get("table")

    return table_list


def request_tables_to_lm_from_db(natural_language_query, table_manager, content_limit=3):
    """
    Extracts most similar tables from database using embeddings and similarity functions, and then lets the llm choose the most relevant one.
    """
    tables = get_relevant_tables_from_database(natural_language_query, content_limit = content_limit)
    gpt_selected_table_str = get_relevant_tables_from_lm(natural_language_query, table_manager, table_list = tables)

    gpt_selected_table = table_manager.get_table(gpt_selected_table_str)

    return gpt_selected_table