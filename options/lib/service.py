"""
Module for the service
"""

# pylint: disable=no-self-use

import flask
import flask_restful


def build():
    """
    Builds the Flask App
    """

    app = flask.Flask("cnc-forge-options")
    app.api = flask_restful.Api(app)

    app.api.add_resource(Health, '/health')
    app.api.add_resource(Simple, '/simple')
    app.api.add_resource(Complex, '/complex')
    app.api.add_resource(Basic, '/basic')
    app.api.add_resource(Token, '/token')

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


class Simple(flask_restful.Resource):
    """
    Class for a simple API call
    """

    def get(self):
        """
        Just return people, stuff, things
        """
        return [
            "people",
            "stuff",
            "things"
        ]


class Complex(flask_restful.Resource):
    """
    Class for a complex API call
    """

    def get(self):
        """
        Just return fruit
        """
        return {
            "fruits": [
                {
                    "id": 1,
                    "name": "apple",
                    "meta": {
                        "fancy": "Apple"
                    }
                },
                {
                    "id": 2,
                    "name": "pear",
                    "meta": {
                        "fancy": "Pear"
                    }
                },
                {
                    "id": 3,
                    "name": "orange",
                    "meta": {
                        "fancy": "Orange"
                    }
                }
            ]
        }


class Basic(flask_restful.Resource):
    """
    Class for a basic auth API call
    """

    def get(self):
        """
        Make sure the u/p is right
        """

        if flask.request.headers.get("Authorization") != "Basic bXk6c2VsZg==":
            return {"message": "Unauthorized"}, 401

        return [
            "bass",
            "how",
            "low"
        ]


class Token(flask_restful.Resource):
    """
    Class for a token auth API call
    """

    def get(self):
        """
        Make sure the token is right
        """

        if flask.request.headers.get("Authorization") != "Bearer funspot":
            return {"message": "Unauthorized"}, 401

        return [
            "galaga",
            "pacman",
            "defender"
        ]
