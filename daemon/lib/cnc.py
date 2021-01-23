"""
Module for CnC
"""

import os
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

    def iterate(self, items, values):
        """
        Iterate through items, checking condition
        Eventually we will emit values too
        """

        for item in items:
            if "condition" not in item or self.transform(item["condition"], values):
                yield item, values

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

        # IF source is a directory

        if os.path.isdir(f"/opt/service/cnc/{self.data['id']}/source/{content['source']}"):

            # Make sure it exists on destination

            if not os.path.exists(f"/opt/service/cnc/{self.data['id']}/destination/{content['source']}"):
                os.makedirs(f"/opt/service/cnc/{self.data['id']}/destination/{content['source']}")

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
            self.destination(content, self.transform(self.source(content), self.data["values"]))

        # It worked, so delete the content

        del self.data['content']

    def content(self, code, change, content, values):
        """
        Processes a content
        """

        # Transform the source and destination

        content["source"] = self.transform(content["source"], values)
        content["destination"] = self.transform(content["destination"], values)

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

        # Iterate through content, which it'll check conditions

        for content, content_values in self.iterate(change["content"], values):
            self.content(code, change, content, content_values)

    def code(self, code, values):
        """
        Process a code block
        """

        # If there's a github block, use it to checkout the code

        if "github" in code:
            code["github"] = self.transform(code["github"], values)
            self.daemon.github.clone(self.data, code, code["github"])

        # Iterate through changes, which it'll check conditions

        for change, change_values in self.iterate(code["change"], values):
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

        # Iterate through changes, which it'll check conditions

        for code, code_values in self.iterate(self.data["code"], self.data["values"]):
            self.code(code, code_values)

        # If we're here we were successful and can clean up

        self.data["status"] = "Completed"
        shutil.rmtree(f"/opt/service/cnc/{self.data['id']}")
