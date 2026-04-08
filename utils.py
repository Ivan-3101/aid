import json
import globals
from sqlalchemy import create_engine,text,bindparam
from sqlalchemy.orm import  Session
import pandas as pd

def memdata(observed:dict,store:dict):
    globals.logger.debug(f'mem:{store}')
    
    jsonquery=store['jsonquery']

    if not bool(jsonquery):
        return globals.refdata[store['object']]
    else:
        return  None #jsonLogic(jsonquery, globals.refdata[store['object']], operations=DRONA)

def execute_query_with_params(session, query, param_dict):
    processed_query = query
    bind_params = []

    for key, value in param_dict.items():
        bind_param_key = key.replace('.', '_')
        processed_query = processed_query.replace(f':{key}', f':{bind_param_key}')

        # If the value is a list/tuple, use expanding=True
        if isinstance(value, (list, tuple)):
            bind_params.append(bindparam(bind_param_key, expanding=True))
        else:
            bind_params.append(bindparam(bind_param_key))

    stmt = text(processed_query).bindparams(*bind_params)
    result = session.execute(stmt, {key.replace('.', '_'): value for key, value in param_dict.items()})
    return result

def execute_query(session, query, param_dict):
    processed_query = query


    for key, value in param_dict.items():
        
        processed_query = processed_query.replace(f':{key}', f'{value}')
        

    result = session.execute(text(processed_query))
    return result

def build_query(agent_data,store_params):
    where_clause=""
    for key in store_params:
        opr= key.get('operator','')
        data=get_var(agent_data,key['valueField'])
        if key.get('type','') == 'list':
            result = ','.join(f'"{item}"' for item in data)

            where_clause=where_clause+" "+ opr+" " + key['name'] +" in (" +result+")"
        else:    
            where_clause=where_clause+" "+ opr+" " + key['name'] +"='" +data+"'"
       
def dbdata(agent_data:dict,store:dict):
    globals.logger.debug(f'db:{store}')
    globals.logger.debug(f'agent_data:{agent_data}')
    with Session(globals.dbs[store['conn']]['engine']) as session:
            
        column_values={}
         
        for key in store['params']:

            column_values[key['name']]=get_var(agent_data,key['valueField'])
        query = store['query']

        result = execute_query_with_params(session, query, column_values)
        if store.get("noofrows","one")=="one":
            row = result.fetchone()
            if row:
                return row[0]
        else:
            rows = result.fetchall()
            keys = result.keys()
            result_list = [dict(zip(keys, row)) for row in rows]
            return result_list
    return None


      
def rocksdata(observed:dict,store:dict):
    globals.logger.debug(f'rocks:{store}')
    
    key_raw_value=get_var(observed,store['key'])
    if key_raw_value is not None:
        if store['keytype']=='int':
            key_value=str(int(key_raw_value))
        else:
            key_value=key_raw_value
        
        v = globals.rocksdb_db[store['object']].get(key_value.encode())
        if v:
            return json.loads(v)
        else:
            return None
    else:
        return None    
    

def redisdata(observed:dict,store:dict):
    globals.logger.debug(f'redisdata:{store}')
    values={}
    for key in store['key']:
        val=get_var(observed,key['val'])
        if val is None:
            values[key['name']]= None
        else:    
            if key['keytype']=='int':
                values[key['name']]=str(int(val))           
            else:
                values[key['name']]=val
    #print(values)    
    #print(store['redis_key'])
    redis_key=store['redis_key'].format(**values)
    v=globals.rs[store['object']].get(redis_key)
    if v:
        return json.loads(v)
    else:
        return None
     

def apidata(observed:dict,store:dict):
    globals.logger.debug(f'api:{store}')    
    return 'x'

def get_var(data, var_name, not_found=None):
    """Gets variable value from data dictionary, supports dot notation and '*' for lists."""
    try:
        parts = str(var_name).split('.')
        for i, key in enumerate(parts):
            if key == '*':
                if not isinstance(data, list):
                    return not_found
                rest = '.'.join(parts[i + 1:])
                return [get_var(item, rest, not_found) for item in data]
            try:
                data = data[key]
            except TypeError:
                data = data[int(key)]
    except (KeyError, TypeError, ValueError):
        return not_found
    else:
        return data

def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f'{parent_key}{sep}{k}' if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)