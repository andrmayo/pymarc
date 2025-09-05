from csv import DictReader
from io import StringIO

from pymarc import CSVReader, Field, Indicators, Leader, Record, Subfield
from pymarc.htmlutils import repl_nonASCII


class CSVHandler:
    """Handle CSV.
    Note that in CSV representation subfields are separated by $."""

    def __init__(self):
        """Init."""
        self.records = []
        self._record = None
        self._field = None
        self._text = []

    def element(self, element_dict):
        """Convert CSV `element_dict` to pymarc fields."""
        self._record = Record()
        # ensures fields are added to record in original order
        leader = element_dict.get("LDR")
        if not leader:
            leader = element_dict["leader"]
        self._record.leader = Leader(leader)
        fields = element_dict["field_order"].split()
        for field in fields:
            if not element_dict.get(field):
                continue
            element_dict[field] = element_dict[field].replace(chr(31), "$")
            if "$" in element_dict[field][:3]:
                indicators, field_text = element_dict[field].split("$", maxsplit=1)
                indicators = indicators.replace("\\", " ")
                indicators = list(indicators)[:2]
            else:
                indicators, field_text = (None, element_dict[field])
            # deal with duplicate field tags
            tag = field
            if "_" in tag:
                tag = tag[: tag.index("_")]
            if indicators:
                subfields = (
                    [Subfield(code=s[0], value=s[1:]) for s in field_text.split("$")]
                    if field_text
                    else []
                )
                field = Field(
                    tag=tag,
                    indicators=Indicators(*indicators),
                    subfields=subfields,
                )
            else:
                field = Field(
                    tag=tag,
                    data=field_text,
                )
            self._record.add_field(field)
        self.process_record(self._record)

    def elements(self, dict_list):
        """Sends `dict_list` to `element`."""
        if not isinstance(dict_list, list):
            dict_list = [dict_list]
        for rec in dict_list:
            self.element(rec)
        return self.records

    def process_record(self, record):
        """Append `record` to `self.records`."""
        self.records.append(record)

    def get_record(self, index: int) -> Record:
        """Takes in an index integer and returns relevant line of csv as Record object"""
        return self.records[index]

    def html_ent(self) -> None:
        """Converts all non-ASCII utf-8 characters to their ASCII-compatible entity names.
        Applied in-place to self.records."""
        for i, rec in enumerate(self.records):
            self.records[i] = repl_nonASCII(rec)


def parse_csv_to_array(csv_file):
    """CSV to elements."""
    csv_reader = CSVReader(csv_file)
    handler = CSVHandler()
    return handler.elements(csv_reader.records)


def parse_csv_to_dict(csv_string: str) -> dict:
    """Converts record serialized as CSV string to dict."""
    str_input = StringIO(csv_string, newline="")
    csv_dict = list(DictReader(str_input))[0]
    return csv_dict
