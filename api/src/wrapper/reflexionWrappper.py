import json

from operator import itemgetter
from os import getenv
from langchain.globals import set_debug, set_verbose
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.llms import Ollama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence, RunnablePassthrough, RunnableLambda, RunnableParallel, chain
from langchain_openai import OpenAI
from table_selection.table import TableManager
from wrapper.json_check import json_iterator, set_form_json
from wrapper.logsHandlerCallback import logsHandler

from config import TABLES_PATH, OPENAI_KEY


# TABLES_PATH = getenv('TABLES_PATH')
OLLAMA_URL = 'https://caleuche-ollama.datawheel.us'
CONFIG_FILE_NAME = 'wrapper_datausa.json'
OPENAI = OPENAI_KEY

######### Models

model_ = OpenAI(
    model_name="gpt-3.5-turbo-instruct",
    temperature=0,
    openai_api_key=OPENAI
    )

model = Ollama(
    base_url= OLLAMA_URL,
    model= "llama2:7b-chat-q8_0",
    temperature= 0,
  ).with_config(
    seed= 123,
    run_name= 'basic_llama', 
  )

model_adv = Ollama(
    base_url= OLLAMA_URL,
    model= 'mixtral:8x7b-instruct-v0.1-q4_K_M',#'gemma:7b-instruct-q4_K_M',//
    system= '',
    temperature= 0,
).with_config(
    seed= 123,
    run_name= 'advance_mixtral',
)


############# Aux func
@chain
def stream_acc(info):
    """
    Prevent LLMs to stream (stutter) within a langchain chain. Use after the LLM.
    """
    print('In stream acc: {}'.format(info))
    return info

############# Prompts

#####  LLM Question

question_sys_prompt = """
You are a grammar expert analyzing questions in chats. All output must be in valid JSON format. 
Don't add explanation beyond the JSON.
"""

question_prompt = PromptTemplate.from_template(
"""
In the following Chat history, classify if the latest [User] input is:
- a new question made by the user, or 
- a complementary information for a previous question, or 
- not a question

If the input is classified as 'complementary information', summarize the question.

Answer using following output format. All answer must contain all the four fields (history, reasoning, type and question).
Here are some examples:

{{
"history": "[User]: Which country exported most copper;[AI]: Which year?;[User]:2022[.]",
"reasoning":"User initially asked which country exported the most copper, then AI asked in which year, then user complemented with year 2022",
"type": "complementary information" 
"question": "Which country exported most copper in 2022",
}}

{{
"history": "[User]: Which country exported most copper in 2022?;[AI]:Chile;[User]:What are the top five exporting countries for cars in terms of value?;[.]",
"reasoning":"The lastest question is What are the top five exporting countries for cars in terms of value? which is not related to previous questions",
"type": "new question" 
"question": "What are the top five exporting countries for cars in terms of value?",
}}

{{
"history": "[User]: Hi. how are you?[.]",
"reasoning":"The user greet",
"type": "not a question" 
"question": "User said hi",
}}

here is a chat history: {chathistory}
""")

alt_question_prompt = PromptTemplate.from_template(
"""
You are a grammar expert analyzing questions in chats. All output must be in valid JSON format. 
Don't add explanation beyond the JSON.

In the following Chat history, classify if the latest [User] input is:

- a new question made by the user, or 
- a complementary information for a previous question, or 
- not a question

If the input is classified as 'complementary information', summarize the question.
Answer using following output format. 
All answer must contain all the four fields: 
"history" withthe chat history, 
"reasoning" with your analysis, 
"type": with the classification categoty
"question": with a synthesis of the user's question

Here are some examples:

{{
"history": "[User]: Which country exported most copper;[AI]: Which year?;[User]:2022[.]",
"reasoning":"User initially asked which country exported the most copper, then AI asked in which year, then user complemented with year 2022",
"type": "complementary information" 
"question": "Which country exported most copper in 2022",
}}

{{
"history": "[User]: Which country exported most copper in 2022?;[AI]:Chile;[User]:What are the top five exporting countries for cars in terms of value?;[.]",
"reasoning":"The lastest question is What are the top five exporting countries for cars in terms of value? which is not related to previous questions",
"type": "new question" 
"question": "What are the top five exporting countries for cars in terms of value?",
}}

{{
"history": "[User]: Hi. how are you?[.]",
"reasoning":"The user greet",
"type": "not a question" 
"question": "User said hi",
}}

here is a chat history: {chathistory}
""")

##### LLM validation

validation_sys_prompt = """
You are linguistic expert used to analyze questions and complete forms precisely. All output must be in valid JSON format. 
Don't add explanations beyond the JSON.
"""
validation_prompt = PromptTemplate.from_template(
"""
Complete the form based on the question input. User only the explicit information contained in the question.
If no information is available in the question, left the field blank or the current value.
If the question contains information that is already filled in the form, replace it with que question information.
Answer in JSON format as shown in the following examples:

{{
"question":"Which country export the most copper?",
"explanation":"question mentions a exporter, a product, but does not mention a year. 
Then year is left blank and product and flow filled with corresponding values.
User wants the most, then sort is set to 'desc' for descending and limit is set to '1'",
"form_json":{{
    "base_url": "https://oec.world/api/olap-proxy/data.jsonrecords?",
    "cube": "trade_i_baci_a_96",
    "dimensions": {{
        "Year": [2023],
        "HS Product": ["copper"],
        "Hierarchy:Geography": [
            {{
                "Exporter": ["all"]
            }},
            {{
                "Importer": []
            }}
        ],
        "Unit": ["place_holder"]
    }},
    "measures": [
        "Trade Value",
        "Quantity"
    ],
    "limit": "1",
    "sort": "desc",
    "locale": "en"
}},
}}

{{
"question":"How much coffee did Colombia exported to US?",
"explanation":"question mentions a exporter geography, importer geography, a product, but does not mention a year. 
Then year is left as it is and product and exportenr and imported filled with corresponding values.
User wants to know how much, then sort is set to 'all' for descending and limit is set to 'all'",
"form_json":{{
    "base_url": "https://oec.world/api/olap-proxy/data.jsonrecords?",
    "cube": "trade_i_baci_a_96",
    "dimensions": {{
        "Year": [2023],
        "HS Product": ["coffee"],
        "Hierarchy:Geography": [
            {{
                "Exporter": ["Colombia"]
            }},
            {{
                "Importer": ["US"]
            }}
        ],
        "Unit": ["place_holder"]
    }},
    "measures": [
        "Trade Value",
        "Quantity"
    ],
    "limit": "all",
    "sort": "desc",
    "locale": "en"
}},
}}

{{
"question":"How much coffee did Colombia exported to US?",
"explanation":"question mentions a exporter geography, importer geography, a product, but does not mention a year. 
Then year is left as it is and product and exportenr and imported filled with corresponding values.
User wants to know how much, then sort is set to 'all' for descending and limit is set to 'all'",
"form_json":{{
    "base_url": "https://oec.world/api/olap-proxy/data.jsonrecords?",
    "cube": "trade_i_baci_a_96",
    "dimensions": {{
        "Year": [2023],
        "HS Product": ["coffee"],
        "Hierarchy:Geography": [
            {{
                "Exporter": ["Colombia"]
            }},
            {{
                "Importer": ["US"]
            }}
        ],
        "Unit": ["place_holder"]
    }},
    "measures": [
        "Trade Value",
        "Quantity"
    ],
    "limit": "all",
    "sort": "desc",
    "locale": "en"
}},
}}



Here is the form: {form_json}
Here is the question: {question}
"""
)

alt_validation_prompt = PromptTemplate.from_template(
"""
Complete the form based on the question input. User only the explicit information contained in the question.
If no information is available in the question, left the field blank or the current value.
If the question contains information that is already filled in the form, replace it with que question information.
Answer in JSON format as shown in the following examples:

{{
"question":"Which country export the most copper?",
"explanation":"question mention a flow, a product, but does not mention a time. Then time is left blank and product and flow filled with corresponding values",
"form_json":{{
    "base_url": "https://oec.world/api/olap-proxy/data.jsonrecords?",
    "cube": "trade_i_baci_a_96",
    "dimensions": {{
        "Year": [2023],
        "HS Product": ["copper"],
        "Hierarchy:Geography": [
            {{
                "Exporter": ["all"]
            }},
            {{
                "Importer": []
            }}
        ],
        "Unit": []
    }},
    "measures": [
        "Trade Value",
        "Quantity"
    ],
    "limit": "",
    "sort": "",
    "locale": ""
}},
}}


Here is the form: {form_json}
Here is the question: {question}
"""
)

# CHAINs

question_chain = question_prompt\
    .pipe(model.bind(system=question_sys_prompt, format='json'))\
    .pipe(stream_acc)\
    .pipe(JsonOutputParser())\
    .with_fallbacks([
        alt_question_prompt\
        .pipe(model_adv.bind(system=question_sys_prompt, format='json'))\
        .pipe(stream_acc)\
        .pipe(JsonOutputParser)
        ])


valid_chain = validation_prompt\
    .pipe(model.bind(system = validation_sys_prompt, format='json'))\
    .pipe(JsonOutputParser())\
    .with_fallbacks(
        [alt_validation_prompt\
            .pipe(model_adv.bind(
                system = validation_sys_prompt, 
                format= 'json'))\
            .pipe(JsonOutputParser())])

########## ROUTING LOGIC

@chain
def route_question(info):

    print('In route_question: ', info)
    form_json = info['form_json']
    action = info['action']

    if action['type'] == 'not a question':
        return {'question': lambda x: action['question'] } | PromptTemplate.from_template("Answer politely: {question}").pipe(model)
    
    elif action['type'] =='new question':
        form_json = set_form_json(action['question'])
        if form_json:
            return {'form_json': lambda x: form_json, 'question': lambda x: action['question']} | valid_chain
        else:
            return "I'm sorry, but OEC does not have data regarding your question, please try something different"
    
    elif action['type'] == 'complementary information':
        print('complement!!!!!!!!!!!!!')
        return {'form_json': lambda x: form_json, 'question': lambda x: action['question']} | valid_chain
    #case type no api call needed


@chain
def route_answer(info):
    print('In route_answer: ', info )
    handleAPIBuilder = info['input']['handleAPIBuilder']
    process = info['process']

    # if answer is not json is not a question
    if type(process) == str:
        yield json.dumps({'content': process})
    
    else:
        form_json = process['form_json']
        missing = json_iterator(form_json)

        # TODO: Debugg missing result
        table_manager = TableManager(TABLES_PATH)
        table = table_manager.get_table(form_json['cube'])
        if missing:
            request_info = 'Please, specify the following '
            for m in missing:
                if ':' in m[1]:
                    dimension = m[1].split(':')[-1]
                    
                else:
                    dimension = m[1]

                options = table.get_drilldown_members(dimension)
                request_info += '{}, such as {}:'.format(dimension, options)

            yield json.dumps({'content': request_info, 'form_json': form_json })


        else:
            yield json.dumps({'content': "Good question, let's check the data..."})
            #response = handleAPIBuilder(form_json, step= 'get_api_params_from_lm')
            response = handleAPIBuilder(form_json['measures'])
            yield json.dumps({'content': response, 'form_json': form_json})


################ Build Chain

main_chain = RunnableSequence(
    {
        'input': RunnablePassthrough(),
        'process': (
                {
                    'form_json': itemgetter("form_json"),
                    'action': question_chain  
                } | route_question 
            )
    } | route_answer,
)

############# Export function

def wrapperCall(history, form_json, handleAPIBuilder, logger=[] ):
    """
    Stream main_chain answers
    """
    for answer in main_chain.stream({
        'chathistory': ';'.join([f"{' [AI]' if m['user'] == False else ' [User]'}:{m['text']}"
                            for m in history]) + '[.]',
        'form_json': form_json, 
        'handleAPIBuilder': handleAPIBuilder
    }, config = {'callbacks':[logsHandler(logger, print_logs = True, print_starts=False)]}
    ):
        yield answer
  

if __name__ == "__main__":
    wrapperCall(
        [{'user':False, 'text':'hi, how can I help you'},
         {'user':True, 'text':'Which country export the most copper?'}],
         form_json={},
         handleAPIBuilder=lambda x: x,
         )
