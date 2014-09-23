#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import hashlib

from heartbeat import Heartbeat
from flask import jsonify, request, abort

from downstream_node.startup import app
from downstream_node.config import config
from downstream_node.models import Challenges
from downstream_node.lib import gen_challenges
from downstream_node.lib.utils import query_to_list, load_heartbeat


@app.route('/')
def api_index():
    return jsonify(msg='ok')


@app.route('/api/downstream/challenges/<filepath>')
def api_downstream_challenge(filepath):
    """

    :param filepath:
    """
    # Make assertions about the request to make sure it's valid.

    # Commenting out while still in development, should be used in prod
    # try:
    #     assert os.path.isfile(os.path.join('/opt/files', filename))
    # except AssertionError:
    #     resp = jsonify(msg="file name is not valid")
    #     resp.status_code = 400
    #     return resp

    # Hardcode filepath to the testfile in tests while in development
    filepath = os.path.abspath(
        os.path.join(
            os.path.split(__file__)[0], '..', 'tests', 'thirty-two_meg.testfile')  # NOQA
    )

    root_seed = hashlib.sha256(os.urandom(32)).hexdigest()
    filename = os.path.split(filepath)[1]
    app.logger.debug('Fetching challenges for %s' % filename)

    query = Challenges.query.filter(Challenges.filename == filename)

    if not query.all():
        app.logger.debug('No entry in database for file %s;'
                         ' generating challenes' % filename)
        gen_challenges(filepath, root_seed)
        query = Challenges.query.filter(Challenges.filename == filename)

    return jsonify(challenges=query_to_list(query))


@app.route('/api/downstream/challenges/answer/<filepath>', methods=['POST'])
def api_downstream_challenge_answer(filepath):
    """

    :param filepath:
    :return:
    """
    request_json = request.get_json(force=True, silent=True)

    # Make assertions about the request to make sure it's valid.
    try:
        assert request_json
    except AssertionError:
        app.logger.debug('Request missing JSON request body')
        resp = jsonify(msg="missing request json")
        resp.status_code = 400
        return resp

    req_json_keys = ['seed', 'block', 'response']

    try:
        assert sorted(req_json_keys) == sorted(request_json.keys())
    except AssertionError:
        app.logger.debug('Incoming request did not have all keys.')
        resp = jsonify(msg="missing data")
        resp.status_code = 400
        return resp

    # Hardcode filepath to the testfile in tests while in development
    filepath = os.path.abspath(
        os.path.join(
            os.path.split(__file__)[0], '..', 'tests', 'thirty-two_meg.testfile')  # NOQA
    )
    filename = os.path.split(filepath)[1]
    app.logger.debug('Incoming request for file %s' % filename)

    # Commenting out while still in development, should be used in prod
    # try:
    #     assert os.path.isfile(os.path.join('/opt/files', filename))
    # except AssertionError:
    #     resp = jsonify(msg="file name is not valid")
    #     resp.status_code = 400
    #     return resp

    query = Challenges.query.filter(
        Challenges.filename == filename,
        Challenges.block == request_json.get('block'),
        Challenges.seed == request_json.get('seed'),
    )
    challenge = query.all()

    # Oh, and challenge should only be len of 1, or we gots problems
    if len(challenge) == 0:
        app.logger.debug('Nothing found in DB for file %s' % filename)
        abort(404)
    elif len(challenge) < 1:
        app.logger.debug('More than one entry in DB '
                         'with same file, block, seed')
        abort(400)

    node_hb = Heartbeat(filepath, secret=config.SECRET_KEY)
    node_hb = load_heartbeat(node_hb, query)
    result = node_hb.check_answer(request_json.get('response'))

    if result is True:
        app.logger.debug('Match found on file %s' % filename)
        return jsonify(msg='ok', match=True)
    elif result is False:
        app.logger.debug('Match not found on file %s' % filename)
        return jsonify(msg='ok', match=False)
    else:
        resp = jsonify(msg='error')
        resp.status_code = 500
        return resp


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
