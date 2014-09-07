#!/usr/bin/env python
# -*- coding: utf-8 -*-
import hashlib
import os

from flask import jsonify, request
from downstream_node.models import Challenges

from downstream_node.startup import app
from downstream_node.lib import gen_challenges


@app.route('/api/downstream/challenge')
def api_downstream_heartbeats_file():
    """

    :param filepath:
    """
    # Make assertions about the request to make sure it's valid.
    try:
        assert request.json
    except AssertionError:
        resp = jsonify(msg="No JSON received")
        resp.status_code = 400
        return resp

    try:
        assert 'filepath' in request.json
    except AssertionError:
        resp = jsonify(msg="missing filepath in request JSON")
        resp.status_code = 400
        return resp

    filepath = request.json.get('filepath')

    # Commenting out while still in development, should be used in prod
    # try:
    #     assert os.path.isfile(filepath)
    # except AssertionError:
    #     resp = jsonify(msg="filepath is not a valid filepath")
    #     resp.status_code = 400
    #     return resp

    # Hardcode filepath to the testfile in tests while in development
    filepath = os.path.abspath(
        os.path.join(
            os.path.split(__file__)[0], '..', 'tests', 'thirty-two_meg.testfile')
    )

    root_seed = hashlib.sha256(os.urandom(32)).hexdigest

    query = Challenges.query().filter(Challenges.filepath == filepath)

    if not query:
        gen_challenges(filepath, root_seed)
        query = Challenges.query().filter(Challenges.filepath == filepath)

    return jsonify(query)


@app.route('/api/downstream/new/<sjcx_address>')
def api_downstream_new_token(sjcx_address):
    return jsonify(token='dfs9mfa2')


@app.route('/api/downstream/chunk/<token>')
def api_downstream_chunk_contract(token):
    return jsonify(status='no_chunks')
    return jsonify(status='no_token')
    return jsonify(status='error')
    return jsonify(status='ok')


@app.route('/api/downstream/remove/<token>/<file_hash>', methods=['DELETE'])
def api_downstream_end_contract(token, file_hash):
    return jsonify(status='no_token')
    return jsonify(status='no_hash')
    return jsonify(status='error')
    return jsonify(status='ok')


@app.route('/api/downstream/due/<account_token>')
def api_downstream_chunk_contract_status(account_token):
    return jsonify(contracts="data")


@app.route('/api/downstream/challenge/<token>/<file_hash>/<hash_response>')
def api_downstream_answer_chunk_contract(token, file_hash, hash_response):
    return jsonify(status="pass")
    return jsonify(status="fail")