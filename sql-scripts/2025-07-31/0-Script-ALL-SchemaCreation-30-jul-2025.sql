CREATE SCHEMA IF NOT EXISTS agents;

CREATE EXTENSION IF NOT EXISTS vector
    SCHEMA agents
    VERSION "0.7.0";

CREATE TABLE IF NOT EXISTS agents.fhirdoc
(
    itenantid integer,
    doctypeid integer NOT NULL,
    documentname character varying(100) COLLATE pg_catalog."default",
    fhir_sample text COLLATE pg_catalog."default",
    fhir_template text COLLATE pg_catalog."default",
    docid character varying(100) COLLATE pg_catalog."default",
    CONSTRAINT fhirdoc_pkey PRIMARY KEY (doctypeid)
)



CREATE TABLE IF NOT EXISTS agents.langchain_pg_collection
(
    uuid uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    cmetadata json,
    CONSTRAINT langchain_pg_collection_pkey PRIMARY KEY (uuid),
    CONSTRAINT langchain_pg_collection_name_key UNIQUE (name)
)



CREATE TABLE IF NOT EXISTS agents.langchain_pg_embedding
(
    id character varying COLLATE pg_catalog."default" NOT NULL,
    collection_id uuid,
    embedding agents.vector,
    document character varying COLLATE pg_catalog."default",
    cmetadata jsonb,
    CONSTRAINT langchain_pg_embedding_pkey PRIMARY KEY (id)
)



CREATE TABLE IF NOT EXISTS agents.policies
(
    agentname character varying(255) COLLATE pg_catalog."default" NOT NULL,
    itenantid integer NOT NULL,
    policy text COLLATE pg_catalog."default",
    CONSTRAINT policies_pkey PRIMARY KEY (agentname, itenantid)
)




CREATE TABLE IF NOT EXISTS agents.rulesdev
(
    ruleid integer,
    ruledescription text COLLATE pg_catalog."default",
    rulethresholds jsonb,
    rulefieldsdescription jsonb,
    ruletype character varying(50) COLLATE pg_catalog."default",
    rulejson jsonb,
    itenantid integer,
    docid character varying(255) COLLATE pg_catalog."default"
)





CREATE TABLE IF NOT EXISTS agents.rulespecificl1action
(
    ruleid jsonb NOT NULL,
    caseid character varying(100) COLLATE pg_catalog."default" NOT NULL,
    batchdate date,
    monthlyprofile jsonb,
    accountmaster jsonb,
    l1_comment text COLLATE pg_catalog."default",
    l1_decision character varying(100) COLLATE pg_catalog."default",
    itenantid integer,
    docid character varying(255) COLLATE pg_catalog."default",
    CONSTRAINT rulespecificl1action_pkey PRIMARY KEY (ruleid, caseid)
)






CREATE TABLE IF NOT EXISTS agents.sqldev
(
    itenantid integer,
    queryid integer NOT NULL,
    sqldescription text COLLATE pg_catalog."default",
    sqlfielddescriptions jsonb,
    querytemplate text COLLATE pg_catalog."default",
    docid character varying(100) COLLATE pg_catalog."default",
    CONSTRAINT sqldev_pkey PRIMARY KEY (queryid)
)




CREATE TABLE IF NOT EXISTS agents.uinavigator
(
    id integer NOT NULL,
    screen_section text COLLATE pg_catalog."default",
    function text COLLATE pg_catalog."default",
    steps_to_reach text COLLATE pg_catalog."default",
    url text COLLATE pg_catalog."default",
    itenantid integer,
    docid character varying(100) COLLATE pg_catalog."default",
    CONSTRAINT uinavigator_pkey PRIMARY KEY (id)
)




CREATE TABLE IF NOT EXISTS agents.user_manual
(
    doc_name character varying(100) COLLATE pg_catalog."default" NOT NULL,
    version character varying(50) COLLATE pg_catalog."default" NOT NULL,
    date date,
    pageid integer NOT NULL,
    page_content text COLLATE pg_catalog."default",
    itenantid integer,
    docid character varying(255) COLLATE pg_catalog."default",
    CONSTRAINT user_manual_pkey PRIMARY KEY (doc_name, version, pageid)
)



CREATE TABLE IF NOT EXISTS agents.openaivision
(
    itenantid integer NOT NULL,
    docid character varying(255) COLLATE pg_catalog."default"
)
