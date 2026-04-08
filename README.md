[
  {
    "agent": "caseagentv1",
    "model_config": {
      "params": {
        "temperature": 0
      },
      "role": "user"
    },
    "doctype": "RuleSpecificL1Action",
    "input_data": [
      "RuleSpecificL1Action",
      "RuleID",
      "CaseID",
      "BatchDate",
      "itenantid",
      "iaccountid",
      "icustomerid"
    ],
    "vectorstore": {
      "embedding_model": "sentence-transformers/all-mpnet-base-v2",
      "data": [
        "prerequisites.AccountMaster",
        "prerequisites.MonthlyProfile"
      ],
      "filter": [
        "RuleID",
        "RuleSpecificL1Action"
      ],
      "metadata": [
        "RuleSpecificL1Action",
        "ruleid",
        "caseid",
        "batchdate",
        "itenantid"
      ],
      "cnt_similarities": 2
    },
    "prerequisites": [
      {
        "conn": "txndb",
        "name": "MonthlyProfile",
        "type": "DB",
        "query": "WITH flattened_data AS ( select am.*, jt.path, jt.value from (SELECT * FROM profiles.account_monthly where itenantid=:itenantid and iaccountid=:iaccountid order by itenantid,tdate desc LIMIT 1 )am CROSS JOIN LATERAL( WITH RECURSIVE json_tree AS ( SELECT key, value, key AS path FROM jsonb_each(am.val) as e UNION ALL select t.key, t.value, json_tree.path || '.' || t.key as path from json_tree CROSS join lateral jsonb_each(json_tree.value) as t where jsonb_typeof(json_tree.value) = 'object' ) select path, value from json_tree where jsonb_typeof(value) <> 'object') as jt), transformed_json AS ( select fd.iaccountid, fd.tdate, fd.itenantid, jsonb_object_agg(fd.path, fd.value) as transformed_json from flattened_data fd group by fd.iaccountid,fd.tdate,fd.itenantid ) select ( select jsonb_object_agg( coalesce(m.vcdescription,kv.key), kv.value ) from jsonb_each(tj.transformed_json) kv left join profiles.metadata m on kv.key = m.vcpath ) AS final_json from transformed_json tj;",
        "params": [
          {
            "name": "iaccountid",
            "valueField": "input_data.iaccountid"
          },
          {
            "name": "itenantid",
            "valueField": "input_data.itenantid"
          }
        ]
      },
      {
        "conn": "txndb",
        "name": "AccountMaster",
        "type": "DB",
        "query": "SELECT json_build_object('ifsc', a.vcifsc, 'attribs', a.vcattribs, 'customer', json_build_object('email', c.vcemail, 'gender', c.vcgender, 'attribs', c.vcattribs, 'doi_dob', c.dtdoidob, 'customerId', c.icustomerid, 'externalId', c.vcexternalcustid, 'salutation', c.vcsalutation, 'default_mcc', c.imcc, 'postal_code', c.vcpostalcode, 'customerName', c.vccustomername, 'customerType', c.vccustomertype, 'verifiedName', c.vcverifiedname, 'identity_type1', c.vcidentitytype1, 'identity_type2', c.vcidentitytype2, 'onboarding_date', c.dtonboardingdate, 'iso_country_code', c.vccountrycode, 'identity_details1', c.vcidentitydetails1, 'identity_details2', c.vcidentitydetails2, 'registered_mobile', c.vcregisteredmobile, 'address_geolocation', c.vcregisteredaddressgeolocation), 'merchant', a.bmerchant, 'verified', a.bverified, 'accountId', a.iaccountid, 'itenantid', a.itenantid, 'externalId', a.vcexternalaccountid, 'accountName', a.vcaccountname, 'accountType', a.iaccounttypeid, 'default_mcc', a.imcc, 'expiry_date', a.dtexpirydate, 'accountNumber', a.vcaccount, 'record_status', a.irecordstatus, 'accountProvider', a.vcaccountproviderid, 'onboarding_date', a.dtonboardingdate) AS val FROM masters.accounts a JOIN masters.customers c ON a.icustomerid = c.icustomerid where iaccountid =:iaccountid and a.itenantid=:itenantid LIMIT 1;",
        "params": [
          {
            "name": "iaccountid",
            "valueField": "input_data.iaccountid"
          },
          {
            "name": "itenantid",
            "valueField": "input_data.itenantid"
          }
        ]
      }
    ],
    "postrequisites": [
      {
        "conn": "txndb",
        "name": "similar_cases",
        "type": "DB",
        "query": "select docid,ruleid,caseid,TO_CHAR(batchdate::date, 'YYYY-MM-DD') as batchdate,monthlyprofile, accountmaster from agents.rulespecificl1action d WHERE docid in :docid ;",
        "params": [
          {
            "name": "docid",
            "type": "list",
            "valueField": "*.docid"
          }
        ],
        "noofrows": "all"
      },
      {
        "conn": "txndb",
        "name": "policy",
        "type": "DB",
        "query": "select policy from agents.policies WHERE agentname='RuleSpecificL1Agent' limit 1;",
        "params": [],
        "noofrows": "one"
      }
    ],
    "prompt_template": {
      "input": [
        {
          "key": "postrequisites.policy",
          "name": "policy"
        },
        {
          "key": "postrequisites.similar_cases",
          "name": "similar_cases"
        },
        {
          "key": "input_data",
          "name": "case_attributes"
        }
      ],
      "template": "You are an expert in fraud detection policies and case analysis. Below is the policy document:\n{policy}\n\nA new case has the following attributes:\n{case_attributes}\n\nHere are relevant historical cases:\n{similar_cases}\n\nBased on the policy document and the historical cases, decide the most appropriate action and provide remarks.\n\nOutput your response in the json format with no additional text or formatting:\n{{\"comment\": \"<comment>\", \"decision\": \"<decision>\"}}"
    }
  },
  {
    "agent": "userManual",
    "model_config": {
      "params": {
        "temperature": 0
      },
      "role": "user"
    },
    "doctype": "UserManual",
    "input_data": [
      "user_query"
    ],
    "vectorstore": {
      "embedding_model": "sentence-transformers/all-mpnet-base-v2",
      "data": [
        "input_data.user_query"
      ],
      "filter": [
        "DocName",
        "Page ID",
        "Version"
      ],
      "metadata": [
        "Date",
        "DocName",
        "Page ID",
        "Version",
        "iTenantID"
      ],
      "cnt_similarities": 2
    },
    "prerequisites": [],
    "postrequisites": [
      {
        "conn": "txndb",
        "name": "relevant_docs",
        "type": "DB",
        "query": "select docid,doc_name,version,TO_CHAR(date::date, 'YYYY-MM-DD') as date, pageid, page_content from agents.user_manual d WHERE docid in :docid ;",
        "params": [
          {
            "name": "docid",
            "type": "list",
            "valueField": "*.docid"
          }
        ],
        "noofrows": "all"
      },
      {
        "conn": "txndb",
        "name": "policy",
        "type": "DB",
        "query": "select policy from agents.policies WHERE agentname='DP Help Agent' limit 1;",
        "params": [],
        "noofrows": "one"
      }
    ],
    "prompt_template": {
      "input": [
        {
          "key": "postrequisites.policy",
          "name": "policy"
        },
        {
          "key": "postrequisites.relevant_docs",
          "name": "relevant_docs"
        },
        {
          "key": "input_data.user_query",
          "name": "query"
        }
      ],
      "template": "You are a Dronapay Support agent.You have to follow the given policy document - {policy} Help answer User's query- {query} From the Dronapay documentation repository, here is the most relevant info-{relevant_docs} Answer User's query.Output your response in the json format with no additional text or formatting:\n{{\"answer\": \"<answer>\"}}"
    }
  },
  {
    "agent": "userManualPM",
    "model_config": {
      "params": {
        "temperature": 0
      },
      "role": "user"
    },
    "input_data": [
      "user_query"
    ],
    "vectorstore": {
      "embedding_model": "sentence-transformers/all-mpnet-base-v2",
      "data": [
        "input_data.user_query"
      ],
      "filter": [
        "DocName",
        "Page ID",
        "Version"
      ],
      "metadata": [
        "Date",
        "DocName",
        "Page ID",
        "Version",
        "iTenantID"
      ],
      "cnt_similarities": 2
    },
    "prerequisites": [],
    "response_type": "text",
    "postrequisites": [
      {
        "conn": "txndb",
        "name": "relevant_docs",
        "type": "DB",
        "query": "select docid,doc_name,version,TO_CHAR(date::date, 'YYYY-MM-DD') as date, pageid, page_content from agents.user_manual d WHERE docid in :docid ;",
        "params": [
          {
            "name": "docid",
            "type": "list",
            "valueField": "*.docid"
          }
        ],
        "noofrows": "all"
      },
      {
        "conn": "txndb",
        "name": "policy",
        "type": "DB",
        "query": "select policy from agents.policies WHERE agentname='DP Help Agent' limit 1;",
        "params": [],
        "noofrows": "one"
      }
    ],
    "prompt_template": {
      "input": [
        {
          "key": "postrequisites.policy",
          "name": "policy"
        },
        {
          "key": "postrequisites.relevant_docs",
          "name": "relevant_docs"
        },
        {
          "key": "input_data.user_query",
          "name": "query"
        }
      ],
      "template": "You are a Dronapay Support agent.You have to follow the given policy document - {policy} Help answer User's query- {query} From the Dronapay documentation repository, here is the most relevant info-{relevant_docs} Answer User's query"
    }
  },
  {
    "agent": "rulesDev",
    "model_config": {
      "params": {
        "temperature": 0
      },
      "role": "user"
    },
    "doctype": "RulesDev",
    "input_data": [
      "user_query"
    ],
    "vectorstore": {
      "embedding_model": "sentence-transformers/all-mpnet-base-v2",
      "data": [
        "input_data.user_query"
      ],
      "filter": [
        "RuleID"
      ],
      "metadata": [
        "RuleID",
        "iTenantID"
      ],
      "cnt_similarities": 2
    },
    "prerequisites": [],
    "postrequisites": [
      {
        "conn": "txndb",
        "name": "similar_cases",
        "type": "DB",
        "query": "select docid,ruleid,ruledescription, rulethresholds, rulefieldsdescription, ruletype, rulejson from agents.rulesdev d WHERE docid in :docid;",
        "params": [
          {
            "name": "docid",
            "type": "list",
            "valueField": "*.docid"
          }
        ],
        "noofrows": "all"
      },
      {
        "conn": "txndb",
        "name": "policy",
        "type": "DB",
        "query": "select policy from agents.policies WHERE agentname='Rule Developer' limit 1;",
        "params": [],
        "noofrows": "one"
      }
    ],
    "prompt_template": {
      "input": [
        {
          "key": "postrequisites.policy",
          "name": "policy"
        },
        {
          "key": "postrequisites.similar_cases",
          "name": "similar_cases"
        },
        {
          "key": "input_data.rule_expectation",
          "name": "query"
        }
      ],
      "template": "You are a rulesDev agent. You will help develop new rules in Drona. Below is the policy document that you have to follow - {policy}. Following is the user’s rule expectation and review it in a step wise manner following the policy - {query} .From historical rule requirements , here are the most relevant examples - {similar_cases}.Please construct JSONLogic for the rule. Output your response in the json format with no additional text or formatting:\n{{\"answer\": \"<answer>\"}}"
    }
  },
  {
    "agent": "sqlagentv1",
    "model_config": {
      "params": {
        "temperature": 0
      },
      "role": "user"
    },
    "doctype": "SQLDev",
    "input_data": [
      "user_query"
    ],
    "vectorstore": {
      "embedding_model": "sentence-transformers/all-mpnet-base-v2",
      "data": [
        "input_data.user_query"
      ],
      "filter": [
        "queryid"
      ],
      "metadata": [
        "queryid",
        "itenantid"
      ],
      "cnt_similarities": 2
    },
    "prerequisites": [],
    "postrequisites": [
      {
        "conn": "txndb",
        "name": "similar_queries",
        "type": "DB",
        "query": "SELECT docid, itenantid, queryid, sqldescription, sqlfielddescriptions, querytemplate  FROM agents.sqldev WHERE docid IN :docid;",
        "params": [
          {
            "name": "docid",
            "type": "list",
            "valueField": "*.docid"
          }
        ],
        "noofrows": "all"
      },
      {
        "conn": "txndb",
        "name": "policy",
        "type": "DB",
        "query": "SELECT policy FROM agents.policies WHERE agentname = 'SQL Developer' LIMIT 1;",
        "params": [],
        "noofrows": "one"
      }
    ],
    "prompt_template": {
      "input": [
        {
          "key": "postrequisites.policy",
          "name": "policy"
        },
        {
          "key": "postrequisites.similar_queries",
          "name": "similar_queries"
        },
        {
          "key": "input_data.query_expectation",
          "name": "query"
        }
      ],
      "template": "You are an expert SQL Developer. Follow the given policy to construct SQL queries from user expectations.\n\nPolicy:\n{policy}\n\nUser Request:\n{query}\n\nHere are similar past examples:\n{similar_queries}\n\nNow, generate a complete SQL query based on the user request. Do not return any explanation, formatting, JSON, or parameters—only the raw SQL query as plain text output. Output your response in the json format with no additional text or formatting:\n{{\"answer\": \"<answer>\"}}"
    }
  },
  {
    "agent": "uinavigatorv1",
    "model_config": {
      "params": {
        "temperature": 0
      },
      "role": "user"
    },
    "doctype": "uinavigatorv1",
    "input_data": [
      "user_query",
      "iTenantID"
    ],
    "vectorstore": {
      "embedding_model": "sentence-transformers/all-mpnet-base-v2",
      "data": [
        "input_data.user_query"
      ],
      "filter": [
        "iTenantID"
      ],
      "metadata": [
        "id",
        "itenantid"
      ],
      "cnt_similarities": 3
    },
    "prerequisites": [],
    "postrequisites": [
      {
        "conn": "txndb",
        "name": "similar_cases",
        "type": "DB",
        "query": "SELECT docid, screen_section, function, steps_to_reach, url FROM agents.uinavigator WHERE docid IN :docid;",
        "params": [
          {
            "name": "docid",
            "type": "list",
            "valueField": "*.docid"
          }
        ],
        "noofrows": "all"
      },
      {
        "conn": "txndb",
        "name": "policy",
        "type": "DB",
        "query": "SELECT policy FROM agents.policies WHERE agentname='UINavigator' LIMIT 1;",
        "params": [],
        "noofrows": "one"
      }
    ],
    "prompt_template": {
      "input": [
        {
          "key": "postrequisites.policy",
          "name": "policy"
        },
        {
          "key": "postrequisites.similar_cases",
          "name": "similar_cases"
        },
        {
          "key": "input_data.user_query",
          "name": "user_query"
        }
      ],
      "template": "You are an expert at navigating Dronapay's UI. Follow the policy document:\n{policy}\n\nThe user has provided the following query:\n{user_query}\n\n Here are similar cases related to user's query:\n{similar_cases}\n\n Help the user in reaching their requested place in Dronapay UI . Output your response in JSON format with no additional text or formatting:\n{{\"instructions\": \"<generated_instructions>\"}}"
    }
  },
  {
    "agent": "openaiVision",
    "model_config": {
      "params": {
        "temperature": 0,
        "model": "gpt-4o-mini"
      },
      "role": "user",
      "data": {
        "type": "image",
        "source_type": "base64",
        "mime_type": "image/jpeg"
      },
      "data_key": "input_data.base64_img"
    },
    "doctype": "openaiVision",
    "input_data": [
      "base64_img"
    ],
    "prerequisites": [],
    "postrequisites": [],
    "prompt_template": {
      "input": [
      ],
      "template": "Please do a complete OCR of all the things present in the image. Output your response in the json format with no additional text or formatting:\n{{\"answer\": \"<answer>\"}}"
    }
  },
  {
    "agent": "ocrToFhir",
    "model_config": {
      "params": {
        "temperature": 0
      },
      "role": "user"
    },
    "doctype": "ocrToFhir",
    "input_data": [
      "ocr_text"
    ],
    "prerequisites": [],
    "postrequisites": [],
    "prompt_template": {
      "input": [
        {
          "key": "input_data.ocr_text",
          "name": "ocr_text"
        },
        {
          "key": "",
          "name": "template"
        }
      ],
      "template": "From the above template given - {template} fill the json with ocr text only- {ocr_text} produce a new json as per FHIR. Return only json and no other text."
    }
  },
  {
    "agent": "orchestratorAgent",
    "model_config": {
      "params": {
        "temperature": 0
      },
      "role": "user"
    },
    "doctype": "Orchestrator",
    "input_data": [
      "itenantid",
      "iuserid",
      "user_query"
    ],
    "prerequisites": [
      {
        "conn": "txndb",
        "name": "agentdescriptions",
        "type": "DB",
        "query": "SELECT vcagentname, vcagentdescription FROM ui.aiagents WHERE itenantid = :itenantid AND irecordstatus = 1 AND vcinitiation = 'Chat';",
        "params": [
          {
            "name": "itenantid",
            "valueField": "input_data.itenantid"
          }
        ],
        "noofrows": "all"
      },
      {
        "conn": "txndb",
        "name": "chathistory",
        "type": "DB",
        "query": "SELECT vcmessage FROM ui.agentchats WHERE iuserid = :iuserid ORDER BY dttimestamp DESC LIMIT 10;",
        "params": [
          {
            "name": "iuserid",
            "valueField": "input_data.iuserid"
          }
        ],
        "noofrows": "all"
      },
      {
        "conn": "txndb",
        "name": "policy",
        "type": "DB",
        "query": "SELECT policy FROM agents.policies WHERE agentname='Drona' LIMIT 1;",
        "params": [],
        "noofrows": "one"
      }
    ],
    "postrequisites": [],
    "prompt_template": {
      "input": [
        {
          "key": "prerequisites.agentdescriptions",
          "name": "agentdescriptions"
        },
        {
          "key": "prerequisites.chathistory",
          "name": "chathistory"
        },
        {
          "key": "input_data.user_query",
          "name": "user_query"
        },
        {
          "key": "prerequisites.policy",
          "name": "policy"
        }
      ],
      "template": "You are the central Orchestrator Agent overseeing a network of specialized agents in a multi-agent Retrieval-Augmented Generation (RAG) system.\n\n=== Available Agents and Capabilities ===\n{agentdescriptions}\n\n=== User Query ===\n{user_query}\n\n=== Policy Context ===\n{policy}\n\n=== Chat History ===\n{chathistory}\n\nYour responsibilities:\n1. Assess whether the user query is relevant, safe, and within the permitted scope.\n2. If it is a follow-up query, use the chat history to maintain context and continuity.\n3. If needed, refine or rewrite the query to better capture the user's intent.\n4. Select the single most suitable agent from the list to handle the query.\n5. Respond strictly in one of the following JSON formats:\n\n--- If the query is valid and can be routed:\n{{{{\n  \"data\": {{{{\n    \"user_query\": \"<user_query>\"\n  }}}},\n  \"agentid\": \"<vcagentname from agentdescriptions>\"\n}}}}\n\n--- If the query is invalid, unsafe, or out of scope of vcagentdescription from agentdescriptions:\n{{  \"answer\": \"<clear, concise explanation>\"}}\n\nOnly output the JSON. Do not include explanations, comments, or additional formatting."
    }
  }
]