# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import functools
import json
import logging
import os
import time
from datetime import date

from bottle import Bottle, run, request
from gevent import monkey

monkey.patch_all()
from ..utils import level_debug
from ..utils.analysis_codes import VERBOSE_ERROR_TYPE
from ..data_model.dao.mongodb import UrlManagerDao, DocumentsDao, ProxiesDao

logRest = logging.getLogger("Scrap_Ufal.RESTAPI")
logRest.setLevel(level_debug)

app = Bottle()
app.patch = functools.partial(app.route, method='PATCH')

APP_NAME = "scrapufal"
VERSION = "v1"

MODE = os.environ.get('MODE', 'DEV')

if MODE == 'PROD':
    client = UrlManagerDao(os.environ.get('MONGODB_ADDON_URI'))
    docs_dao = DocumentsDao(os.environ.get('MONGODB_ADDON_URI'))
    proxy_dao = ProxiesDao(os.environ.get('MONGODB_ADDON_URI'))
else:
    client = UrlManagerDao(host='172.17.0.1')
    docs_dao = DocumentsDao(host='172.17.0.1')
    proxy_dao = ProxiesDao(host='172.17.0.1')

NAME_VERSION = "/%s/%s/" % (APP_NAME, VERSION)


@app.put(NAME_VERSION + "urls")
def insert_urls():
    body_error = {"message": {"errors": [], "success": False}}
    if request.headers.get('Content-Type') != "application/json":
        logRest.warn("Invalid Content-Type")
        body_error['message']['errors'].append("Invalid Content-Type")
        return body_error

    data = request.json

    try:
        list_urls = data['urls']
        client.set_chunk_url(list_urls)
    except Exception as e:
        logRest.error("Some error are happens", exc_info=True)
        body_error['message']['errors'].append(str(e))
        return body_error

    return {"message": {"success": True}}


@app.get(NAME_VERSION + "status/urls/<collection>")
def status_enqueue(collection):
    key = {"_id": int(date.today().strftime("%Y%m%d"))}

    result = client.db_urls[collection].find_one(key)

    result = {"urls": []} if not result else result
    return {
        "message":
            {"success": True, "result": "%s have: %s" %
                                        (collection.upper(),
                                         len(result['urls']))}
    }


@app.get(NAME_VERSION + "status/documents/<start:re:\d{8}>/<end:re:\d{8}>/")
def count_documents_last_days(start, end):
    return "%s - %s\n" % (start, end)


@app.route(NAME_VERSION + 'errors_code/', method="OPTIONS")
def get_list_errors():
    return VERBOSE_ERROR_TYPE


@app.get(NAME_VERSION + 'analyze_document/<doc_id:re:\d{4}\w{2}\d{6}>/')
def recover_analyzed_document(doc_id):
    doc_found = docs_dao.documents.find_one({"_id": doc_id, "analysed": True})
    if not doc_found:
        return 'aqui eu mando uma mensagem informando pra adiconar X, Y, Z' \
               'parametros para adicionar na queue esse documento'

    json_response = {
        'time_analyze_ms': doc_found['time_analyze_ms'],
        'errors': doc_found['errors'],
        'url': doc_found['geral_data']['url']
    }

    return json_response


@app.get("/")
def home():
    start = time.time()
    key = {"_id": int(date.today().strftime("%Y%m%d"))}

    result_queue = client.db_urls['queue'].find_one(key)
    result_queue_loaded = client.db_urls['queue_loaded'].find_one(key)
    result_fallback = client.db_urls['fallback'].find_one(key)
    result_finder_urls = client.finder_urls_notas.find({}).count()

    pipeline = [{'$project': {'_id': '$dados_basicos.fase'}},
                {'$group': {'_id': '$_id', 'total': {'$sum': 1}}}]

    documents_sumerized = docs_dao.documents.aggregate(pipeline)
    result_docs = {'Total': 0}
    for item in documents_sumerized:
        result_docs[item['_id']] = item['total']
        result_docs['Total'] += item['total']

    proxies_in_use = proxy_dao.proxies.find({"in_use": True}).count()
    proxies_available = proxy_dao.proxies.find({"in_use": False}).count()

    result = {
        "urls": {
            "queue": len(result_queue['urls']) if result_queue else 0,
            "queue_loaded": len(
                result_queue_loaded['urls']) if result_queue_loaded else 0,
            "fallback": len(result_fallback['urls']) if result_fallback else 0,
            "finder_urls": result_finder_urls
        },
        "documents": result_docs,
        "proxies": {
            "in_use": proxies_in_use,
            "available": proxies_available
        }
    }
    return_msg = json.dumps(result, indent=3)
    return_msg = "<pre>" + return_msg + "</pre>"
    return_msg += "<br>elapse: %.6f" % (time.time() - start)
    return_msg += "<script>setInterval(function() {location.reload(true)}, 20000);</script>"
    return return_msg


def run_app():
    run(app, host='0.0.0.0', port=8080,
        debug=True, reloader=True, server='gevent')


if __name__ == '__main__':
    run_app()
