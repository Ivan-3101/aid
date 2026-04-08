import os
import globals
from sqlalchemy import create_engine, MetaData, Table, select, exc,text
from sqlalchemy.orm import  Session
from sqlalchemy.sql import func
from sqlalchemy.ext.automap import automap_base

import pandas as pd
from datetime import datetime, date,timedelta


def get_secret(secret_path):
    
    secrets_data = {}
    try:
        # Iterate over files in the secret path
        
        for filename in os.listdir(secret_path):
            
            filepath = os.path.join(secret_path, filename)
            if os.path.isfile(filepath):
                with open(filepath, 'r') as file:
                    # Read the contents of each file and store it in the secrets_data dictionary
                    secrets_data[filename] = file.read()
                    
    except Exception as e:
        globals.logger.error("Error reading secrets from path: ",exc_info=e)
    
    return secrets_data

def get_connection_str(type):
    conn_str = globals.secret_data[type].strip() + globals.config['appname']  

    
    return conn_str

def get_db_url() -> str:
    return "postgresql+psycopg://{0}:{1}@{2}:{3}/{4}?options=-c%20search_path=agents&application_name=={5}".format(globals.secret_data['DBUSER'],globals.secret_data['DBPWD'],globals.config['DB']['DBHOST'], globals.config['DB']['port'], globals.config['DB']['DBNAME'], globals.config['appname'])

def get_jdbc_url() -> str:
    return "jdbc:postgresql://{0}:{1}/{2}?ApplicationName={3}".format(globals.config['DB']['DBHOST'], globals.config['DB']['port'], globals.config['DB']['DBNAME'], globals.config['appname'])


def load_session():
    
    """Load db session which will be used 
    Args: None      
    Returns:
        engine,transactions schema mapper,analytics schema mapper   
    """

   
    cfg =  globals.config['connections'][0]
    conn_str=get_connection_str(cfg['name'])  
    engine = create_engine(conn_str,**cfg['params'])

    return engine

def get_data1(query:str,params:dict):
    
    logger=globals.logger
    
    with Session(globals.engine) as session:
        try:

            result = pd.read_sql_query(text(query), session.bind,params=params)
        except Exception as pe:
            logger.error(f'Not configured  correctly:, query: {query}, params:{params}', exc_info=pe)
            result=None
    return result    

def add_config(appname:str,env:str):
    
    logger=globals.logger
    
    with Session(globals.engine) as session:
        try:
            
            result = pd.read_sql_query(text("Select cfgname,config from masters.sysconfig where application= :appname and env= :env "), session.bind,params={'appname':appname,'env':env}).to_records()
            #if not result.empty:
            
            for row in result:
                globals.config[row['cfgname']] = row['config']
            
        except Exception as pe:
            logger.error(f'Not configured  correctly:, {appname}', exc_info=pe)
            
    return None      


