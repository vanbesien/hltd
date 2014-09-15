#!/bin/env python

import sys
import requests

sys.path.append('/opt/hltd/python')
sys.path.append('/opt/hltd/lib')

import mappings

from pyelasticsearch.client import ElasticSearch
from pyelasticsearch.client import IndexAlreadyExistsError
from pyelasticsearch.client import ElasticHttpError
from pyelasticsearch.client import ConnectionError
from pyelasticsearch.client import Timeout

if len(sys.argv)>=4:

  command = sys.argv[1]
  server_url=sys.argv[2]
  index_name=sys.argv[3]
else:
  print "Parameters: command[create,alias,mapping] server url, index name"
  print "  COMMANDS:"
  print "    create: create index"
  print "    alias: create index *_read and *_write aliases"
  print "    create missing document mappings for the index"
  sys.exit(1)

if server_url.startswith('http://')==False:
  server_url='http://'+server_url

#connection
es = ElasticSearch(server_url)

#pick mapping
if index_name.startswith('runindex'):
  my_mapping = mappings.central_runindex_mapping
if index_name.startswith('boxinfo'):
  my_mapping = mappings.central_boxinfo_mapping

#alias convention
alias_write=index_name+"_write"
alias_read=index_name+"_read"

if command=='create':
  es.create_index(index_name, settings={ 'settings': mappings.central_es_settings, 'mappings': my_mapping })

if command=='alias':
  #check if alias exists
  status1 = requests.get(server_url+'/_alias/'+alias_write).status_code
  status2 = requests.get(server_url+'/_alias/'+alias_read).status_code
  aliases_settings = { "actions": []}
  if status1!=200:
    alias_settings["actions"].append({"add": {"index": index_name, "alias": alias_write}})
  else:
    print alias_write,"already exists"
  if status2!=200:
    alias_settings["actions"].append({"add": {"index": index_name, "alias": alias_read}})
  else:
    print alias_read,"already exists"
  if len(alias_settings["actions"])>0:
    es.update_aliases(aliases_settings)

if command=='mapping':
    for key in my_mapping:
        try:
            doc = my_mapping[key]
            res = requests.get(server_url+'/'+index_name+'/'+key+'/_mapping')
            if res.status_code==404:
                print "index doesn't exist. Try to create it first?"
                break
            #only update if mapping is empty
            if res.status_code==200:
              if res.content.strip()=='{}':
                result = requests.post(server_url+'/'+index_name+'/'+key+'/_mapping',str(doc))
                if result.status_code==200:
                    print "created document mapping for '"+key+"'"
                else:
                    print "Failed to create mapping for",key
                    print result.content
              else:
                print "document mapping for '"+key+"' already exists"
        except Exception:
            print ex
            pass


