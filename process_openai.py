import os
import json
import subprocess
from openai import OpenAI
from util import read_json, get_schema_and_table_list, execute_function_call, visualise

def process_query(query):
    if isinstance(query, list) and all(isinstance(item, dict) and 'role' in item and 'content' in item for item in query):
        return query
    else:
        return [{'role': 'user', 'content': query}]

def call_fn(client, query, model, tools, toolchoice=None):
    if toolchoice is None:
        response = client.chat.completions.create(
            model=model,
            messages=process_query(query),
            tools=tools,
            tool_choice='auto',
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=process_query(query),
            tools=tools,
            tool_choice={"type": "function", "function": {"name": toolchoice}},
        )
    return response

def main(query):
    dirname = os.getcwd()
    config_path = os.path.join(dirname, 'config')
    info = read_json(os.path.join(config_path, 'info.json'))

    GPT_MODEL = info.get('GPT_4')

    custom_functions = [
        {
            "type": "function",
            "function": {
                'name': 'extract_SQL',
                'description': 'Generate SQL query to answer a given question from attached SQLITE databases.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'The query that the user asked for to return information from attached SQLITE databases'
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                'name': 'visualise',
                'description': 'Perfect python code thats ready to run, of a visualisation of given data or a csv',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'code': {
                            'type': 'string',
                            'description': 'A perfect python function to do analysis as asked, comprehensive with all relevant import functions, ready to be run.'
                        }
                    }
                },
                "required": ["code"]
            }
        }
    ]

    client = OpenAI()

    response = call_fn(client, query, GPT_MODEL, custom_functions)

    # Debugging: Print the entire response object
    print("Response object:", response)

    # Extract the dataframe
    df = execute_function_call(response)
    
    # Visualize the dataframe
    if df is not None:
        chart = visualise(df)
        return chart
    else:
        print("Failed to extract dataframe")
        return None

if __name__ == '__main__':
    dirname = os.getcwd()
    config_path = os.path.join(dirname, 'config')
    subprocess.run(['python3', 'get_table_schema.py'])
    final_schema, tables = get_schema_and_table_list(config_path)
    query = f"""Extract dependency data for gene EP300, group them by OncotreeLineage and calculate averages. The schema is {final_schema} and {tables}.
    The databases are already attached as: 
    ATTACH DATABASE 'db/ProteinNetwork.db' AS ProteinNetwork
    ATTACH DATABASE 'db/DepMap.db' AS DepMap

    Ensure we use those names. You do not need to attach the DBs again. Make sure you use the right table names. You are writing a SQL query to answer the question from SQLITE."""
    
    result = main(query)
    print(result)