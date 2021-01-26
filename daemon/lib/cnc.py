"""
Module for CnC
"""

import os
import copy
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

        self.daemon = daemon

    def transform(self, template, values):
        """
        Transform whatever's sent, either str or recurse through
        """

        if isinstance(template, str):
            return self.daemon.env.from_string(template).render(**values)
        if isinstance(template, list):
            return [self.transform(item, values) for item in template]
        if isinstance(template, dict):
            return {key: self.transform(item, values) for key, item in template.items()}

    def transpose(self, block, values):
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

        for block in blocks:
            for iterate_values in self.iterate(block, values):
                block_values = {**values, **iterate_values}
                if self.condition(block, block_values):
                    yield copy.deepcopy(block), block_values

    def exclude(self, content):
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

    def preserve(self, content):
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

    def source(self, content):
        """
        Retrieves the content of a source file
        """

        with open(f"/opt/service/cnc/{self.data['id']}/source/{content['source']}", "r") as load_file:
            return load_file.read()

    def destination(self, content, data=None):
        """
        Retrieve or store the content of a destination file
        """

        if data is not None:
            with open(f"/opt/service/cnc/{self.data['id']}/destination/{content['destination']}", "w") as destination_file:
                destination_file.write(data)
        else:
            with open(f"/opt/service/cnc/{self.data['id']}/destination/{content['destination']}", "r") as destination_file:
                return destination_file.read()

    def copy(self, content):
        """
        Copies the content of source to desintation unchanged
        """

        shutil.copy(
            f"/opt/service/cnc/{self.data['id']}/source/{content['source']}",
            f"/opt/service/cnc/{self.data['id']}/destination/{content['destination']}"
        )

    def text(self, source, destination, location):
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
            f"/opt/service/cnc/{self.data['id']}/destination/{content['destination']}",
            os.stat(f"/opt/service/cnc/{self.data['id']}/source/{content['source']}").st_mode
        )

    def craft(self, code, change, content, values):
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

        if not os.path.exists(os.path.dirname(f"/opt/service/cnc/{self.data['id']}/destination/{content['destination']}")):
            os.makedirs(os.path.dirname(f"/opt/service/cnc/{self.data['id']}/destination/{content['destination']}"))

        # If source is a directory

        if os.path.isdir(f"/opt/service/cnc/{self.data['id']}/source/{content['source']}"):

            # Iterate though the items found

            for item in os.listdir(f"/opt/service/cnc/{self.data['id']}/source/{content['source']}"):
                self.craft(code, change, {
                    "source": f"{content['source']}/{item}",
                    "destination": f"{content['destination']}/{item}",
                    "exclude": content['exclude'],
                    "include": content['include'],
                    "preserve": content['preserve'],
                    "transform": content['transform']
                }, values)
            return

        # If we're preserving, jsut copy, else load source and transformation to destination

        if self.preserve(content):

            self.copy(content)

        else:

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

        # It worked, so delete the content

        del self.data['content']

    def content(self, code, change, content, values):
        """
        Processes a content
        """

        # Transform the source and destination

        content["source"] = self.transform(content["source"], values)
        content["destination"] = self.transform(content.get("destination", content["source"]), values)

        # Transform exclude, include, preserve, and transforma and ensure they're lists

        for collection in ["exclude", "include", "preserve", "transform"]:
            content[collection] = self.transform(content.get(collection, []), values)
            if isinstance(content[collection], str):
                content[collection] = [content[collection]]

        # Craft this content

        self.craft(code, change, content, values)

    def change(self, code, change, values):
        """
        Process a change block
        """

        # If there's a github block, use it to pull the code

        if "github" in change:
            change["github"] = self.transform(change["github"], values)
            self.daemon.github.change(self.data, code, change["github"])

        # Go through each content, which it'll check conditions, transpose, and iterate

        for content, content_values in self.each(change["content"], values):
            self.content(code, change, content, content_values)

    def code(self, code, values):
        """
        Process a code block
        """

        # If there's a github block, use it to checkout the code

        if "github" in code:
            code["github"] = self.transform(code["github"], values)
            self.daemon.github.clone(self.data, code, code["github"])

        # Go through each change, which it'll check conditions, transpose, and iterate

        for change, change_values in self.each(code["change"], values):
            self.change(code, change, change_values)

        # If there's a github block, use it to commit the code

        if "github" in code:
            self.daemon.github.commit(self.data, code, code["github"])

    def process(self, data):
        """
        Process a CnC
        """

        # Store the data

        self.data = data

        # Store the outputs untransformed code to root so
        # We don't change what's originally there

        self.data["code"] = self.data["output"]["code"]

        # Create the directory for this process, in case it dies and
        # we need to look at what's going on

        os.makedirs(f"/opt/service/cnc/{self.data['id']}", exist_ok=True)

        # Go through each code, which it'll check conditions, transpose, and iterate

        for code, code_values in self.each(self.data["code"], self.data["values"]):
            self.code(code, code_values)

        # If we're here we were successful and can clean up

        self.data["status"] = "Completed"
        shutil.rmtree(f"/opt/service/cnc/{self.data['id']}")
