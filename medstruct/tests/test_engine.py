import unittest

from medstruct.core import ExtractionEngine
from medstruct.core.models import SchemaDefinition
from medstruct.core.schema_lint import validate_schema
from medstruct.store import load_schema


class ExtractionEngineTest(unittest.TestCase):
    def test_extracts_stroke_demo_fields(self):
        schema = load_schema("stroke_registry_v1")
        document = (
            "主诉：言语不清、右肢无力1天余。\n"
            "现病史：患者出现言语不清，伴右肢无力，无头痛，进食水无呛咳。\n"
            "既往史：既往高血压10年，否认糖尿病、房颤。\n"
            "查体：BP 左140/83mmHg 右151/87mmHg。\n"
            "辅助检查：头MRI示DWI高信号，考虑急性脑梗死。入院NIHSS评分：6分。\n"
            "入院诊断：急性脑梗死。"
        )
        response = ExtractionEngine().extract(schema, document)
        values = {item.field_id: item.value for item in response.results}
        self.assertEqual(values["hypertension"], "是")
        self.assertEqual(values["diabetes"], "否")
        self.assertEqual(values["speech_disorder"], "是")
        self.assertEqual(values["headache"], "否")
        self.assertEqual(values["nihss_in"], "6")

    def test_custom_schema_regex(self):
        schema = SchemaDefinition.from_dict(
            {
                "id": "custom",
                "name": "custom",
                "fields": [
                    {
                        "id": "drug",
                        "name": "出院带药",
                        "section": "出院医嘱",
                        "keywords": ["出院带药"],
                        "regex_patterns": ["出院带药[:：]?(?P<value>[^。\\n]+)"],
                    }
                ],
            }
        )
        response = ExtractionEngine().extract(schema, "出院医嘱：出院带药：阿司匹林100mg qd。")
        self.assertEqual(response.results[0].value, "阿司匹林100mg qd")

    def test_schema_lint_blocks_bad_regex(self):
        schema = SchemaDefinition.from_dict(
            {
                "id": "bad",
                "name": "bad",
                "fields": [
                    {
                        "id": "broken",
                        "name": "坏字段",
                        "strategies": ["regex"],
                        "regex_patterns": ["("],
                    }
                ],
            }
        )
        report = validate_schema(schema)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["error_count"], 1)


if __name__ == "__main__":
    unittest.main()
