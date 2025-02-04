from __future__ import annotations

import csv
import json
import uuid
from typing import Any, AnyStr, Callable, Tuple

from django.core.exceptions import ValidationError

from core.cached_queries import get_val_types
from core.models.core_tables import TypeDef


class Val:
    val_type: TypeDef
    positions: dict[str, int] = {
        "text": 2,
        "array_text": 3,
        "int": 4,
        "array_int": 5,
        "num": 6,
        "array_num": 7,
        "blob": 8,
        "blob_array": 9,
        "bool": 10,
        "array_bool": 11,
    }

    def __init__(
        self,
        val_type: TypeDef | None,
        value: Any,
        unit: str,
        null: bool = False,
        raw_string: str = "",
    ):
        self.null = null
        self.unit: str | None = None
        if isinstance(value, str):
            if len(value) == 0:
                print(raw_string)
        if not self.null and val_type is not None:
            self.val_type = val_type
            if not isinstance(val_type, str):
                self.type_uuid = val_type.uuid
            else:
                val_type = self.validate_type(val_type)
            self.value = value
            if isinstance(self.value, str):
                self.value = self.convert_value()
            self.unit = unit
            self.str_value = raw_string
            # print(self.val_type.description, self.value, self.unit)
        else:
            self.value = None
            # self.val_type = None

    def to_db(self):
        if not self.null:
            string_list: list[Any] = [""] * 12
            val_type_uuid: uuid.UUID = self.val_type.uuid
            string_list[0] = str(val_type_uuid)
            string_list[1] = self.unit
            val_type_desc = self.val_type.description
            string_list[self.positions[val_type_desc]] = f'"{str(self.value)}"'
            return f'({",".join(string_list)})'
        else:
            return None

    def convert_value(self) -> Any:
        # Converts self.value from string to its primitive type. Used in validator and initialization
        converted_value: Any = None
        if not self.null:
            if "array" in self.val_type.description:
                converted_value = self.convert_list_value(
                    self.val_type.description, self.value
                )
            else:
                converted_value = self.convert_single_value(
                    self.val_type.description, self.value
                )
        return converted_value

    def convert_single_value(self, description: str, value: Any) -> Any:
        int_convert: Callable[[str], int] = lambda x: int(float(x))
        primitives = {
            "bool": bool,
            "int": int_convert,
            "num": float,
            "text": str,
            "blob": str,
        }
        # reverse_primitives = {bool: "bool", int: "int", float: "num", str: "text"}
        default_primitives = {
            "bool": False,
            "int": 0,
            "num": 0.0,
            "text": " ",
            "blob": " ",
        }
        prim = primitives[description]
        try:
            if value:
                result = prim(value)
            else:
                result = default_primitives[description]
        except Exception as e:
            print(e)
            # raise ValidationError(
            #    f'Data type mismatch, type provided is "{description}" but value is of type "{reverse_primitives[type(value)]}"'
            # )
            result = default_primitives[description]
        return result

    def convert_list_value(self, description: str, value: Any):
        primitives = {
            "array_bool": bool,
            "array_int": int,
            "array_num": float,
            "array_text": str,
        }
        prim = primitives[description]
        try:
            if isinstance(value, str):
                value = json.loads(value)
            result = [prim(val) for val in value]

        except Exception as e:
            raise ValidationError(
                f"Data type mismatch, type provided is {description} but exception occured: {e}"
            )

        # table = str.maketrans('[]', '{}')
        table = str.maketrans("{}", "[]")
        result = json.dumps(result).translate(table)
        return result

    def __str__(self):
        if not self.null:
            return f"{self.value} {self.unit}"
            # return self.str_value
        else:
            return ""

    def __repr__(self):
        if not self.null:
            return f"{self.value} {self.unit} {self.val_type.description}"
        else:
            return None

    def to_dict(self) -> Any:
        if not self.null:
            return {
                "value": self.value,
                "unit": self.unit,
                "type": self.val_type.description,
            }
        else:
            # return "null"
            return None

    @classmethod
    def from_db(cls, val_string):
        # print(val_string)
        args = list(csv.reader([val_string[1:-1]]))[0]
        # print(args)
        type_uuid = args[0]
        unit = args[1]
        val_type: TypeDef = get_val_types(uuid.UUID(type_uuid))

        # Values should be from index 2 onwards.
        value = args[cls.positions[val_type.description]]

        if val_type.description == "text":
            value = str(value)
        elif "array" in val_type.description:
            # import pdb; pdb.set_trace()
            table = str.maketrans("{}", "[]")
            value = value.translate(table)
            value = json.loads(value)
        if "bool" in val_type.description:
            table = str.maketrans(
                {"t": "true", "f": "false", "T": "true", "F": "false"}
            )
            value = value.translate(table)
            # value = json.loads(value)
        return cls(val_type, value, unit, raw_string=val_string)

    @classmethod
    def from_dict(cls, json_data):
        if json_data is None:
            return cls(None, None, "", null=True)
        else:
            required_keys = set(["type", "value", "unit"])
            val_type = None
            # Check if all keys are present in
            if not all(k in json_data for k in required_keys):
                print("Data does not have attribute keys")
                raise ValidationError(
                    f'Missing key "{required_keys - set(json_data.keys())}". ',
                    "invalid",
                )
            else:
                try:
                    val_type = cls.validate_type(json_data["type"])
                except Exception as e:
                    print(
                        "Exception occured in Val.from_dict(). Ignore if initializing"
                    )
            return cls(val_type, json_data["value"], json_data["unit"])

    @classmethod
    def validate_type(cls, type_string):
        # Check if type exists in database
        val_type = None
        val_types = get_val_types().values()
        for vt in val_types:
            if vt.category == "data" and vt.description == type_string:
                val_type = vt
                break
        # except TypeDef.DoesNotExist:
        if val_type is None:
            options = [val.description for val in val_types]
            raise ValidationError(
                f'Data type {type_string} does not exist. Options are: {", ".join(options)}',
                code="invalid",
            )
        return val_type
