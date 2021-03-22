"""
Module for the service
"""

# pylint: disable=no-self-use

import os
import time
import copy
import glob
import json

import yaml
import redis

import flask
import flask_restful

import jinja2
import opengui

FIELDS = [
    {
        "name": "forge",
        "description": "what to craft from",
        "readonly": True
    },
    {
        "name": "craft",
        "description": "name of what to craft, used for repos, branches, change requests",
        "validation": r'^[a-z][a-z0-9\-]{1,46}$',
        "required": True,
        "trigger": True
    }
]

RESERVED = [
    "forge",
    "craft",
    "code",
    "cnc"
]

def build():
    """
    Builds the Flask App
    """

    app = flask.Flask("cnc-forge-api")
    app.api = flask_restful.Api(app)

    with open("/opt/service/secret/redis.json", "r") as redis_file:
        app.redis = redis.Redis(charset="utf-8", decode_responses=True, **json.loads(redis_file.read()))

    app.api.add_resource(Health, '/health')
    app.api.add_resource(Forge, '/forge', '/forge/<id>')
    app.api.add_resource(CnC, '/cnc', '/cnc/<id>')

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
            if forge_path.split("/")[-1] not in ["fields.yaml", "values.yaml"]:
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

    @classmethod
    def list(cls):
        """
        Returns the list of forges with descriptions
        """

        forges = cls.forges()

        return {"forges": [{"id": id, "description": forges[id]} for id in sorted(forges.keys())]}

    @classmethod
    def retrieve(cls, id):
        """
        Return a single forge
        """

        forges = cls.forges()

        if id not in forges:
            return {"message": f"forge '{id}' not found"}, 404

        forge = cls.forge(id)

        return {"forge": forge, "yaml": yaml.safe_dump(forge, default_flow_style=False)}

    def get(self, id=None):
        """
        GET method handling
        """

        if id is None:
            return self.list()

        return self.retrieve(id)


class CnC(flask_restful.Resource):
    """
    Class of actions to force code and/or chagnes from Forge's.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = jinja2.Environment(keep_trailing_newline=True)
        self.env.globals.update(port=self.port)

    @staticmethod
    def port(name):
        """
        Calculate a port vsalue based of a name
        """

        words = name.upper().split('-', 1)

        if len(words) == 1:
            words.append(words[0][1])

        return int(f"{ord(words[0][0])}{ord(words[1][0])}")

    def values(self, fields):
        """
        Gets the current values from the fields so far
        """

        values = {}

        for field in fields:
            if field.value is None and field.default is not None:
                values[field.name] = field.default
            else:
                values[field.name] = field.value

        return values

    def satisfied(self, fields, field, values):
        """
        Determines with the criteria for a field are satisfied
        """

        requires = field.get("requires", [])

        if isinstance(requires, str):
            requires = [requires]

        for require in requires:
            if require not in fields or not fields[require].validate(store=False):
                return False

        if "condition" in field and self.env.from_string(field["condition"]).render(**values) != "True":
            return False

        return True

    def field(self, fields, field):
        """
        Adds a field if requires and conditions are satsified
        """

        values = self.values(fields)

        if not self.satisfied(fields, field, values):
            if field["name"] in fields.values:
                del fields.values[field["name"]]
            return

        default = field.get("default")

        if isinstance(default, str):
            default = self.env.from_string(field["default"]).render(**values)

        fields.append({**field, "default": default})

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

        if os.path.exists("/opt/service/forge/fields.yaml"):
            with open("/opt/service/forge/fields.yaml", "r") as fields_file:
                fields.extend(yaml.safe_load(fields_file).get("fields", []))

        for field in forge.get("input", {}).get("fields", []):
            if field["name"] in RESERVED:
                raise Exception(f"field name '{field['name']}' is reserved")
            self.field(fields, field)

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

        cnc = copy.deepcopy(forge)

        cnc["values"] = {}

        if os.path.exists("/opt/service/forge/values.yaml"):
            with open("/opt/service/forge/values.yaml", "r") as values_file:
                cnc["values"].update(yaml.safe_load(values_file).get("values", {}))

        cnc["test"] = flask.request.json.get("test", False)
        cnc["values"].update({field.name: field.value for field in fields})
        cnc["values"]["code"] = cnc["values"]["craft"].replace('-', '_')
        cnc["status"] = "Created"

        cnc["id"] = f"{cnc['values']['craft']}-{cnc['values']['forge']}-{int(time.time())}"

        cnc["values"]["cnc"] = cnc["id"]

        flask.current_app.redis.set(f"/cnc/{cnc['id']}", json.dumps(cnc), ex=86400)

        return {"cnc": cnc}, 202

    @staticmethod
    def list():
        """
        Returns the list of tasks
        """

        return {"cncs": [{"id": id.split("/")[-1]} for id in sorted(flask.current_app.redis.keys("/cnc/*"))]}

    @staticmethod
    def retrieve(id):
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

        return self.retrieve(id)

    def patch(self, id):
        """
        PATCH method handling (just retries)
        """

        retrieved = self.retrieve(id)

        if "cnc" not in retrieved:
            return retrieved

        cnc = retrieved["cnc"]

        cnc["status"] = "Retry"

        if "traceback" in cnc:
            del cnc["traceback"]

        if "content" in cnc:
            del cnc["content"]

        flask.current_app.redis.set(f"/cnc/{id}", json.dumps(cnc), ex=86400)

        return {"cnc": cnc, "yaml": yaml.safe_dump(cnc, default_flow_style=False)}, 201

    def delete(self, id):
        """
        PATCH method handling (just retries)
        """

        retrieved = self.retrieve(id)

        if "cnc" not in retrieved:
            return retrieved

        flask.current_app.redis.delete(f"/cnc/{id}")

        return {"deleted": 1}, 201
