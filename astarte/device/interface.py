# Copyright 2020-2021 SECO Mind S.r.l.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Tuple
from astarte.device.mapping import Mapping
from datetime import datetime
from re import sub, match

DEVICE = "device"
SERVER = "server"


class Interface:
    """
    Class that represent an Interface definition

    Interfaces are a core concept of Astarte which defines how data is exchanged between Astarte and its peers.
    They are not to be intended as OOP interfaces, but rather as the following definition:

    In Astarte each interface has an owner, can represent either a continuous data stream or a snapshot of a set
    of properties, and can be either aggregated into an object or be an independent set of individual members.

    Attributes
    ----------
        name: str
            Interface name
        version_major: int
            Interface version major number
        version_minor: int
            Interface version minor number
        type: str
            Interface type
        ownership: str
            Interface ownership
        aggregation: str
            Interface aggregation policy
        mappings: Mapping
            Interface mapping list
    """

    def __init__(self, interface_definition: dict):
        """
        Parameters
        ----------
        interface_definition: dict
            An Astarte Interface definition in the form of a Python dictionary. Usually obtained by using json.loads on
            an Interface file.
        """
        self.name = interface_definition["interface_name"]
        self.version_major = interface_definition["version_major"]
        self.version_minor = interface_definition["version_minor"]
        self.type = interface_definition["type"]
        self.ownership = "device"
        if "ownership" in interface_definition:
            self.ownership = interface_definition["ownership"]
        self.aggregation = ""
        if "aggregation" in interface_definition:
            self.aggregation = interface_definition["aggregation"]
        self.mappings: dict = {}
        for mapping_definition in interface_definition["mappings"]:
            mapping = Mapping(mapping_definition, self.type)
            self.mappings[mapping.endpoint] = mapping

    def is_aggregation_object(self):
        """
        Check if the current Interface is a datastream with aggregation object
        Returns
        -------
        bool
            True if aggregation: object
        """
        return self.aggregation == "object"

    def is_server_owned(self):
        """
        Check the Interface ownership
        Returns
        -------
        bool
            True if ownership: server
        """
        return self.ownership == "server"

    def get_mapping(self, endpoint) -> Mapping:
        """
        Retrieve the Mapping with the given endpoint from the Interface
        Parameters
        ----------
        endpoint: str
            The Mapping endpoint

        Returns
        -------
        Mapping or None
            The Mapping if found, None otherwise
        """
        for path, mapping in self.mappings.items():
            regex = sub(r'%{\w+}', r'.+', path)
            if match(regex + "$", endpoint):
                return mapping

    def validate(self, path: str, payload, timestamp: datetime) -> Tuple[bool, str]:
        """
        Interface Data validation

        Parameters
        ----------
        path: str
            Data endpoint in interface
        payload: object
            Data to validate
        timestamp: datetime or None
            Timestamp associated to the payload

        Returns
        -------
        success: bool
            Success of the validation operation
        msg: str
            Error message if success is False
        """
        # Check the interface has device ownership
        if self.ownership != DEVICE:
            return False, f"The interface {self.name} is not owned by the device "
        if not self.is_aggregation_object():
            # Check the validity of the path
            mapping = self.get_mapping(path)
            if mapping:
                return mapping.validate(payload, timestamp)

            return False, f"Path {path} not in the {self.name} interface."
        else:
            if not isinstance(payload, dict):
                return False, f"The interface {self.name} is aggregate, but the payload is not a dictionary"

            # Validate all paths
            for k, v in payload.items():
                mapping = self.get_mapping(f"{path}/{k}")
                if mapping:
                    result, errormsg = mapping.validate(v, timestamp)
                    if not result:
                        return result, errormsg
                else:
                    return False, f"Path {path} not in the {self.name} interface."

            # Check all elements are present
            for mapping in self.mappings:
                endpoint = mapping[len(path + "/"):]
                if endpoint not in payload:
                    return False, f"Path {mapping} has no value in {self.name} interface."
            return True, ""
