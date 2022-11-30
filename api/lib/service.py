"""
Module for the service
"""

# pylint: disable=no-self-use,too-many-instance-attributes

import os
import time
import copy
import glob
import json

import yaml
import redis
import requests

import flask
import flask_restful

import jinja2
import opengui
import overscore
import yaes

FORGE = {
    "name": "forge",
    "description": "what to craft from",
    "readonly": True
}

CRAFT = {
    "name": "craft",
    "description": "name of what to craft, used for repos, branches, change requests",
    "validation": r'^[a-z][a-z0-9\-]{1,46}$',
    "required": True,
    "trigger": True
}

RESERVED = [
    "forge",
    "code",
    "cnc"
]

class Options:
    """
    Class for retrieving options remotely
    """

    creds = {}

    @classmethod
    def config(cls):
        """
        Sets up creds
        """

        for creds in glob.glob("/opt/service/secret/options_*.json"):

            name = creds.split("/options_")[-1].split(".")[0]

            with open(creds, "r") as creds_file:
                cls.creds[name] = json.load(creds_file)
                cls.creds[name].setdefault("verify", True)

    session = None
    method = None
    url = None
    verify = None
    path = None
    params = None
    body = None
    results = None
    option = None
    title = None

    def __init__(self, data):

        self.session = requests.Session()

        creds = copy.deepcopy(self.creds.get(data.get("creds", "default"), {"verify": True}))
        creds.update(data)

        creds.setdefault("method", "GET")
        creds.setdefault("path", "")
        creds.setdefault("headers", {})
        creds.setdefault("params", {})
        creds.setdefault("body", {})
        creds.setdefault("results", "")
        creds.setdefault("option", "")
        creds.setdefault("title", "")

        self.url = creds["url"]
        self.verify = creds["verify"]

        self.method = creds["method"]
        self.path = creds["path"]
        self.params = creds["params"]
        self.body = creds["body"]
        self.results = creds["results"]
        self.option = creds["option"]
        self.title = creds["title"]

        if "username" in creds:
            self.session.auth = (creds["username"], creds["password"])

        if "token" in creds:
            self.session.headers["Authorization"] = f"Bearer {creds['token']}"

        if creds["headers"]:
            self.session.headers.update(creds["headers"])

    def retrieve(self, extra):
        """
        Retrieves the options and adds to extra
        """

        url = f"{self.url}/{self.path}" if self.path else self.url

        results = self.session.request(self.method, url, verify=self.verify, params=self.params, json=self.body).json()

        if self.results:
            results = overscore.get(results, self.results)

        extra["options"] = []

        if self.title:
            extra["titles"] = {}

        for result in results:
            if self.option:
                option = overscore.get(result, self.option)
                extra["options"].append(option)
                if self.title:
                    title = overscore.get(result, self.title)
                    extra["titles"][option] = title
            else:
                extra["options"].append(result)


def build():
    """
    Builds the Flask App
    """

    app = flask.Flask("cnc-forge-api")
    app.api = flask_restful.Api(app)

    app.redis = redis.Redis(host="redis.cnc-forge", charset="utf-8", decode_responses=True)

    app.api.add_resource(Health, '/health')
    app.api.add_resource(Forge, '/forge', '/forge/<id>')
    app.api.add_resource(CnC, '/cnc', '/cnc/<id>')

    Options.config()

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
        env = jinja2.Environment(keep_trailing_newline=True)
        env.globals.update(port=self.port)
        self.engine = yaes.Engine(env)

    @staticmethod
    def port(name):
        """
        Calculate a port value based of a name
        """

        words = name.upper().split('-', 1)

        if len(words) == 1:
            words.append(words[0][1])

        return int(f"{ord(words[0][0])}{ord(words[1][0])}")

    def field(self, fields, field, values):
        """
        Adds a field if requires and conditions are satsified
        """

        children = None

        if "fields" in field:

            children = opengui.Fields()

            for child, child_values in self.engine.each(field["fields"], values):
                self.field(children, child, child_values)

            del field["fields"]

        field = self.engine.transform(field, values)

        if field["name"] in RESERVED:
            raise Exception(f"field name '{field['name']}' is reserved")

        if field["name"] not in fields:
            field.setdefault("default", None)

        extra = {}

        if isinstance(field.get("options"), dict):
            Options(field["options"]).retrieve(extra)

        fields.update({**field, **extra})

        fields[field['name']].fields = children

    def fields(self, forge, values):
        """
        Gets the dynamic fields
        """

        values["forge"] = forge['id']

        fields = [FORGE]

        if "craft" not in forge.get("input", {}):
            fields.append(CRAFT)

        if os.path.exists("/opt/service/forge/fields.yaml"):
            with open("/opt/service/forge/fields.yaml", "r") as fields_file:
                fields.extend(yaml.safe_load(fields_file).get("fields", []))

        fields = opengui.Fields(
            values=values,
            fields=fields,
            ready=True
        )

        fields["forge"].description = forge["description"]

        for field, each_values in self.engine.each(forge.get("input", {}).get("fields", []), values):
            self.field(fields, field, each_values)

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

        if "action" not in (flask.request.json or {}):
            return {"message": "missing action"}, 400

        fields = self.fields(forge, (flask.request.json or {}).get("values"))

        if not fields.validate():
            return fields.to_dict(), 400

        cnc = copy.deepcopy(forge)

        cnc["values"] = {}

        if os.path.exists("/opt/service/forge/values.yaml"):
            with open("/opt/service/forge/values.yaml", "r") as values_file:
                cnc["values"].update(yaml.safe_load(values_file).get("values", {}))

        cnc["action"] = flask.request.json["action"]
        cnc["values"].update({field.name: field.value for field in fields})

        craft = cnc["values"][forge["input"]["craft"] if "craft" in forge.get("input", {}) else "craft"]

        if isinstance(craft, list):
            craft = "-".join(craft)[:46]

        cnc["values"]["code"] = craft.replace('-', '_')
        cnc["status"] = "Created"

        cnc["id"] = f"{craft}-{cnc['values']['forge']}-{int(time.time())}"

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

        if flask.request.data and "yaml" in (flask.request.json or {}):
            cnc = yaml.safe_load(flask.request.json["yaml"])
        else:
            cnc = retrieved["cnc"]

        cnc["status"] = "Retry"

        for issue in ["error", "traceback", "content", "change", "code"]:
            if issue in cnc:
                del cnc[issue]

        if not flask.request.data or (flask.request.json or {}).get("save", True):
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
