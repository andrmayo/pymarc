from htmlutils import repl_nonASCII
from reader import CSVReader

from pymarc import Field, Indicators, Leader, Record, Subfield


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
        for field in element_dict:
            if isinstance(field, str) and (
                field.upper() == "LDR" or field.lower() == "leader"
            ):
                self._record.leader = Leader(element_dict[field])
                continue
            element_dict[field] = element_dict[field].replace(chr(31), "$")
            if "$" in element_dict[field][:3]:
                indicators, field_text = element_dict[field].split("$", maxsplit=1)
                indicators = indicators.replace("\\", " ")
                indicators = list(indicators)[:2]
            else:
                indicators, field_text = (None, element_dict[field])
            if indicators:
                subfields = (
                    [Subfield(code=s[0], value=s[1:]) for s in field_text.split("$")]
                    if field_text
                    else []
                )
                field = Field(
                    tag=field,
                    indicators=Indicators(*indicators),
                    subfields=subfields,
                )
            else:
                field = Field(
                    tag=field,
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
