"""
Module for CnC
"""

# pylint: disable=too-many-public-methods,inconsistent-return-statements

import os
import glob
import json
import yaml
import shutil
import fnmatch

import jinja2
import overscore
import yaes

import github

class CnC:
    """
    Class that craft the code and changes
    """

    def __init__(self, data):
        """
        Store the daemon
        """

        self.data = data
        self.engine = yaes.Engine(jinja2.Environment(keep_trailing_newline=True))

    @staticmethod
    def exclude(content):
        """
        Exclude content from being copied from source to destination based on pattern
        """

        # Check override to include no matter what first

        for pattern in content['include']:
            if fnmatch.fnmatch(content['source'], pattern):
                return False

        # Now exclude

        for pattern in content['exclude']:
            if fnmatch.fnmatch(content['source'], pattern):
                return True

        return False

    @staticmethod
    def preserve(content):
        """
        Preserve content as is without transformation based on pattern
        """

        # Check override first to transform no matter what

        for pattern in content['transform']:
            if fnmatch.fnmatch(content['source'], pattern):
                return False

        # Now preserve

        for pattern in content['preserve']:
            if fnmatch.fnmatch(content['source'], pattern):
                return True

        return False

    def base(self):
        """
        Gets the base directory for the current cnc
        """
        return f"/opt/service/cnc/{self.data['id']}"

    def relative(self, path):
        """
        Gets the relative path based on base and whether source or destnation
        """
        return path.split(self.base(), 1)[-1].split("/", 2)[-1]

    def source(self, content, path=False):
        """
        Retrieves the content of a source file
        """

        if isinstance(content['source'], dict):
            return content['source']['value']

        source = os.path.abspath(f"{self.base()}/source/{content['source']}")

        if not source.startswith(f"{self.base()}/source"):
            raise Exception(f"invalid path: {source}")

        if path:
            return source

        with open(source, "r") as source_file:
            return source_file.read()

    def destination(self, content, data=None, path=False):
        """
        Retrieve or store the content of a destination file
        """

        destination = os.path.abspath(f"{self.base()}/destination/{content['destination']}")

        if not destination.startswith(f"{self.base()}/destination"):
            raise Exception(f"invalid path: {destination}")

        if path:
            return destination

        if not content.get("replace", True) and os.path.exists(destination):
            return

        if data is None:
            with open(destination, "r") as destination_file:
                return destination_file.read()

        with open(destination, "w") as destination_file:
            return destination_file.write(data)

    def copy(self, content):
        """
        Copies the content of source to desintation unchanged
        """

        source = self.source(content, path=True)
        destination = self.destination(content, path=True)

        if not content.get("replace", True) and os.path.exists(destination):
            return

        shutil.copy(source, destination)

    def remove(self, content):
        """
        Removes the content of desintation
        """

        destination = self.destination(content, path=True)

        if os.path.isdir(destination):
            shutil.rmtree(destination)
            return

        os.remove(destination)

    @staticmethod
    def text(source, destination, location, remove):
        """
        Inserts destination into source at location if not present
        """

        if remove:

            if source not in destination:
                return destination

            if isinstance(location, bool) and location:
                return "".join(destination.split(source))

            if f"cnc-forge: {location}" in destination:

                if source[-1] != "\n":
                    source = f"{source}\n"

                sections = destination.split(f"cnc-forge: {location}")
                sections[0] = "".join(sections[0].split(source))
                return f"cnc-forge: {location}".join(sections)


        if source in destination:
            return destination

        if isinstance(location, bool) and location:
            return destination + source

        if source[-1] == "\n":
            source = source[:-1]

        lines = []

        for line in destination.split("\n"):
            if f"cnc-forge: {location}" in line:
                lines.append(source)
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def json(source, destination, location, remove):
        """
        Inserts destination into source at location if not present
        """

        source = json.loads(source)
        destination = json.loads(destination)

        value = overscore.get(destination, location)

        if source not in value and not remove:
            value.append(source)

        if source in value and remove:
            value.remove(source)

        return json.dumps(destination, indent=4) + "\n"

    @staticmethod
    def yaml(source, destination, location, remove):
        """
        Inserts destination into source at location if not present
        """

        source = yaml.safe_load(source)
        destination = yaml.safe_load(destination)

        value = overscore.get(destination, location)

        if source not in value and not remove:
            value.append(source)

        if source in value and remove:
            value.remove(source)

        return yaml.safe_dump(destination, default_flow_style=False)

    def mode(self, content):
        """
        Have the desination mode match the source mode
        """

        os.chmod(
            self.destination(content, path=True),
            os.stat(self.source(content, path=True)).st_mode
        )

    def directory(self, content, values):
        """
        Craft a directory
        """

        # Iterate though the items found as long as we're not .git

        if content["source"].split("/")[-1] != ".git":
            for item in os.listdir(self.source(content, path=True)):
                self.craft({**content,
                    "source": f"{content['source']}/{item}" if content['source'] else item,
                    "destination": f"{content['destination']}/{item}" if content['destination'] else item
                }, values)

    def file(self, content, values):
        """
        Craft a file
        """

        # If we're preserving, just copy, else load source and transformation to destination

        remove = content.get("remove", False)

        if remove and "text" not in content and "json" not in content and "yaml" not in content:
            self.remove(content)
            return

        if self.preserve(content):
            self.copy(content)
            return

        source = self.engine.transform(self.source(content), values)

        # See if we're injecting anywhere, else just overwrite

        mode = False

        if "text" in content:
            destination = self.text(
                source, self.destination(content),
                self.engine.transform(content["text"], values) if isinstance(content["text"], str) else content["text"],
                remove
            )
        elif "json" in content:
            destination = self.json(source, self.destination(content), self.engine.transform(content["json"], values), remove)
        elif "yaml" in content:
            destination = self.yaml(source, self.destination(content), self.engine.transform(content["yaml"], values), remove)
        else:
            mode = isinstance(content['source'], str)
            destination = source

        self.destination(content, destination)

        if mode:
            self.mode(content)

    def craft(self, content, values):
        """
        Craft changes, the actual work of creating desitnations from sources
        """

        # Skip if we're to exclude

        if self.exclude(content):
            return

        print(content)

        # Store the last content here in case there's an error

        self.data['content'] = content

        # Make sure the directory exists

        if not os.path.exists(os.path.dirname(self.destination(content, path=True))):
            os.makedirs(os.path.dirname(self.destination(content, path=True)))

        # If source is a directory

        if isinstance(content['source'], str) and os.path.isdir(self.source(content, path=True)):

            self.directory(content, values)

        else:

            self.file(content, values)

        # It worked, so delete the content

        if "content" in self.data:
            del self.data['content']

    def content(self, content, values):
        """
        Processes a content
        """

        # Transform exclude, include, preserve, and transforma and ensure they're lists

        for collection in ["exclude", "include", "preserve", "transform"]:
            content[collection] = self.engine.transform(content.get(collection, []), values)
            if isinstance(content[collection], str):
                content[collection] = [content[collection]]
            content[collection] = [pattern[:-1] if pattern[-1] == "/" else pattern for pattern in content[collection]]

        # Transform the source on templating, using destination if it doesn't exist for remove

        content["source"] = self.engine.transform(content.get("source", content.get("destination")), values)

        if isinstance(content["source"], dict):

            sources = [content["source"]]

        else:

            if content["source"] == "/":
                sources = [""]
            else:

                path = self.source(content, path=True)

                if '*' in path or os.path.isdir(path):
                    sources = [self.relative(source) for source in glob.glob(path)]
                else:
                    sources = [self.relative(path)]

        # Go through the source as glob, transforming destination accordingly, assuming source if missing

        for source in sources:
            self.craft({**content,
                "source": source,
                "destination": self.engine.transform(content.get("destination", source), values)
            }, values)

    def change(self, change, values):
        """
        Process a change block
        """

        # If there's a github block, use it to pull the code

        controller = None

        if "github" in change:
            change["github"] = self.engine.transform(change["github"], values)
            controller = github.GitHub(self, change["github"])

        if controller is not None:
            controller.change()

        # Go through each content, which it'll check conditions, transpose, and iterate

        for content, content_values in self.engine.each(change["content"], values):
            self.content({"remove": change["remove"], **content}, content_values)

    def code(self, code, values):
        """
        Process a code block
        """

        # If there's a github block, use it to checkout the code

        controller = None

        if "github" in code:
            code["github"] = self.engine.transform(code["github"], values)
            controller = github.GitHub(self, code["github"])

        controller.code()

        # Go through each change, which it'll check conditions, transpose, and iterate

        for change, change_values in self.engine.each(code["change"], values):
            self.change({"remove": code["remove"], **change}, change_values)

        # If there's a github block, use it to commit the code

        controller.commit()

    def link(self, link):
        """
        Adds a link to display
        """

        self.data.setdefault("links", [])

        if link not in self.data["links"]:
            self.data["links"].append(link)

    def process(self):
        """
        Process a CnC
        """

        # Store the outputs untransformed code to root so
        # We don't change what's originally there

        self.data["code"] = self.data["output"]["code"]

        # Wipe and create the directory for this process

        shutil.rmtree(self.base(), ignore_errors=True)
        os.makedirs(self.base())

        # Go through each code, which it'll check conditions, transpose, and iterate

        for code, code_values in self.engine.each(self.data["code"], self.data["values"]):
            self.code({"remove": self.data["action"] == "remove", **code}, code_values)

        # If we're here we were successful and can clean up if we're not testing

        self.data["status"] = "Completed"

        if self.data["action"] == "test":
            shutil.rmtree(f"{self.base()}/source", ignore_errors=True)
        else:
            shutil.rmtree(self.base(), ignore_errors=True)
