"""
Module for the service
"""

# pylint: disable=no-self-use

import time
import glob
import json

import yaml
import redis

import flask
import flask_restful

import opengui

FIELDS = [
    {
        "name": "forge",
        "description": "What to craft",
        "readonly": True
    },
    {
        "name": "craft",
        "description": "Name of what to craft, used for repos, branches, change requests",
        "validation": '^[a-z0-9\-]{4,48}$',
        "trigger": True
    }
]

def build():
    """
    Builds the Flask App
    """

    app = flask.Flask("cnc-forge-api")
    api = flask_restful.Api(app)

    with open("/opt/service/secret/redis.json", "r") as redis_file:
        app.redis = redis.Redis(charset="utf-8", decode_responses=True, **json.loads(redis_file.read()))

    api.add_resource(Health, '/health')
    api.add_resource(Forge, '/forge', '/forge/<id>')
    api.add_resource(CnC, '/cnc', '/cnc/<id>')

    return app


class Health(flask_restful.Resource):
    """
    Class for Health checks
    """

    def get(self):
        """
        Just return ok
        """
        return {"message": "OK"}


class Forge(flask_restful.Resource):
    """
    Forge class for design patterns to cnc
    """

    @staticmethod
    def forges():
        """
        Gets all forges return as dict
        """

        forges = {}

        for forge_path in sorted(glob.glob("/opt/service/forge/*.yaml")):
            with open(forge_path, "r") as forge_file:
                forges[forge_path.split("/")[-1].split(".")[0]] = yaml.safe_load(forge_file)["description"]

        return forges

    @staticmethod
    def forge(id):
        """
        Gets a single forge and return as dict
        """

        with open(f"/opt/service/forge/{id}.yaml", "r") as forge_file:
            forge = yaml.safe_load(forge_file)

        forge["id"] = id

        return forge

    def list(self):
        """
        Returns the list of forges with descriptions
        """

        forges = self.forges()

        return {"forges": [{"id": id, "description": forges[id]} for id in sorted(forges.keys())]}

    def retrieve(self, id):
        """
        Return a single forge
        """

        forges = self.forges()

        if id not in forges:
            return {"message": f"forge '{id}' not found"}, 404

        forge = self.forge(id)

        return {"forge": forge, "yaml": yaml.safe_dump(forge, default_flow_style=False)}

    def get(self, id=None):
        """
        GET method handling
        """

        if id is None:
            return self.list()
        else:
            return self.retrieve(id)


class CnC(flask_restful.Resource):
    """
    Class of actions to force code and/or chagnes from Forge's.
    """

    def fields(self, forge, values):
        """
        Gets the dynamic fields
        """

        values["forge"] = forge['id']

        fields = opengui.Fields(
            values=values,
            fields=FIELDS,
            ready=True
        )

        fields["forge"].description = forge["description"]

        fields.extend(forge.get("input", {}).get("fields", []))

        if "generate" in forge.get("input", {}):
            module_name, method_name =  forge["input"]["generate"].rsplit(".", 1)
            module = __import__(f"forge.{module_name}")
            method = getattr(getattr(module, module_name), method_name)
            fields.extend(method(fields, values, forge) or [])

        return fields

    def options(self, id):
        """
        OPTIONS method handling
        """

        forges = Forge.forges()

        if id not in forges:
            return {"message": f"forge '{id}' not found"}, 404

        forge = Forge.forge(id)

        fields = self.fields(forge, (flask.request.json or {}).get("values", {}))

        fields.validate()

        return fields.to_dict(), 200

    def post(self, id):
        """
        POST method handling
        """

        forges = Forge.forges()

        if id not in forges:
            return {"message": f"forge '{id}' not found"}, 404

        forge = Forge.forge(id)

        fields = self.fields(forge, (flask.request.json or {}).get("values"))

        if not fields.validate():
            return fields.to_dict(), 400

        cnc = forge

        cnc["values"] = {field.name: field.value for field in fields}
        cnc["status"] = "Created"

        cnc["id"] = f"{cnc['values']['craft']}-{cnc['values']['forge']}-{int(time.time())}"

        flask.current_app.redis.set(f"/cnc/{cnc['id']}", json.dumps(cnc), ex=86400)

        return {"cnc": cnc}, 200

    def list(self):
        """
        Returns the list of tasks
        """

        return {"cncs": [{"id": id.split("/")[-1]} for id in sorted(flask.current_app.redis.keys("/cnc/*"))]}

    def retrieve(self, id):
        """
        Return a single task
        """

        cnc = flask.current_app.redis.get(f"/cnc/{id}")

        if not cnc:
            return {"message": f"cnc '{id}' not found"}, 404

        cnc = json.loads(cnc)

        return {"cnc": cnc, "yaml": yaml.safe_dump(cnc, default_flow_style=False)}

    def get(self, id=None):
        """
        GET method handling
        """

        if id is None:
            return self.list()
        else:
            return self.retrieve(id)

    def patch(self, id):
        """
        PATCH method handling (just retries)
        """

        cnc = self.retrieve(id)["cnc"]

        cnc["status"] = "Retry"

        if "traceback" in cnc:
            del cnc["traceback"]

        flask.current_app.redis.set(f"/cnc/{id}", json.dumps(cnc), ex=86400)

        return {"cnc": cnc, "yaml": yaml.safe_dump(cnc, default_flow_style=False)}, 200

    def delete(self, id):
        """
        PATCH method handling (just retries)
        """

        self.retrieve(id)

        flask.current_app.redis.delete(f"/cnc/{id}")

        return {"deleted": 1}, 200
