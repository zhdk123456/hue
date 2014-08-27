#!/usr/bin/env python
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


## Main views are inherited from Beeswax.


import logging
import json

from django.http import HttpResponse

from desktop.lib.django_util import render
from beeswax.design import hql_query
from beeswax.server import dbms
from beeswax.server.dbms import get_query_server_config


LOG = logging.getLogger(__name__)


def dashboard(request):
  return render('dashboard.mako', request, {
    'query_json': json.dumps({}),
    'dashboard_json': json.dumps({'layout': [
              {"size":2,"rows":[{"widgets":[{"size":12,"name":"Top salaries","id":"52f07188-f30f-1296-2450-f77e02e1a5c1","widgetType":"facet-widget",
                   "properties":{},"offset":0,"isLoading":True,"klass":"card card-widget span12"}]}],"drops":["temp"],"klass":"card card-home card-column span2"},
              {"size":10,"rows":[{"widgets":[
                  {"size":12,"name":"Grid Results","id":"52f07188-f30f-1296-2450-f77e02e1a5c0","widgetType":"resultset-widget",
                   "properties":{},"offset":0,"isLoading":True,"klass":"card card-widget span12"}]}],
              "drops":["temp"],"klass":"card card-home card-column span10"}
         ],
        'facets': [{'id': '52f07188-f30f-1296-2450-f77e02e1a5c1', 'label': 'Top salaries', 'field': 'salary', 'widget_type': 'facet-widget', 
                    'properties': {'limit': 10}}],
        'properties': [{'database': 'default', 'table': 'sample_07'}]
        }), 
  })


def query(request):  
  result = {
    'status': -1,
    'data': {}
  }
    
  fqs = json.loads(request.POST['query'])['fqs']

  if fqs:
    filters = ' AND '.join(['%s = %s' % (fq['field'], value) for fq in fqs for value in fq['filter']])
  else:
    filters = ''

  if 'facet' in request.POST: 
    facet = json.loads(request.POST['facet'])
    database = 'default'
    table = 'sample_07'  
    hql = "SELECT %(field)s FROM %(database)s.%(table)s WHERE %(field)s IS NOT NULL %(filters)s ORDER BY %(field)s DESC LIMIT %(limit)s" % {
        'database': database, 'table': table, 'limit': facet['properties']['limit'],
        'field': facet['field'],
        'filters': (' AND ' + filters) if filters else ''
    }
    result['id'] = facet['id']
    result['field'] = facet['field']
    fields = [fq['field'] for fq in fqs]
    result['selected'] = facet['field'] in fields
  else:
    database = 'default'
    table = 'sample_07'    
    hql = "SELECT * FROM %s.%s" % (database, table,)
    if filters:
      hql += ' WHERE ' + filters

  query_server = get_query_server_config(name='impala')
  query = hql_query(hql)
  db = dbms.get(request.user, query_server=query_server)
  handle = db.execute_and_wait(query, timeout_sec=5.0)

  if handle:
    data = db.fetch(handle, rows=100)
    result['data'] = list(data.rows())
    result['cols'] = list(data.cols())
    result['status'] = 0
    db.close(handle)
    
  return HttpResponse(json.dumps(result), mimetype="application/json")


def new_facet(request):
  result = {'status': -1, 'message': 'Error'}

  try:
    dashboard = json.loads(request.POST.get('dashboard', '{}')) # Perms
    facet_json = json.loads(request.POST.get('facet_json', '{}'))
    facet_field = request.POST['field']

    result['message'] = ''
    result['facet'] =  {
        'id': facet_json['id'],
        'label': facet_field,
        'field': facet_field,
        'widget_type': facet_json['widgetType'], 
        'properties': {'limit': 10}
    }
    result['status'] = 0
  except Exception, e:
    result['message'] = unicode(str(e), "utf8")

  return HttpResponse(json.dumps(result), mimetype="application/json")


def new_search(request):

  return render('dashboard.mako', request, {
    'query_json': json.dumps({}),
    'dashboard_json': json.dumps({'layout': [
              {"size":2,"rows":[],"drops":["temp"],"klass":"card card-home card-column span2"},
              {"size":10,"rows":[{"widgets":[
                  {"size":12,"name":"Grid Results","id":"52f07188-f30f-1296-2450-f77e02e1a5c0","widgetType":"resultset-widget",
                   "properties":{},"offset":0,"isLoading":True,"klass":"card card-widget span12"}]}],
              "drops":["temp"],"klass":"card card-home card-column span10"}
         ],
        'facets': [],
        'properties': [{'database': 'default', 'table': 'sample_07'}]
        }), 
  })



def _create_facet(collection, user, facet_id, facet_label, facet_field, widget_type):
  properties = {
    'sort': 'desc',
    'canRange': False,
    'stacked': False,
    'limit': 10,
    'mincount': 0,
    'isDate': False,
    'andUp': False,  # Not used yet
  }

  facet_type = 'field'

  if widget_type == 'map-widget':
    properties['scope'] = 'world'
    properties['mincount'] = 1
    properties['limit'] = 100

  return {
    'id': facet_id,
    'label': facet_label,
    'field': facet_field,
    'type': facet_type,
    'widgetType': widget_type,
    'properties': properties
  }
