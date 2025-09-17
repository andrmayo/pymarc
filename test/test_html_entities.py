# This file is part of pymarc. It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution and at
# https://opensource.org/licenses/BSD-2-Clause. pymarc may be copied, modified,
# propagated, or distributed according to the terms contained in the LICENSE
# file.

import copy
import json
import unittest
from io import BytesIO, StringIO

import pymarc
from pymarc import Field, Indicators, Record, Subfield


class HTMLEntitiesWriterTest(unittest.TestCase):
    """Test the html_entities feature across all Writer classes."""

    def setUp(self):
        """Create test record with non-ASCII characters."""
        self.record = Record()
        self.record.add_field(
            Field(
                tag="245",
                indicators=Indicators("0", "0"),
                subfields=[
                    Subfield(code="a", value="Café: a story of héllo"),
                    Subfield(code="b", value="with naïve characters"),
                    Subfield(code="c", value="by José María"),
                ],
            )
        )
        self.record.add_field(
            Field(
                tag="260",
                indicators=Indicators(" ", " "),
                subfields=[
                    Subfield(code="a", value="Münich :"),
                    Subfield(code="b", value="Schöne Verlag,"),
                    Subfield(code="c", value="2023."),
                ],
            )
        )
        # Control field without subfields
        self.record.add_field(Field(tag="001", data="café123"))

        # Expected escaped values
        self.expected_cafe = "Caf&eacute;: a story of h&eacute;llo"
        self.expected_naive = "with na&iuml;ve characters"
        self.expected_jose = "by Jos&eacute; Mar&iacute;a"
        self.expected_munich = "M&uuml;nich :"
        self.expected_schone = "Sch&ouml;ne Verlag,"
        self.expected_control = "caf&eacute;123"

    def test_record_mutation_behavior(self):
        """Test that html_entities=True mutates the original record."""
        original_245a = self.record["245"]["a"]
        original_001 = self.record["001"].data

        # Write with html_entities=True
        file_handle = StringIO()
        writer = pymarc.JSONWriter(file_handle, html_entities=True)
        writer.write(self.record)
        writer.close(close_fh=False)

        # Check that original record was mutated
        self.assertEqual(self.record["245"]["a"], self.expected_cafe)
        self.assertEqual(self.record["001"].data, self.expected_control)
        self.assertNotEqual(self.record["245"]["a"], original_245a)
        self.assertNotEqual(self.record["001"].data, original_001)

    def test_record_preservation_without_html_entities(self):
        """Test that html_entities=False preserves the original record."""
        original_245a = self.record["245"]["a"]
        original_001 = self.record["001"].data

        # Write with html_entities=False (default)
        file_handle = StringIO()
        writer = pymarc.JSONWriter(file_handle, html_entities=False)
        writer.write(self.record)
        writer.close(close_fh=False)

        # Check that original record was NOT mutated
        self.assertEqual(self.record["245"]["a"], original_245a)
        self.assertEqual(self.record["001"].data, original_001)

    def test_json_writer_html_entities(self):
        """Test JSONWriter with html_entities=True."""
        record_copy = copy.deepcopy(self.record)

        file_handle = StringIO()
        writer = pymarc.JSONWriter(file_handle, html_entities=True)
        writer.write(record_copy)
        writer.close(close_fh=False)

        # Check that subfields were escaped
        self.assertEqual(record_copy["245"]["a"], self.expected_cafe)
        self.assertEqual(record_copy["245"]["b"], self.expected_naive)
        self.assertEqual(record_copy["245"]["c"], self.expected_jose)
        self.assertEqual(record_copy["260"]["a"], self.expected_munich)
        self.assertEqual(record_copy["260"]["b"], self.expected_schone)

        # Check control field
        self.assertEqual(record_copy["001"].data, self.expected_control)

    def test_csv_writer_html_entities(self):
        """Test CSVWriter with html_entities=True."""
        record_copy = copy.deepcopy(self.record)

        file_handle = StringIO()
        writer = pymarc.CSVWriter(file_handle, html_entities=True)
        writer.write_all([record_copy])
        writer.close(close_fh=False)

        csv_output = file_handle.getvalue()

        # Check that escaped values appear in CSV output
        self.assertIn(self.expected_cafe, csv_output)
        self.assertIn(self.expected_naive, csv_output)
        self.assertIn(self.expected_jose, csv_output)
        self.assertIn(self.expected_munich, csv_output)
        self.assertIn(self.expected_schone, csv_output)
        self.assertIn(self.expected_control, csv_output)

    def test_marc_writer_html_entities(self):
        """Test MARCWriter with html_entities=True."""
        record_copy = copy.deepcopy(self.record)

        file_handle = BytesIO()
        writer = pymarc.MARCWriter(file_handle, html_entities=True)
        writer.write(record_copy)
        writer.close(close_fh=False)

        # Check that record was mutated
        self.assertEqual(record_copy["245"]["a"], self.expected_cafe)
        self.assertEqual(record_copy["245"]["b"], self.expected_naive)
        self.assertEqual(record_copy["245"]["c"], self.expected_jose)
        self.assertEqual(record_copy["001"].data, self.expected_control)

    def test_text_writer_html_entities(self):
        """Test TextWriter with html_entities=True."""
        record_copy = copy.deepcopy(self.record)

        file_handle = StringIO()
        writer = pymarc.TextWriter(file_handle, html_entities=True)
        writer.write(record_copy)
        writer.close(close_fh=False)

        text_output = file_handle.getvalue()

        # Check that escaped values appear in text output
        self.assertIn(self.expected_cafe, text_output)
        self.assertIn(self.expected_naive, text_output)
        self.assertIn(self.expected_jose, text_output)
        self.assertIn(self.expected_control, text_output)

    def test_xml_writer_html_entities(self):
        """Test XMLWriter with html_entities=True."""
        record_copy = copy.deepcopy(self.record)

        file_handle = BytesIO()
        writer = pymarc.XMLWriter(file_handle, html_entities=True)
        writer.write(record_copy)
        writer.close(close_fh=False)

        xml_output = file_handle.getvalue().decode("utf-8")

        # Check that double-escaped values appear in XML output (HTML entities get XML-escaped)
        self.assertIn("Caf&amp;eacute;: a story of h&amp;eacute;llo", xml_output)
        self.assertIn("with na&amp;iuml;ve characters", xml_output)
        self.assertIn("by Jos&amp;eacute; Mar&amp;iacute;a", xml_output)
        self.assertIn("caf&amp;eacute;123", xml_output)

    def test_multiple_records_mutation(self):
        """Test that each record is mutated independently."""
        record1 = copy.deepcopy(self.record)
        record2 = copy.deepcopy(self.record)

        # Modify second record to have different values
        record2["245"]["a"] = "Différent title with ñoño"

        file_handle = StringIO()
        writer = pymarc.JSONWriter(file_handle, html_entities=True)
        writer.write(record1)
        writer.write(record2)
        writer.close(close_fh=False)

        # Check that both records were mutated correctly
        self.assertEqual(record1["245"]["a"], self.expected_cafe)
        self.assertEqual(
            record2["245"]["a"], "Diff&eacute;rent title with &ntilde;o&ntilde;o"
        )

    def test_empty_subfield_handling(self):
        """Test handling of empty or None subfield values."""
        record = Record()
        record.add_field(
            Field(
                tag="245",
                indicators=Indicators("0", "0"),
                subfields=[
                    Subfield(code="a", value=""),
                    Subfield(code="b", value="Normal text"),
                ],
            )
        )

        file_handle = StringIO()
        writer = pymarc.JSONWriter(file_handle, html_entities=True)
        writer.write(record)
        writer.close(close_fh=False)

        # Should not raise an exception - test passes if no exception is raised
        output = file_handle.getvalue()
        self.assertIsNotNone(output)

    def test_non_string_data_handling(self):
        """Test that non-string data is handled gracefully."""
        # This test verifies the html_escape_unicode function handles non-strings
        from pymarc.htmlutils import html_escape_unicode

        # Should return the input unchanged for non-strings
        self.assertEqual(html_escape_unicode(123), 123)
        self.assertEqual(html_escape_unicode(None), None)
        self.assertEqual(html_escape_unicode([]), [])

    def test_ascii_only_text_unchanged(self):
        """Test that ASCII-only text is not modified."""
        record = Record()
        record.add_field(
            Field(
                tag="245",
                indicators=Indicators("0", "0"),
                subfields=[
                    Subfield(code="a", value="ASCII only title"),
                    Subfield(code="b", value="with normal characters"),
                ],
            )
        )

        original_245a = record["245"]["a"]
        original_245b = record["245"]["b"]

        file_handle = StringIO()
        writer = pymarc.JSONWriter(file_handle, html_entities=True)
        writer.write(record)
        writer.close(close_fh=False)

        # ASCII text should remain unchanged
        self.assertEqual(record["245"]["a"], original_245a)
        self.assertEqual(record["245"]["b"], original_245b)


if __name__ == "__main__":
    unittest.main()

