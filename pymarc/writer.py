# This file is part of pymarc. It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution and at
# https://opensource.org/licenses/BSD-2-Clause. pymarc may be copied, modified,
# propagated, or distributed according to the terms contained in the LICENSE
# file.

"""Pymarc Writer."""

import csv
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from typing import IO, Union
from warnings import warn

import pymarc
from pymarc import Record, WriteNeedsRecord


class Writer:
    """Base Writer object."""

    def __init__(self, file_handle: IO) -> None:
        """Init."""
        self.file_handle = file_handle

    def write(self, record: Record) -> None:
        """Write."""
        if not isinstance(record, Record):
            raise WriteNeedsRecord

    def close(self, close_fh: bool = True) -> None:
        """Closes the writer.

        If close_fh is False close will also close the underlying file handle
        that was passed in to the constructor. The default is True.
        """
        if close_fh:
            self.file_handle.close()
        self.file_handle = None  # type: ignore


class CSVWriter(Writer):
    """A class for writing records as an array of MARC-in-CSV objects.

    IMPORTANT: You must close a CSVWriter,
    otherwise you will not get valid CSV.
    Also, the CSVWriter will impose the same order of fields on all records being processed.
    By default, this is sorted by tag in increasing order, but pass
    `sort_tags=False` to use the order in which the CSVWriter encounters tags with
    `write_all`, or else `sort_tags=False` with `add_tags` to explicitly control the order.
    Because the same order is imposed on all records in the CSV, records written to CSV
    and then back to MARC may not be identical to the original records.

    Simple usage::

    .. code-block:: python

        from pymarc import CSVWriter

        # writing individual records to a file (not recommended)
        writer = CSVWriter(open('file.csv','wt'))
        writer.add_tags(['001', '003', '264', '300']
        writer.write(record1)
        writer.write(record2)
        writer.close()  # Important!

        #writing multiple records (as list) to a file (recommended)
        writer = CSVWriter(open('file.csv','wt'))
        writer.write_all(records)
        writer.close()  # Important!

        # writing to a string
        string = StringIO()
        writer = CSVWriter(string)
        writer.write(records)
        writer.close(close_fh=False)  # Im6portant!
        print(string)
    """

    def __init__(self, file_handle: IO) -> None:
        super().__init__(file_handle)
        self.write_count = 0
        self.marc_tags: list = ["LDR"]
        self.csv_dict_writer = None

    def write(self, record):
        """Writes record.
        Note that for writing single records to a CSV file, if record contains
        a tag that hasn't been defined (explicitly with `CSVWriter.add_tags`
        or implicitly with `write_all`), the corresponding field will simply be skipped.
        This applies to duplicate tags as well: to process multiple fields with the
        same tag, e.g. two fields with tag 630, `self.marc_tags` must contain
        '630' and '630_2', if three fields, '630_3', etc.
        So `CSVWriter.add_tags` or `CSVWriter.write_all` should always be called beforehand.
        It is probably best always to use `CSVWriter.write_all`."""
        Writer.write(self, record)
        leader = record.leader.leader
        csv_record = {}
        csv_record["LDR"] = leader
        tag_counts = {}
        field_order = []
        for marc_field in record.get_fields():
            field_order.append(marc_field)
            tag_counts[marc_field.tag] = tag_counts.get(marc_field.tag, 0) + 1
            cur_tag = marc_field.tag
            if tag_counts[marc_field.tag] > 1:
                cur_tag = f"{marc_field.tag}_{tag_counts[marc_field.tag]}"
            if cur_tag not in self.marc_tags:
                print(f"skipping marc tag: {marc_field.tag}")
                continue
            indicator1 = marc_field.indicator1 if marc_field.indicator1 != " " else "\\"
            indicator2 = marc_field.indicator2 if marc_field.indicator2 != " " else "\\"
            if not indicator1:
                indicator1 = "\\"
            if not indicator2:
                indicator2 = "\\"
            if marc_field.subfields:
                csv_record[cur_tag] = (
                    f"{indicator1}{indicator2}{''.join([f'${s.code}{s.value}' for s in marc_field.subfields])}"
                )
            else:
                csv_record[marc_field.tag] = marc_field.data
        csv_record["field_order"] = " ".join(field_order)

        if not self.csv_dict_writer:
            self.marc_tags = sorted(self.marc_tags)
            self.csv_dict_writer = csv.DictWriter(
                self.file_handle,  # type: ignore
                self.marc_tags,
            )
            self.csv_dict_writer.writeheader()

        if len(self.marc_tags) <= 1:
            msg = "No marc tags have been added, so CSV will be missing fields. Call add_tags or write_all before write."
            warn(msg, UserWarning, stacklevel=1)

        self.csv_dict_writer.writerow(csv_record)

    def add_tags(self, tags: Iterable) -> list:
        """Add CSV columns for fields in marc records.
        Only necessary if calling `CSVWriter.write`
        without previously calling `CSVWriter.write_all`."""
        self.marc_tags.extend(tags)
        return self.marc_tags

    def write_all(self, records: Union[Record, list]) -> None:
        """Writes records.
        Infers the columns for CSV from tags in records,
        so there's no need to call `CSVWriter.add_tags`."""
        if not isinstance(records, list):
            records = [records]
        csv_records = []
        for record in records:
            Writer.write(self, record)
            csv_record = {}
            if record:
                leader = record.leader.leader
                csv_record["LDR"] = leader
                tag_counts = {}
                csv_fields = []
                for marc_field in record.get_fields():
                    cur_tag = marc_field.tag
                    tag_counts[cur_tag] = tag_counts.get(cur_tag, 0) + 1
                    if tag_counts[cur_tag] > 1:
                        cur_tag = f"{cur_tag}_{tag_counts[cur_tag]}"
                    if cur_tag not in self.marc_tags:
                        self.marc_tags.append(cur_tag)
                    csv_fields.append(cur_tag)
                    # deal with indicators
                    indicator1 = (
                        marc_field.indicator1 if marc_field.indicator1 != " " else "\\"
                    )
                    indicator2 = (
                        marc_field.indicator2 if marc_field.indicator2 != " " else "\\"
                    )
                    if not indicator1:
                        indicator1 = "\\"
                    if not indicator2:
                        indicator2 = "\\"
                    # note that some fields may have no subfields (as with control fields).
                    # in this case, marc_field.subfields returns and empty list.
                    if marc_field.subfields:
                        csv_record[cur_tag] = (
                            f"{indicator1}{indicator2}{''.join([f'${s.code}{s.value}' for s in marc_field.subfields])}"
                        )
                    # handle field without subfields. These should be control fields.
                    else:
                        csv_record[cur_tag] = marc_field.data
                csv_record["field_order"] = " ".join(csv_fields)

                csv_records.append(csv_record)
        if not self.csv_dict_writer:
            self.marc_tags = sorted(self.marc_tags)
            csv_headings = self.marc_tags + ["field_order"]
            self.csv_dict_writer = csv.DictWriter(
                self.file_handle,  # type: ignore
                csv_headings,
            )
            self.csv_dict_writer.writeheader()

        self.csv_dict_writer.writerows(csv_records)

    def close(self, close_fh: bool = True) -> None:
        """Closes the writer.

        If close_fh is False close will also close the underlying file
        handle that was passed in to the constructor. The default is True.
        """
        Writer.close(self, close_fh)


class JSONWriter(Writer):
    """A class for writing records as an array of MARC-in-JSON objects.

    IMPORTANT: You must the close a JSONWriter,
    otherwise you will not get valid JSON.

    Simple usage::

    .. code-block:: python

        from pymarc import JSONWriter

        # writing to a file
        writer = JSONWriter(open('file.json','wt'))
        writer.write(record)
        writer.close()  # Important!

        # writing to a string
        string = StringIO()
        writer = JSONWriter(string)
        writer.write(record)
        writer.close(close_fh=False)  # Important!
        print(string)
    """

    def __init__(self, file_handle: IO) -> None:
        """You need to pass in a text file like object."""
        super().__init__(file_handle)
        self.write_count = 0
        self.file_handle.write("[")

    def write(self, record: Record) -> None:
        """Writes a record."""
        Writer.write(self, record)
        if self.write_count > 0:
            self.file_handle.write(",")
        json.dump(record.as_dict(), self.file_handle, separators=(",", ":"))
        self.write_count += 1

    def close(self, close_fh: bool = True) -> None:
        """Closes the writer.

        If close_fh is False close will also close the underlying file
        handle that was passed in to the constructor. The default is True.
        """
        self.file_handle.write("]")
        Writer.close(self, close_fh)


class MARCWriter(Writer):
    """A class for writing MARC21 records in transmission format.

    Simple usage::

    .. code-block:: python

        from pymarc import MARCWriter

        # writing to a fileIO
        writer = MARCWriter(open('file.dat','wb'))
        writer.write(record)
        writer.close()

        # writing to a string (Python 2 only)
        string = StringIO()
        writer = MARCWriter(string)
        writer.write(record)
        writer.close(close_fh=False)
        print(string)

        # writing to memory (Python 3 only)

        memory = BytesIO()
        writer = MARCWriter(memory)
        writer.write(record)
        writer.close(close_fh=False)
    """

    def __init__(self, file_handle: IO) -> None:
        """You need to pass in a byte file like object."""
        super().__init__(file_handle)

    def write(self, record: Record) -> None:
        """Writes a record."""
        Writer.write(self, record)
        self.file_handle.write(record.as_marc())


class TextWriter(Writer):
    """A class for writing records in prettified text MARCMaker format.

    A blank line separates each record.

    Simple usage:

    .. code-block:: python

        from pymarc import TextWriter

        # writing to a file
        writer = TextWriter(open('file.txt','wt'))
        writer.write(record)
        writer.close()

        # writing to a string
        string = StringIO()
        writer = TextWriter(string)
        writer.write(record)
        writer.close(close_fh=False)
        print(string)
    """

    def __init__(self, file_handle: IO) -> None:
        """You need to pass in a text file like object."""
        super().__init__(file_handle)
        self.write_count = 0

    def write(self, record: Record) -> None:
        """Writes a record."""
        Writer.write(self, record)
        if self.write_count > 0:
            self.file_handle.write("\n")
        self.file_handle.write(str(record))
        self.write_count += 1


class XMLWriter(Writer):
    """A class for writing records as a MARCXML collection.

    IMPORTANT: You must then close an XMLWriter, otherwise you will not get
    a valid XML document.

    Simple usage:

    .. code-block:: python

        from pymarc import XMLWriter

        # writing to a file
        writer = XMLWriter(open('file.xml','wb'))
        writer.write(record)
        writer.close()  # Important!

        # writing to a string (Python 2 only)
        string = StringIO()
        writer = XMLWriter(string)
        writer.write(record)
        writer.close(close_fh=False)  # Important!
        print(string)

        # writing to memory (Python 3 only)
        memory = BytesIO()
        writer = XMLWriter(memory)
        writer.write(record)
        writer.close(close_fh=False)  # Important!
    """

    def __init__(self, file_handle: IO) -> None:
        """You need to pass in a binary file like object."""
        super().__init__(file_handle)
        self.file_handle.write(b'<?xml version="1.0" encoding="UTF-8"?>')
        self.file_handle.write(b'<collection xmlns="http://www.loc.gov/MARC21/slim">')

    def write(self, record: Record) -> None:
        """Writes a record."""
        Writer.write(self, record)
        node = pymarc.record_to_xml_node(record)
        self.file_handle.write(ET.tostring(node, encoding="utf-8"))

    def close(self, close_fh: bool = True) -> None:
        """Closes the writer.

        If close_fh is False close will also close the underlying file handle
        that was passed in to the constructor. The default is True.
        """
        self.file_handle.write(b"</collection>")
        Writer.close(self, close_fh)
