import logging
import logging.config
import sys
from logging.handlers import TimedRotatingFileHandler
import configparser	
import socket
import json
import pandas as pd

import redis
from redis import Redis
from redis.cluster import RedisCluster

from sqlalchemy import create_engine,true,text
from sqlalchemy.orm import  Session
from datetime import datetime
import db
import os

from typing import Dict, Any,Optional

config=None
task_status={}
logger=None
secret_data={}
engine=None
refdbs={}
dbs={}
def create_logs(name:str):
    global logger
    global config
    logging.config.dictConfig(config['logs'])
    logger = logging.getLogger(name)
    hdlr_faust = logging.getLogger(name).handlers
    return logger,hdlr_faust

def set_config_params():
    global config
    with open('config.json') as config_file:
        config = json.load(config_file)

def set_connections():
    global dbs,config
    
    for conn in config['connections']  : 
        connectionstring=db.get_connection_str(conn['name'])      
        conn['engine'] = create_engine(connectionstring,**conn['params'])
        dbs[conn['name']]=conn



def load_redis():
    global rs,config
    for db in config['redis']  : 
        logger.debug(f'redis:{db}')  
        cluster_mode=db.get('cluster', True)
        if cluster_mode:
            rs[db['name']] = RedisCluster(host=db['redishost'], port=int(db['redisport']),   password=db['redispwd'])
        else:
            rs[db['name']] = Redis(host=db['redishost'], port=int(db['redisport']))
    #   

def startup():
    global logger,config,secret_data,engine
    from sqlalchemy import create_engine, text

    secret_data = db.get_secret(config['path'])
    logger.debug(f'secrets:{secret_data}')
    engine =db.load_session()
    
    db.add_config('DIA',config['appname'])
    set_connections()
    logger.info("Loaded DB connections")
    load_redis()
    logger.info("Connected to redis ")
    logger.debug(config)

