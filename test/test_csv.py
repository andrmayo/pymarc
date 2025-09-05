# This file is part of pymarc. It is subject to the license terms in the
# LICENSE file found in the top-level directory of this distribution and at
# https://opensource.org/licenses/BSD-2-Clause. pymarc may be copied, modified,
# propagated, or distributed according to the terms contained in the LICENSE
# file.

import copy
import csv
import io
import unittest

import pymarc


class CSVReaderTest(unittest.TestCase):
    def setUp(self):
        with open("test/test.csv") as fh:
            self.in_csv = list(csv.DictReader(fh, strict=False))

        self._csv_fh = open("test/test.csv")  # noqa: SIM115
        self.reader = pymarc.CSVReader(self._csv_fh)  # type: ignore

    def tearDown(self) -> None:
        self._csv_fh.close()

    def testRoundtrip(self):
        """Test from and to csv.

        Tests that result of loading records from the test file
        produces objects deeply equal to the result of loading
        marc-in-csv files directly
        """
        recs = list(self.reader)
        self.assertEqual(
            len(self.in_csv), len(recs), "Incorrect number of records found"
        )
        for i, rec in enumerate(recs):
            deserialized = pymarc.parse_csv_to_dict(rec.as_csv())
            comp = copy.deepcopy(self.in_csv[i])
            # remove empty fields from csv dict
            to_delete = []
            for key in comp:
                if not comp[key]:
                    to_delete.append(key)
            for key in to_delete:
                del comp[key]
            self.assertEqual(comp, deserialized)

    def testOneRecord(self):
        """Tests case when in source csv there is only 1 record not wrapped in list."""
        output = io.StringIO(newline="")
        fieldnames = list(self.in_csv[0])
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(self.in_csv[0])
        data = output.getvalue()
        # remove empty fields from csv dict
        to_delete = []
        comp = copy.deepcopy(self.in_csv[0])
        for key in comp:
            if not comp[key]:
                to_delete.append(key)
        for key in to_delete:
            del comp[key]
        reader = pymarc.CSVReader(data)  # type: ignore
        self.assertEqual(
            [pymarc.parse_csv_to_dict(rec.as_csv()) for rec in reader][0], comp
        )


# TODO: revise tests below
class csvTest(unittest.TestCase):
    def setUp(self):
        self._test_fh = open("test/test.dat", "rb")  # noqa: SIM115
        self.reader = pymarc.MARCReader(self._test_fh)
        self._record = pymarc.Record()
        field = pymarc.Field(
            tag="245",
            indicators=pymarc.Indicators("1", "0"),
            subfields=[
                pymarc.Subfield(code="a", value="Python"),
                pymarc.Subfield(code="c", value="Guido"),
            ],
        )
        self._record.add_field(field)

    def tearDown(self) -> None:
        self._test_fh.close()

    def test_as_dict_single(self):
        _expected = {
            "fields": [
                {
                    "245": {
                        "ind1": "1",
                        "ind2": "0",
                        "subfields": [{"a": "Python"}, {"c": "Guido"}],
                    }
                }
            ],
            "leader": "          22        4500",
        }
        self.assertEqual(_expected, self._record.as_dict())

    def test_as_csv_types(self):
        rd = self._record.as_dict()
        self.assertTrue(isinstance(rd, dict))
        self.assertTrue(isinstance(rd["leader"], str))
        self.assertTrue(isinstance(rd["fields"], list))
        self.assertTrue(isinstance(rd["fields"][0], dict))
        self.assertTrue(isinstance(rd["fields"][0], dict))
        self.assertTrue(isinstance(rd["fields"][0]["245"]["ind1"], str))
        self.assertTrue(isinstance(rd["fields"][0]["245"]["ind2"], str))
        self.assertTrue(isinstance(rd["fields"][0]["245"]["subfields"], list))
        self.assertTrue(isinstance(rd["fields"][0]["245"]["subfields"][0], dict))
        self.assertTrue(isinstance(rd["fields"][0]["245"]["subfields"][0]["a"], str))
        self.assertTrue(isinstance(rd["fields"][0]["245"]["subfields"][1]["c"], str))

    def test_as_csv_simple(self):
        record = self._record.as_csv()
        record = pymarc.parse_csv_to_dict(record)

        self.assertTrue("LDR" in record)
        self.assertEqual(record["LDR"], "          22        4500")

        self.assertTrue("field_order" in record)
        self.assertTrue("245" in record)
        self.assertEqual(record["245"], "10$aPython$cGuido")

    def test_as_csv_multiple(self):
        for record in self.reader:
            self.assertEqual(dict, pymarc.parse_csv_to_dict(record.as_csv()).__class__)  # type: ignore


class csvParse(unittest.TestCase):
    def setUp(self):
        self._one_dat_fh = open("test/one.dat", "rb")  # noqa: SIM115
        self._one_csv_fh = open("test/one.csv")  # noqa: SIM115
        self._batch_xml_fh = open("test/batch.xml")  # noqa: SIM115
        self._batch_csv_fh = open("test/batch.csv")  # noqa: SIM115

        self.reader_dat = pymarc.MARCReader(self._one_dat_fh)
        self.parse_csv = pymarc.parse_csv_to_array(self._one_csv_fh)
        self.batch_xml = pymarc.parse_xml_to_array(self._batch_xml_fh)
        self.batch_csv = pymarc.parse_csv_to_array(self._batch_csv_fh)

    def tearDown(self) -> None:
        self._one_dat_fh.close()
        self._one_csv_fh.close()
        self._batch_xml_fh.close()
        self._batch_csv_fh.close()

    def testRoundtrip(self):
        # TODO: problem here is that current csv processing can't handle
        # records where the same field tag is repeated
        # CSVWriter should now have been fixed to write csv with distinct column names for identical marc tags
        # Remaining issue is that, although reading and writing to CSV can now handle duplicate records,
        # it does not preserve order

        recs = list(self.reader_dat)
        self.assertEqual(
            len(self.parse_csv), len(recs), "Incorrect number of records found"
        )
        for from_dat, from_csv in zip(recs, self.parse_csv):
            self.assertEqual(from_dat.as_marc(), from_csv.as_marc(), "Incorrect Record")

    def testParsecsvXml(self):
        self.assertEqual(
            len(self.batch_csv),
            len(self.batch_xml),
            "Incorrect number of parse records found",
        )
        for from_dat, from_csv in zip(self.batch_csv, self.batch_xml):
            self.assertEqual(from_dat.as_marc(), from_csv.as_marc(), "Incorrect Record")


if __name__ == "__main__":
    unittest.main()
