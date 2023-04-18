# This file is part of pymarc. It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution and at
# https://opensource.org/licenses/BSD-2-Clause. pymarc may be copied, modified,
# propagated, or distributed according to the terms contained in the LICENSE
# file.

"""The pymarc field file."""

import logging
from collections import defaultdict
from typing import List, Optional, DefaultDict, NamedTuple, Iterator, Dict

from pymarc.constants import SUBFIELD_INDICATOR, END_OF_FIELD
from pymarc.marc8 import marc8_to_unicode

Subfield = NamedTuple("Subfield", [("code", str), ("value", str)])


class Field:
    """Field() pass in the field tag, indicators and subfields for the tag.

    .. code-block:: python

        field = Field(
            tag = '245',
            indicators = ['0','1'],
            subfields = [
                Subfield(code='a', value='The pragmatic programmer : '),
                Subfield(code='b', value='from journeyman to master /'),
                Subfield(code='c', value='Andrew Hunt, David Thomas.'),
            ])

    If you want to create a control field, don't pass in the indicators
    and use a data parameter rather than a subfields parameter:

    .. code-block:: python

        field = Field(tag='001', data='fol05731351')
    """

    __slots__ = ("tag", "data", "indicators", "subfields", "__pos")

    def __init__(
        self,
        tag: str,
        indicators: Optional[List[str]] = None,
        subfields: Optional[List[Subfield]] = None,
        data: str = "",
    ):
        """Initialize a field `tag`."""
        # attempt to normalize integer tags if necessary
        try:
            self.tag = f"{int(tag):03}"
        except ValueError:
            self.tag = f"{tag}"

        if subfields and isinstance(subfields[0], str):
            raise ValueError(
                """The subfield input no longer accepts strings, and should use Subfield.
                   Please consult the documentation for details.
                """
            )

        # assume control fields are numeric only; replicates ruby-marc behavior
        if self.tag < "010" and self.tag.isdigit():
            self.data = data
        else:
            self.subfields: List[Subfield] = subfields or []
            self.indicators = [str(x) for x in (indicators or [])]

    @classmethod
    def convert_legacy_subfields(cls, subfields: List[str]) -> List[Subfield]:
        """
        Converts older-style subfield lists into Subfield lists.

        Converts the old-style list of strings into a list of Subfields.
        As a class method this does not actually set any fields; it simply
        takes a list of strings and returns a list of Subfields.

        .. code-block:: python

            legacy_fields: list[str] = ['a', 'The pragmatic programmer : ',
                                        'b', 'from journeyman to master /',
                                        'c', 'Andrew Hunt, David Thomas']

            coded_fields: list[Subfield] = Field.convert_legacy_subfields(legacy_fields)

            myfield = Field(
                tag="245",
                indicators = ['0','1'],
                subfields=coded_fields
            )

        :param subfields: A list of [code, value, code, value]
        :return: A list of Subfield named tuples
        """
        # Make an iterator out of the incoming subfields.
        subf_it: Iterator[str] = iter(subfields)
        # This creates a tuple based on the next value of the iterator. In this case,
        # the subfield code will be the first element, and then the subfield value
        # will be the second.
        subf = zip(subf_it, subf_it)
        # Create a coded subfield tuple of each (code, value) item in the incoming
        # subfields.
        return [Subfield._make(t) for t in subf]

    def __iter__(self):
        self.__pos = 0
        return self

    def __str__(self) -> str:
        """String representation of the field.

        A Field object in a string context will return the tag, indicators
        and subfield as a string. This follows MARCMaker format; see [1]
        and [2] for further reference. Special character mnemonic strings
        have yet to be implemented (see [3]), so be forewarned. Note also
        for complete MARCMaker compatibility, you will need to change your
        newlines to DOS format ('CRLF').

        [1] http://www.loc.gov/marc/makrbrkr.html#mechanics
        [2] http://search.cpan.org/~eijabb/MARC-File-MARCMaker/
        [3] http://www.loc.gov/marc/mnemonics.html
        """
        if self.is_control_field():
            _data: str = self.data.replace(" ", "\\")
            return f"={self.tag}  {_data}"
        else:
            _ind = []
            _subf = []

            for indicator in self.indicators:
                if indicator in (" ", "\\"):
                    _ind.append("\\")
                else:
                    _ind.append(f"{indicator}")

            for subfield in self.subfields:
                _subf.append(f"${subfield.code}{subfield.value}")

            return f"={self.tag}  {''.join(_ind)}{''.join(_subf)}"

    def get(self, code: str, default=None):
        """A dict-like get method with a default value.

        Implements a non-raising getter for a subfield code that will
        return the value of the first subfield whose code is `key`.
        """
        if code not in self:
            return default
        return self[code]

    def __getitem__(self, code: str) -> str:
        """Retrieve the first subfield with a given subfield code in a field.

        Raises KeyError if `code` is not in the Field.

        .. code-block:: python

            field['a']
        """
        if code not in self:
            raise KeyError

        for subf in self.subfields:
            if subf.code == code:
                return subf.value
        # This should not occur, but just incase we've looped through
        # and couldn't find the code, default to raising KeyError.
        raise KeyError

    def __contains__(self, subfield: str) -> bool:
        """Allows a shorthand test of field membership.

        .. code-block:: python

            'a' in field

        """
        for s in self.subfields:
            if s.code == subfield:
                return True
        return False

    def __setitem__(self, code: str, value: str) -> None:
        """Set the values of the subfield code in a field.

        .. code-block:: python

            field['a'] = 'value'

        Raises KeyError if there is more than one subfield code.
        """
        num_subfields: int = [x.code for x in self.subfields].count(code)

        if num_subfields > 1:
            raise KeyError(f"more than one code '{code}'")
        elif num_subfields == 0:
            raise KeyError(f"no code '{code}'")

        for idx, subf in enumerate(self.subfields):
            if subf.code == code:
                new_val = Subfield(code=subf.code, value=value)
                self.subfields[idx] = new_val
                break

    def __next__(self) -> Subfield:
        if not hasattr(self, "subfields"):
            raise StopIteration

        try:
            subfield = self.subfields[self.__pos]
            self.__pos += 1
            return subfield  # type: ignore
        except IndexError:
            raise StopIteration

    def value(self) -> str:
        """Returns the field as a string w/ tag, indicators, and subfield indicators."""
        if self.is_control_field():
            return self.data
        return " ".join(subfield.value.strip() for subfield in self.subfields)

    def get_subfields(self, *codes) -> List[str]:
        """Get subfields matching `codes`.

        get_subfields() accepts one or more subfield codes and returns
        a list of subfield values.  The order of the subfield values
        in the list will be the order that they appear in the field.

        .. code-block:: python

            print(field.get_subfields('a'))
            print(field.get_subfields('a', 'b', 'z'))
        """
        return [subfield.value for subfield in self.subfields if subfield.code in codes]

    def add_subfield(self, code: str, value: str, pos=None) -> None:
        """Adds a subfield code/value to the end of a field or at a position (pos).

        If pos is not supplied or out of range, the subfield will be added at the end.

        .. code-block:: python

            field.add_subfield('u', 'http://www.loc.gov')
            field.add_subfield('u', 'http://www.loc.gov', 0)
        """
        append: bool = pos is None or pos > len(self.subfields)
        insertable: Subfield = Subfield(code=code, value=value)

        if append:
            self.subfields.append(insertable)
        else:
            self.subfields.insert(pos, insertable)

    def delete_subfield(self, code: str) -> Optional[str]:
        """Deletes the first subfield with the specified 'code' and returns its value.

        .. code-block:: python

            value = field.delete_subfield('a')

        If no subfield is found with the specified code None is returned.
        """
        if code not in self:
            return None

        index: int = [s.code for s in self.subfields].index(code)
        whole_field: Subfield = self.subfields.pop(index)

        return whole_field.value

    def subfields_as_dict(self) -> Dict[str, List]:
        """Returns the subfields as a dictionary.

        The dictionary is a mapping of subfield codes and values. Since
        subfield codes can repeat the values are a list.
        """
        subs: DefaultDict[str, List] = defaultdict(list)
        for field in self.subfields:
            subs[field.code].append(field.value)
        return dict(subs)

    def is_control_field(self) -> bool:
        """Returns true or false if the field is considered a control field.

        Control fields lack indicators and subfields.
        """
        return self.tag < "010" and self.tag.isdigit()

    def linkage_occurrence_num(self) -> Optional[str]:
        """Return the 'occurrence number' part of subfield 6, or None if not present."""
        ocn = self.get("6", "")
        return ocn.split("-")[1].split("/")[0] if ocn else None

    def as_marc(self, encoding: str) -> bytes:
        """Used during conversion of a field to raw marc."""
        if self.is_control_field():
            return f"{self.data}{END_OF_FIELD}".encode(encoding)

        _subf = []
        for subfield in self.subfields:
            _subf.append(f"{SUBFIELD_INDICATOR}{subfield.code}{subfield.value}")

        return (
            f"{self.indicator1}{self.indicator2}{''.join(_subf)}{END_OF_FIELD}".encode(
                encoding
            )
        )

    # alias for backwards compatibility
    as_marc21 = as_marc

    def format_field(self) -> str:
        """Returns the field as a string w/ tag, indicators, and subfield indicators.

        Like :func:`Field.value() <pymarc.field.Field.value>`, but prettier
        (adds spaces, formats subject headings).
        """
        if self.is_control_field():
            return self.data

        field_data: str = ""

        for subfield in self.subfields:
            if subfield.code == "6":
                continue

            if not self.is_subject_field():
                field_data += f" {subfield.value}"
            else:
                if subfield.code not in ("v", "x", "y", "z"):
                    field_data += f" {subfield.value}"
                else:
                    field_data += f" -- {subfield.value}"
        return field_data.strip()

    def is_subject_field(self) -> bool:
        """Returns True or False if the field is considered a subject field.

        Used by :func:`format_field() <pymarc.field.Field.format_field>` .
        """
        return self.tag.startswith("6")

    @property
    def indicator1(self) -> str:
        """Indicator 1."""
        return self.indicators[0]

    @indicator1.setter
    def indicator1(self, value: str) -> None:
        """Indicator 1 (setter)."""
        self.indicators[0] = value

    @property
    def indicator2(self) -> str:
        """Indicator 2."""
        return self.indicators[1]

    @indicator2.setter
    def indicator2(self, value: str) -> None:
        """Indicator 2 (setter)."""
        self.indicators[1] = value


class RawField(Field):
    """MARC field that keeps data in raw, un-decoded byte strings.

    Should only be used when input records are wrongly encoded.
    """

    def as_marc(self, encoding: Optional[str] = None):
        """Used during conversion of a field to raw MARC."""
        if encoding is not None:
            logging.warning("Attempt to force a RawField into encoding %s", encoding)
        if self.is_control_field():
            return self.data + END_OF_FIELD.encode("ascii")  # type: ignore
        marc: bytes = self.indicator1.encode("ascii") + self.indicator2.encode("ascii")
        for subfield in self.subfields:
            marc += (
                SUBFIELD_INDICATOR.encode("ascii")
                + subfield.code.encode("ascii")
                + subfield.value  # type: ignore
            )
        return marc + END_OF_FIELD.encode("ascii")


def map_marc8_field(f: Field) -> Field:
    """Map MARC8 field."""
    if f.is_control_field():
        f.data = marc8_to_unicode(f.data)
    else:
        f.subfields: List[Subfield] = [
            Subfield(subfield.code, marc8_to_unicode(subfield.value))
            for subfield in f.subfields
        ]
    return f
