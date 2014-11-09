#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pickle

from flask import jsonify, request
from sqlalchemy import desc
from datetime import datetime

from .startup import app
from .node import (create_token, get_chunk_contract,
                   verify_proof,  update_contract,
                   lookup_contract)
from .models import Token
from .exc import InvalidParameterError, NotFoundError, HttpHandler


@app.route('/')
def api_index():
    return jsonify(msg='ok')


@app.route('/api/downstream/status/list/',
           defaults={'o': False, 'd': False, 'sortby': 'id',
                     'limit': None, 'page': None})
@app.route('/api/downstream/status/list/<int:limit>',
           defaults={'o': False, 'd': False, 'sortby': 'id', 'page': None})
@app.route('/api/downstream/status/list/<int:limit>/<int:page>',
           defaults={'o': False, 'd': False, 'sortby': 'id'})
@app.route('/api/downstream/status/list/by/<sortby>',
           defaults={'o': False, 'd': False, 'limit': None, 'page': None})
@app.route('/api/downstream/status/list/by/d/<sortby>',
           defaults={'o': False, 'd': True, 'limit': None, 'page': None})
@app.route('/api/downstream/status/list/by/<sortby>/<int:limit>',
           defaults={'o': False, 'd': False, 'page': 0})
@app.route('/api/downstream/status/list/by/d/<sortby>/<int:limit>',
           defaults={'o': False, 'd': True, 'page': 0})
@app.route('/api/downstream/status/list/by/<sortby>/<int:limit>/<int:page>',
           defaults={'o': False, 'd': False})
@app.route('/api/downstream/status/list/by/d/<sortby>/<int:limit>/<int:page>',
           defaults={'o': False, 'd': True})
@app.route('/api/downstream/status/list/online/',
           defaults={'o': True, 'd': False, 'sortby': 'id',
                     'limit': None, 'page': None})
@app.route('/api/downstream/status/list/online/<int:limit>',
           defaults={'o': True, 'd': False, 'sortby': 'id', 'page': None})
@app.route('/api/downstream/status/list/online/<int:limit>/<int:page>',
           defaults={'o': True, 'd': False, 'sortby': 'id'})
@app.route('/api/downstream/status/list/online/by/<sortby>',
           defaults={'o': True, 'd': False, 'limit': None, 'page': None})
@app.route('/api/downstream/status/list/online/by/d/<sortby>',
           defaults={'o': True, 'd': True, 'limit': None, 'page': None})
@app.route('/api/downstream/status/list/online/by/<sortby>/<int:limit>',
           defaults={'o': True, 'd': False, 'page': 0})
@app.route('/api/downstream/status/list/online/by/d/<sortby>/<int:limit>',
           defaults={'o': True, 'd': True, 'page': 0})
@app.route('/api/downstream/status/list/online/by/'
           '<sortby>/<int:limit>/<int:page>',
           defaults={'o': True, 'd': False})
@app.route('/api/downstream/status/list/online/by/d/'
           '<sortby>/<int:limit>/<int:page>',
           defaults={'o': True, 'd': True})
def api_downstream_status_list(o, d, sortby, limit, page):
    with HttpHandler() as handler:
        sort_map = {'id': Token.farmer_id,
                    'address': Token.addr,
                    'uptime': None,
                    'heartbeats': Token.hbcount,
                    'contracts': Token.contract_count,
                    'size': Token.size,
                    'online': Token.online}

        if (sortby not in sort_map):
            raise InvalidParameterError('Invalid sort')

        # we need to calculate uptime manually
        # what we're doing here is going through each farmer's contracts. it
        # sums up the time that the farmer has been online, and then divides
        # by the total time the farmer has had any contracts.
        if o:
            all_tokens = Token.query.filter(Token.online).all()
        else:
            all_tokens = Token.query.all()
        uptimes = dict()
        for t in all_tokens:
            uptimes[t.id] = t.uptime

        if (sortby == 'uptime'):
            key = lambda x: uptimes[x.id]
            if (d):
                key = lambda x: -uptimes[x.id]
            farmer_list = sorted(all_tokens, key=key)
            if (page is not None):
                farmer_list = farmer_list[limit * page:limit * page + limit]

            if (limit is not None):
                farmer_list = farmer_list[:limit]
        else:
            sort_stmt = sort_map[sortby]
            if (d):
                sort_stmt = desc(sort_stmt)

            farmer_list_query = Token.query

            if (o):
                farmer_list_query = farmer_list_query.filter(Token.online)

            farmer_list_query = farmer_list_query.order_by(sort_stmt)

            if (limit is not None):
                farmer_list_query = farmer_list_query.limit(limit)

            if (page is not None):
                farmer_list_query = farmer_list_query.offset(limit * page)

            farmer_list = farmer_list_query.all()

        farmers = list(map(lambda a:
                           dict(id=a.farmer_id,
                                address=a.addr,
                                location=pickle.loads(a.location),
                                uptime=round(uptimes[a.id] * 100, 2),
                                heartbeats=a.hbcount,
                                contracts=a.contract_count,
                                last_due=a.last_due,
                                size=a.size,
                                online=a.online), farmer_list))

        return jsonify(farmers=farmers)

    return handler.response


@app.route('/api/downstream/status/show/<farmer_id>')
def api_downstream_status_show(farmer_id):
    with HttpHandler() as handler:
        a = Token.query.filter(Token.farmer_id == farmer_id).first()

        if (a is None):
            raise NotFoundError('Nonexistant farmer id.')

        return jsonify(id=a.farmer_id,
                       address=a.addr,
                       location=pickle.loads(a.location),
                       uptime=round(a.uptime * 100, 2),
                       heartbeats=a.hbcount,
                       contracts=a.contract_count,
                       last_due=a.last_due,
                       size=a.size,
                       online=a.online)

    return handler.response


@app.route('/api/downstream/new/<sjcx_address>')
def api_downstream_new_token(sjcx_address):
    # generate a new token
    with HttpHandler() as handler:
        db_token = create_token(sjcx_address, request.remote_addr)
        beat = pickle.loads(db_token.heartbeat)
        pub_beat = beat.get_public()
        return jsonify(token=db_token.token,
                       type=type(beat).__name__,
                       heartbeat=pub_beat.todict())

    return handler.response


@app.route('/api/downstream/heartbeat/<token>')
def api_downstream_heartbeat(token):
    """This route gets the heartbeat for a token.
    Provided for nodes that need to recover their heartbeat.
    The heartbeat does not contain any private information,
    so having someone else's heartbeat does not help you.
    """
    with HttpHandler() as handler:
        db_token = Token.query.filter(Token.token == token).first()

        if (db_token is None):
            raise NotFoundError('Nonexistent token')

        beat = pickle.loads(db_token.heartbeat)
        pub_beat = beat.get_public()
        return jsonify(token=db_token.token,
                       type=type(beat).__name__,
                       heartbeat=pub_beat.todict())

    return handler.response


@app.route('/api/downstream/chunk/<token>')
def api_downstream_chunk_contract(token):
    with HttpHandler() as handler:
        db_contract = get_chunk_contract(token, request.remote_addr)

        with open(db_contract.tag_path, 'rb') as f:
            tag = pickle.loads(f.read())
        chal = pickle.loads(db_contract.challenge)

        # now since we are prototyping, we can delete the tag and file
        os.remove(db_contract.file.path)
        os.remove(db_contract.tag_path)

        return jsonify(seed=db_contract.seed,
                       size=db_contract.size,
                       file_hash=db_contract.file.hash,
                       challenge=chal.todict(),
                       tag=tag.todict(),
                       due=(db_contract.due - datetime.utcnow()).
                       total_seconds())

    return handler.response


@app.route('/api/downstream/challenge/<token>/<file_hash>')
def api_downstream_chunk_contract_status(token, file_hash):
    """For prototyping, this will generate a new challenge
    """
    with HttpHandler() as handler:
        db_contract = update_contract(token, file_hash)

        return jsonify(challenge=pickle.loads(db_contract.challenge).todict(),
                       due=(db_contract.due - datetime.utcnow()).
                       total_seconds(),
                       answered=db_contract.answered)

    return handler.response


@app.route('/api/downstream/answer/<token>/<file_hash>', methods=['POST'])
def api_downstream_challenge_answer(token, file_hash):
    with HttpHandler() as handler:
        d = request.get_json(silent=True)

        if (dict is False or not isinstance(d, dict) or 'proof' not in d):
            raise InvalidParameterError('Posted data must be an JSON encoded '
                                        'proof object: '
                                        '{"proof":"...proof object..."}')

        db_contract = lookup_contract(token, file_hash)

        beat = pickle.loads(db_contract.token.heartbeat)

        try:
            proof = beat.proof_type().fromdict(d['proof'])
        except:
            raise InvalidParameterError('Proof corrupted.')

        if (not verify_proof(token, file_hash, proof, request.remote_addr)):
            raise InvalidParameterError(
                'Invalid proof.')

        return jsonify(status='ok')

    return handler.response
