from fastapi import FastAPI, Depends, HTTPException, status,Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from typing import Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
import globals
import db
import os
import json

import db
import utils
from datetime import date, datetime
from html import escape
import shlex
import math


# Initialize app and configurations
globals.set_config_params()
logger, hldr_faust = globals.create_logs('DIA')
globals.startup()


app = FastAPI()

security = HTTPBasic()
if globals.secret_data.get('OPENAI_API_KEY'):
    os.environ["OPENAI_API_KEY"] = globals.secret_data['OPENAI_API_KEY']
# GOOGLE_API_KEY is optional — only set if present in secrets (not needed for Ollama/Gemma)
if globals.secret_data.get('GOOGLE_API_KEY'):
    os.environ["GOOGLE_API_KEY"] = globals.secret_data['GOOGLE_API_KEY']
vector_store = {}
embeddings={}

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    
    if credentials.username != globals.secret_data['restuser'] or credentials.password != globals.secret_data['restpwd']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class DynamicRequest(BaseModel):
    data: Dict[str, Any]
    agentid: str

def get_llm(agent_config):
    """Create an LLM instance based on provider config.

    Provider resolution order:
      1. agent_config['model_config']['provider']  (per-agent override in masters.sysconfig)
      2. globals.config['llm_provider']             (global default in config.json)
      3. 'openai'                                   (hardcoded fallback)

    Supported providers:
      - 'openai'  : ChatOpenAI  — uses OPENAI_API_KEY from secrets
      - 'ollama'  : ChatOllama  — uses llm_base_url from config.json (strips /v1 suffix)
      - 'google'  : ChatGoogleGenerativeAI — uses GOOGLE_API_KEY from secrets
    """
    model_config = agent_config['model_config']
    provider = model_config.get('provider', globals.config.get('llm_provider', 'openai'))
    params = model_config.get('params', {})

    if provider == 'openai':
        return ChatOpenAI(**params)

    elif provider == 'ollama':
        from langchain_ollama import ChatOllama
        ollama_params = dict(params)
        if 'base_url' not in ollama_params:
            # Our config uses llm_base_url with /v1 suffix (OpenAI-compat format).
            # ChatOllama uses Ollama's native API — strip /v1 before passing.
            raw_url = globals.config.get('llm_base_url', 'http://localhost:11434')
            ollama_params['base_url'] = raw_url.replace('/v1', '').rstrip('/')
        return ChatOllama(**ollama_params)

    elif provider == 'google':
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(**params)

    else:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Supported values: 'openai', 'ollama', 'google'"
        )

# Helper functions
def load_vector_store(agentid: str,embedding_model:str):
    global embeddings
    logger.debug(f"Loading vector store for Agent ID: {agentid}")
    if globals.config["provider"]=="openai":
        
        embeddings[agentid] = OpenAIEmbeddings()
    else:
        embeddings[agentid] = HuggingFaceEmbeddings(model_name=embedding_model)
    cfg =  globals.config['connections'][0]
    return PGVector(
        embeddings=embeddings[agentid],
        collection_name=agentid,
        connection=db.get_connection_str('agent'),
        use_jsonb=True,
        engine_args=cfg["params"]
    )

def get_agent_config(agentid: str):
    return next((agent for agent in globals.config["agents"] if  agent['agent']==agentid), None)

def validate_input_fields(data: Dict[str, Any], required_fields: list):
    
    for field in required_fields:
        val=utils.get_var(data,field)
        if val  is None:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

def validate_agent_config_and_vector_store(agentid: str):
    agent_config = get_agent_config(agentid)
    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent ID '{agentid}' not found in the configuration.")
    if ('vectorstore' in agent_config) and (agentid not in vector_store):
            raise HTTPException(status_code=404, detail=f"No vector store found for Agent ID '{agentid}'.")
    return agent_config

def initialize_vector_stores(agentname=None):
    for agent in globals.config['agents']:
        if 'vectorstore' in agent:
            if (agentname is None) or (agent['agent']==agentname):
                vector_store[agent['agent']] = load_vector_store(agent['agent'],agent['vectorstore']['embedding_model'])
    logger.debug("Vector stores initialized: %s", vector_store)    

initialize_vector_stores()




# Define prompt template and retrieve from config
def get_prompt_template(config):
    prompt_config = config.get("prompt_template", {})
    return PromptTemplate(
        input_variables=prompt_config.get("input", [
            "policy", "case_attributes", "policy_action", "policy_remarks", "similar_cases"
        ]),
        template=prompt_config.get("template", """
            You are an expert in fraud detection policies and case analysis. Below is the policy document:

            {policy}

            A new case has the following attributes:
            {case_attributes}

            Policy-based suggestion:
            Action: {policy_action}
            Remarks: {policy_remarks}

            From the vector similarity results, here are the most relevant historical cases:
            {similar_cases}

            Based on the policy suggestion and the historical cases, decide the most appropriate action and provide remarks.

            Output your response in the format:
            Action: <action>
            Remarks: <remarks>
            """)
    )

def get_similarities(agentid,agentconfig,data):
    if 'vectorstore' in agentconfig:
        query = ", ".join([f"{key}: {utils.get_var(data,key)}" for key in agentconfig['vectorstore']['data']])
        query_vector = embeddings[agentid].embed_query(query)

        documents = vector_store[agentid].similarity_search_by_vector(query_vector, k=agentconfig['vectorstore']['cnt_similarities'])

        #logger.debug(f"Similarities result:{results}")
        if not documents:
            raise HTTPException(status_code=404, detail="No similar cases found.")
        suggestions=[]

        for doc in documents:
            
            suggestion={}
            suggestion["docid"]=doc.id
            for field in agentconfig['vectorstore']['metadata']:
                logger.debug(f"{field}:metadata:{doc.metadata}")
                suggestion[field]= doc.metadata.get(field, "N/A") 
            suggestions.append(suggestion) 
        return suggestions
    else:
        return None

def get_chain_result(agentid,agent_config,agent_data):
    prompt = get_prompt_template(agent_config)
    inputs={}
    for field in agent_config['prompt_template']['input']:
        inputs[field['name']]=utils.get_var(agent_data,field['key'])
    # Initialize LLM and chain
    filled_prompt = prompt.format(**inputs) 
    llm = get_llm(agent_config)
    #chain = prompt | llm
    message_content =[{
        "type": "text",
        "text": filled_prompt
    }]
    # Check if 'data' block is provided in model_config
    if 'data' in agent_config['model_config']:
        # Clone the data config
        additional_content = dict(agent_config['model_config']['data'])

        # Fill in actual binary or base64 data
        additional_content["data"] = utils.get_var(agent_data, agent_config['model_config']['data_key'])

        # Append to message content
        message_content.append(additional_content)

    # Final message
    message = {
        "role": agent_config['model_config']['role'],
        "content": message_content
    }
    logger.debug(f'message:{message}')
    # Combine into a single query for the LLM
    response = llm.invoke([message])
    return response

def get_requisites(agentid,req_config,agent_data):
    switcher = {
            'DB':utils.dbdata,
            'ROCKS':utils.rocksdata,
            'API': utils.apidata,
            'REDIS':utils.redisdata,
            'MEM': utils.memdata           
        } 
    
    data_prep={}
    
    for datastore in req_config: ##TO Change to Datastore
        try:
            func = switcher.get((datastore['type']).upper(), lambda: 'Invalid Store type')      
            if ('section' in  datastore) : 
                if datastore['section'] not in data_prep:                    
                    data_prep[datastore['section']]={}
                data_prep[datastore['section']][datastore['name']]=func( agent_data,datastore)
            else:    
                data_prep[datastore['name']]=func( agent_data,datastore)
            logger.debug(f'get_requisites:{data_prep}')    
        except Exception as ex:  
            logger.error(f"{agentid}-get_prequisites:error while processing, : {datastore['name']}", exc_info=ex)
       
    return data_prep    

@app.post("/agent")
async def agent_ai(request: DynamicRequest,username: str = Depends(get_current_username)):
    agentid = request.agentid
    
    agent_config = validate_agent_config_and_vector_store(agentid)
    logger.debug(f'Loaded agent config:{agent_config}')
    agent_data={}
    agent_data['input_data']=request.data
    
    agent_data['prerequisites']=get_requisites(agentid,agent_config['prerequisites'],agent_data)
    logger.debug(f'After prerequisites:{agent_data}')
    if 'vectorstore' in agent_config:
        agent_data['similarities']=get_similarities(agentid,agent_config,agent_data)
        logger.debug(f'After similarities:{agent_data}')
        agent_data['postrequisites']=get_requisites(agentid,agent_config['postrequisites'],agent_data["similarities"])
        logger.debug(f'After postrequisites:{agent_data}')
    response=get_chain_result(agentid,agent_config,agent_data)
    logger.debug(response)
    if agent_config.get('response_type','json')=='json':
        json_response=json.loads(response.content)
    else: json_response =response    
    return json_response    


 
@app.post("/add_to_vectorstore")
async def add_to_vectorstore(request: DynamicRequest,username: str = Depends(get_current_username)):
    agentid = request.agentid

    data={}
    data['input_data']=request.data

    agent_config = validate_agent_config_and_vector_store(agentid)
    
    inputs = agent_config["vectorstore"]["data"]
    metadata_keys = [f'input_data.{key}' for key in agent_config["vectorstore"]["metadata"]]
    
    id_field = f'input_data.{agent_config["doctype"]}'
    
    validate_input_fields(data, inputs + metadata_keys + [id_field])
    logger.debug(data)
    # Prepare document for vector store
    page_content = ", ".join([f"{key}: {utils.get_var(data,key)}" for key in inputs])
    metadata = {key: utils.get_var(data,key) for key in metadata_keys}

    document = Document(page_content=page_content, metadata=metadata)
    #embeddings[agentid].embed_query(query)
    vector_store[agentid].add_documents([document], ids=[utils.get_var(data,id_field)])
    return {"message": "Case added successfully!"}

@app.post("/suggest_action")
async def suggest_action(request: DynamicRequest,username: str = Depends(get_current_username)):
    agentid = request.agentid
    data={}
    data['input_data']=request.data
    #data = request.data

    agent_config = validate_agent_config_and_vector_store(agentid)

    inputs = agent_config["input_data"]
    metadata_fields = [f'input_data.{key}' for key in agent_config["metadata"]]
   

    validate_input_fields(data, inputs)

    query = ", ".join([f"{key}: {utils.get_var(data,key)}" for key in inputs])
    query_vector = embeddings.embed_query(query)

    results = vector_store[agentid].similarity_search_by_vector(query_vector, k=3)

    if not results:
        raise HTTPException(status_code=404, detail="No similar cases found.")
    suggestions=[]
    for result in results:
        suggestion={}
        suggestion["context"]=result.page_content
        for field in metadata_fields:
            suggestion[field]= result.metadata.get(field, "N/A") 
        suggestions.append(suggestion)    

    return {"similar_cases": suggestions}

def get_policy_from_db(agent_id):
    
    query="SELECT policy_text FROM agents.policy_documents WHERE agent_id = :agentid ORDER BY created_at DESC LIMIT 1"
        
    result = db.get_data1(query,{'agentid':agent_id})
    
    if not result.empty:
        return result.iloc[0]["policy_text"]  # policy_text from the RealDictCursor
    else:
        raise ValueError(f"No policy found for agent_id: {agent_id}")
    
@app.post("/recommend_action")
async def recommend_action(request: DynamicRequest,username: str = Depends(get_current_username)):
    agentid = request.agentid
    data={}
    data['input_data']=request.data


    agent_config = validate_agent_config_and_vector_store(agentid)

    # Format case attributes using config inputs
    case_attributes = ", ".join([f"{key}: {utils.get_var(data,key)}" for key in agent_config["input_data"]])

    # Policy-based suggestion
    #policy_suggestion = policy_suggest_action(data)

    # Vector similarity suggestion
    query = case_attributes
    query_vector = embeddings.embed_query(query)
    results = vector_store[agentid].similarity_search_by_vector(query_vector, k=3)

    if  results:
        # Format similar cases
        similar_cases = "\n".join(
        [
            f"- ID: {result.metadata[agent_config['id']]}, " +
            ", ".join([f"{field}: {result.metadata[field]}" for field in agent_config["metadata"]]) +
            f", Context: {result.page_content}"
            for result in results
        ]
        )

    prompt = get_prompt_template(agent_config)
    policy = get_policy_from_db(agentid)
    # Initialize LLM and chain
    llm = get_llm(agent_config)
    chain = prompt | llm
    inputs = {
        "policy": policy,  # Assuming `policy_document` is loaded dynamically
        "case_attributes": case_attributes,
        "similar_cases": similar_cases
    }
    # Combine into a single query for the LLM
    response = chain.invoke(inputs)
    json_response=json.loads(response)
    return json_response

@app.post('/reloadconfig')
def reload_config(username: str = Depends(get_current_username),agentname: str = Query(default=None)):
    
    db.add_config('DIA',globals.config['appname'])
    initialize_vector_stores(agentname)
    return "Done"