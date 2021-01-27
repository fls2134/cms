import os
import requests
from requests.auth import HTTPDigestAuth
import traceback
from flask import Blueprint, jsonify, request

from tasks import cv_task
from model.db_base import db
from model.target_model import Target
from model.project_model import Project
from model.device_model import Device
from util.logger import logger

camera_route = Blueprint('camera_route', __name__)
DEVICE_IP = os.environ.get('DEVICE_IP')
DEVICE_ID = os.environ.get('DEVICE_ID')
DEVICE_PW = os.environ.get('DEVICE_PW')


@camera_route.route('/capture', methods=['POST'])
def img_capture():
    logger.info('Capture with camera')
    try:
        data = request.get_json()
        project = data.get('project')
        target = data.get('target')
        device = data.get('device')
        label = data.get('label')
        debug = data.get('debug')

        # skip integrity check if debugging
        if not debug:
            pid = db.session.query(Project).filter_by(name=project).one()
            tid = db.session.query(Target) \
                .filter_by(project=pid.id) \
                .filter_by(name=target).one()
            did = db.session.query(Device).filter_by(serial=device).one()
            task_id = cv_task.capture(header=f'{pid.shorthand}_{tid.name}',
                                      params={'target': tid.id,
                                              'device': did.id,
                                              'label': label})
        else:
            task_id = cv_task.capture(header=f'{project}_{target}',
                                      params={'target': None,
                                              'device': None,
                                              'label': None})
        return jsonify(task_id)
    # TODO
    # 각 DB exception 에 따라 예외처리 세분화
    except Exception as e:
        logger.error(e)
        traceback.print_stack()
        traceback.print_exc()
        return jsonify({'message': 'Failed to capture'}), 200


@camera_route.route('/timelapse', methods=['POST'])
def img_timelapse():
    logger.info('Start timelapse')
    try:
        data = request.get_json()
        project = data.get('project')
        target = data.get('target')
        device = data.get('device')
        label = data.get('label')
        interval = data.get('interval')
        expire_at = data.get('expire_at')
        debug = data.get('debug')

        # skip integrity check if debugging
        if not debug:
            pid = db.session.query(Project).filter_by(name=project).one()
            tid = db.session.query(Target) \
                .filter_by(project=pid.id) \
                .filter_by(name=target).one()
            did = db.session.query(Device).filter_by(serial=device).one()

        cv_task.periodic_capture(
            header=pid.shorthand,
            run_every=interval,
            expire_at=expire_at,
            params={
                'target': tid.id,
                'device': did.id,
                'label': label
            }
        )
        return jsonify({'message': f'Timelapse task for device {did.serial} registered'}), 200
    except Exception as e:
        # TODO
        # 각 DB exception 에 따라 예외처리 세분화
        logger.error(e)
        traceback.print_stack()
        traceback.print_exc()
        return jsonify({'message': 'Failed to start timelapse'}), 200


@camera_route.route('/range', methods=['GET'])
def get_position_range():
    logger.info('Fetch camera min/max range')


# /pos?x=n&y=n&z=n
@camera_route.route('/pos', methods=['GET'])
def update_position():
    logger.info('Update absolute camera position')
    x = request.args.get('x')
    y = request.args.get('y')
    z = request.args.get('z')

    logger.info('newpos: ', {"x": x, "y": y, "z": z})
    headers = {
        'Authorization': 'Digest username="admin", realm="IP Camera HTTP server", nonce="003E6CRqNuT25eRkajM09uTl9nM09uTl9nMz5OX25PZz==", uri="/isp/appispmu.cgi?btOK=submit&i_mt_dirx=3000&i_mt_diry=2206&i_mt_dirz=0", algorithm=MD5, response="c9a1e41244449a3f2477f4cca03c97b0", opaque="5ccc069c403ebaf9f0171e9517f40e41", qop=auth, nc=00000026, cnonce="e05ebfb1f30eace8"'
    }
    resp = requests.get(
        f'http://{DEVICE_IP}/isp/appispmu.cgi?btOK=submit&i_mt_dirx={x}&i_mt_diry={y}&i_mt_dirz={z}',
        headers=headers
    )
    # logger.info(resp.text)
    if resp.status_code == 200:
        return jsonify({
            'message': 'Successfully updated camera position.',
            'result': {"x": x, "y": y, "z": z}
        }), 200
    else:
        return jsonify({
            'message': 'Cannot connect to device'
        }), 404


# /pos_offset?x=n&y=n&z=n
@camera_route.route('/pos_offset', methods=['GET'])
def offset_position():
    logger.info('Update relative camera position')
    x = request.args.get('x')
    y = request.args.get('y')
    z = request.args.get('z')

    logger.info('offset: ' + str({"x": x, "y": y, "z": z}))
    # headers = {
    #    'Authorization': 'Digest username="admin", realm="IP Camera HTTP server", nonce="003E6CRqNuT25eRkajM09uTl9nM09uTl9nMz5OX25PZz==", uri="/isp/appispmu.cgi?btOK=submit&i_mt_dirx=3000&i_mt_diry=2206&i_mt_dirz=0", algorithm=MD5, response="c9a1e41244449a3f2477f4cca03c97b0", opaque="5ccc069c403ebaf9f0171e9517f40e41", qop=auth, nc=00000026, cnonce="e05ebfb1f30eace8"'
    # }
    resp = requests.get(
        f'http://{DEVICE_IP}/isp/appispmu.cgi?btOK=submit&i_mt_incx={x}&i_mt_incy={y}&i_mt_incz={z}',
        auth=HTTPDigestAuth(DEVICE_ID, DEVICE_PW)
    )
    logger.info(resp.text)
    if resp.status_code == 200:
        return jsonify({
            'message': 'Successfully updated camera position.',
            'result': {"x": x, "y": y, "z": z}
        }), 200
    else:
        return jsonify({
            'message': 'Cannot connect to device'
        }), 404


# /focus?value=n
@camera_route.route('/focus', methods=['GET'])
def update_focus():
    logger.info('Update camera focus')
    newfocus = request.args.get('value')
    logger.info(f'newfocus: {newfocus}')
    resp = requests.get(f'http://{DEVICE_IP}/isp/appispmu.cgi?i_c1_dirfcs={newfocus}&btOK=move')
    if resp.status_code == 200:
        return jsonify({
            'message': 'Successfully updated camera focus.',
            'result': newfocus
        }), 200
    else:
        return jsonify({
            'message': 'Cannot connect to device'
        }), 404


@camera_route.route('/repeat/<x>/<y>/<delay>', methods=['GET'])
def repeat(x, y, delay):
    import time
    for i in range(10):
        requests.get(
            f'http://{DEVICE_IP}/isp/appispmu.cgi?btOK=submit&i_mt_incx={x}&i_mt_incy={y}&i_mt_incz=0',
            auth=HTTPDigestAuth(DEVICE_ID, DEVICE_PW)
        )
        time.sleep(float(delay))
    return jsonify({'message': 'Success', }), 200
