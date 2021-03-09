"""
Module for CnC
"""

# pylint: disable=too-many-public-methods

import os
import copy
import glob
import json
import yaml
import shutil
import fnmatch

class CnC:
    """
    Class that craft the code and changes
    """

    def __init__(self, daemon):
        """
        Store the daemon
        """

        self.data = None
        self.daemon = daemon

    def transform(self, template, values):
        """
        Transform whatever's sent, either str or recurse through
        """

        if isinstance(template, list):
            return [self.transform(item, values) for item in template]
        if isinstance(template, dict):
            return {key: self.transform(item, values) for key, item in template.items()}

        return self.daemon.env.from_string(template).render(**values)

    @staticmethod
    def transpose(block, values):
        """
        Transposes values
        """

        transpose = block.get("transpose", {})

        return {derivative: values[original] for derivative, original in transpose.items() if original in values}

    def iterate(self, block, values):
        """
        Iterates values with transposition
        """

        iterate_values = [self.transpose(block, values)]

        iterate = block.get("iterate", {})

        for one in sorted(iterate.keys()):
            many_values = []
            for many_value in iterate_values:
                for value in values[iterate[one]]:
                    many_values.append({**many_value, one: value})
            iterate_values = many_values

        return iterate_values

    def condition(self, block, values):
        """
        Evaludates condition in values
        """

        return "condition" not in block or self.transform(block["condition"], values) == "True"

    def each(self, blocks, values):
        """
        Go through blocks, checking condition
        Eventually we will emit values too
        """

        if isinstance(blocks, dict):
            blocks = [blocks]

        for block in blocks:
            for iterate_values in self.iterate(block, values):
                block_values = {**values, **iterate_values}
                if self.condition(block, block_values):
                    yield copy.deepcopy(block), block_values

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

        if data is None:
            with open(destination, "r") as destination_file:
                return destination_file.read()

        with open(destination, "w") as destination_file:
            return destination_file.write(data)

    def copy(self, content):
        """
        Copies the content of source to desintation unchanged
        """

        shutil.copy(
            self.source(content, path=True),
            self.destination(content, path=True)
        )

    @staticmethod
    def text(source, destination, location):
        """
        Inserts destination into source at location if not present
        """

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

    def value(self, value, location):
        """
        Recursively get location
        """

        if not location:
            return value

        if isinstance(location, str):
            location = location.split('.')

        place = location.pop(0)

        if place.isdigit() or (place[0] == '-' and place[1:].isidigit()):
            place = int(place)

        return self.value(value[place], location)

    def json(self, source, destination, location):
        """
        Inserts destination into source at location if not present
        """

        source = json.loads(source)
        destination = json.loads(destination)

        value = self.value(destination, location)

        if source not in value:
            value.append(source)

        return json.dumps(destination, indent=4)

    def yaml(self, source, destination, location):
        """
        Inserts destination into source at location if not present
        """

        source = yaml.safe_load(source)
        destination = yaml.safe_load(destination)

        value = self.value(destination, location)

        if source not in value:
            value.append(source)

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

        if self.preserve(content):
            self.copy(content)
            return

        source = self.transform(self.source(content), values)

        # See if we're injecting anywhere, else just overwrite

        mode = False

        if "text" in content:
            destination = self.text(source, self.destination(content), content["text"])
        elif "json" in content:
            destination = self.json(source, self.destination(content), content["json"])
        elif "yaml" in content:
            destination = self.yaml(source, self.destination(content), content["yaml"])
        else:
            mode = True
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

        if os.path.isdir(self.source(content, path=True)):

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
            content[collection] = self.transform(content.get(collection, []), values)
            if isinstance(content[collection], str):
                content[collection] = [content[collection]]
            content[collection] = [pattern[:-1] if pattern[-1] == "/" else pattern for pattern in content[collection]]


        # Transform the source on templating

        content["source"] = self.transform(content["source"], values)

        if content["source"] == "/":
            sources = [""]
        else:
            sources = [self.relative(source) for source in glob.glob(self.source(content, path=True))]

        # Go through the source as glob, transforming destination accordingly, assuming source if missing

        for source in sources:
            self.craft({**content,
                "source": source,
                "destination": self.transform(content.get("destination", source), values)
            }, values)

    def change(self, change, values):
        """
        Process a change block
        """

        # If there's a github block, use it to pull the code

        if "github" in change:
            change["github"] = self.transform(change["github"], values)
            self.daemon.github.change(self, change["github"])

        # Go through each content, which it'll check conditions, transpose, and iterate

        for content, content_values in self.each(change["content"], values):
            self.content(content, content_values)

    def code(self, code, values):
        """
        Process a code block
        """

        # If there's a github block, use it to checkout the code

        if "github" in code:
            code["github"] = self.transform(code["github"], values)
            self.daemon.github.clone(self, code["github"])

        # Go through each change, which it'll check conditions, transpose, and iterate

        for change, change_values in self.each(code["change"], values):
            self.change(change, change_values)

        # If there's a github block, use it to commit the code

        if "github" in code:
            self.daemon.github.commit(self, code["github"])

    def link(self, link):
        """
        Adds a link to display
        """

        self.data.setdefault("links", [])

        if link not in self.data["links"]:
            self.data["links"].append(link)

    def process(self, data):
        """
        Process a CnC
        """

        # Store the data

        self.data = data

        # Store the outputs untransformed code to root so
        # We don't change what's originally there

        self.data["code"] = self.data["output"]["code"]

        # Wipe and create the directory for this process

        shutil.rmtree(self.base(), ignore_errors=True)
        os.makedirs(self.base())

        # Go through each code, which it'll check conditions, transpose, and iterate

        for code, code_values in self.each(self.data["code"], self.data["values"]):
            self.code(code, code_values)

        # If we're here we were successful and can clean up if we're not testing

        self.data["status"] = "Completed"

        if self.data["test"]:
            shutil.rmtree(f"{self.base()}/source", ignore_errors=True)
        else:
            shutil.rmtree(self.base(), ignore_errors=True)
