# -*- coding: utf-8 -*-
from flask import request
from flask_classful import FlaskView
import uuid
from bson.json_util import dumps
import time
import logging
import pymongo

from katana.shared_utils.mongoUtils import mongoUtils


# Logging Parameters
logger = logging.getLogger(__name__)
file_handler = logging.handlers.RotatingFileHandler(
    'katana.log', maxBytes=10000, backupCount=5)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
stream_formatter = logging.Formatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(stream_formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class FunctionView(FlaskView):
    route_prefix = '/api/'
    req_fields = ["id", "gen", "func", "shared", "type", "location"]

    def index(self):
        """
        Returns a list of supported functions and their details,
        used by: `katana function ls`
        """
        data = mongoUtils.index("func")
        return_data = []
        for iservice in data:
            return_data.append(dict(
                _id=iservice['_id'],
                gen=(lambda x: "4G" if x == 4 else "5G")(iservice["gen"]),
                func=(lambda x: "EPC" if x == 0 else "xNB")(iservice["func"]),
                type=(lambda x: "Virtual" if x == 0 else "Physical")(
                    iservice["type"]),
                func_id=iservice['id'], loc=iservice["location"],
                created_at=iservice['created_at']))
        return dumps(return_data), 200

    def get(self, uuid):
        """
        Returns the details of specific function,
        used by: `katana function inspect [uuid]`
        """
        return dumps(mongoUtils.get("func", uuid)), 200

    def post(self):
        """
        Add a new supported function.
        The request must provide the network function details.
        used by: `katana func add -f [yaml file]`
        """
        new_uuid = str(uuid.uuid4())
        data = request.json
        data['_id'] = new_uuid
        data['created_at'] = time.time()  # unix epoch
        data["tenants"] = []

        for field in self.req_fields:
            try:
                _ = data[field]
            except KeyError:
                return f"Error: Required fields: {self.req_fields}", 400
        try:
            new_uuid = mongoUtils.add('func', data)
        except pymongo.errors.DuplicateKeyError:
            return f"Network Function with id {data['id']} already exists", 400
        return f"Created {new_uuid}", 201

    def delete(self, uuid):
        """
        Delete a specific network function.
        used by: `katana function rm [uuid]`
        """
        result = mongoUtils.get("func", uuid)
        if result:
            if len(result["tenants"]) > 0:
                return f"Error: Function is used by slices {result['tenants']}"
            mongoUtils.delete("func", uuid)
            return "Deleted Network Function {}".format(uuid), 200
        else:
            # if uuid is not found, return error
            return "Error: No such Network Function: {}".format(uuid), 404

    def put(self, uuid):
        """
        Add or update a new supported network function.
        The request must provide the service details.
        used by: `katana function update -f [yaml file]`
        """
        data = request.json
        data['_id'] = uuid
        old_data = mongoUtils.get("func", uuid)

        if old_data:
            data["created_at"] = old_data["created_at"]
            if len(old_data["tenants"]) > 0:
                return f"Error: Func is used by slices {old_data['tenants']}"
            mongoUtils.update("func", uuid, data)
            return f"Modified {uuid}", 200
        else:
            new_uuid = uuid
            data = request.json
            data['_id'] = new_uuid
            data['created_at'] = time.time()  # unix epoch
            data["tenants"] = []

            for field in self.req_fields:
                try:
                    _ = data[field]
                except KeyError:
                    return f"Error: Required fields: {self.req_fields}", 400
            try:
                new_uuid = mongoUtils.add('func', data)
            except pymongo.errors.DuplicateKeyError:
                return f"Function with id {data['id']} already exists", 400
            return f"Created {new_uuid}", 201
