import csv, io, sys, unittest
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from project_source import accepted, date, numeric, full_identity, project, rows
from metrics import KEYS, groups, account
from exercise import answer


def fact(fid="F1", **changes):
    r = dict(
        fact_id=fid,
        cik="320193",
        adsh="0000320193-26-000020",
        tag="Assets",
        version="us-gaap/2026",
        ddate="20260630",
        qtrs="0",
        uom="USD",
        segment_hash="",
        coreg_hash="",
        accepted="2026-07-31 06:01:00.000000",
        value="100",
        value_state="KNOWN",
        state="ELIGIBLE",
        source_records="1",
    )
    r.update(changes)
    return r


def grouped(level, observations):
    return [account(level, k, v) for k, v in groups(observations, KEYS[level]).items()]


class ContextTests(unittest.TestCase):
    def test_duration_collision_is_separated(self):
        a = [fact(qtrs="1"), fact("F2", qtrs="2", value="200")]
        self.assertEqual(grouped("K0", a)[0]["mixed_duration"], 1)
        self.assertEqual(len(grouped("K1", a)), 2)

    def test_instant_and_duration_are_different(self):
        a = [fact(qtrs="0"), fact("F2", qtrs="4", value="200")]
        self.assertEqual(grouped("K0", a)[0]["mixed_duration"], 1)

    def test_unit_collision_is_separated(self):
        a = [fact(), fact("F2", uom="shares", value="200")]
        self.assertEqual(grouped("K1", a)[0]["mixed_units"], 1)
        self.assertEqual(len(grouped("K2", a)), 2)

    def test_taxonomy_collision_is_separated(self):
        a = [fact(), fact("F2", version="us-gaap/2025")]
        self.assertEqual(grouped("K2", a)[0]["mixed_taxonomy"], 1)
        self.assertEqual(len(grouped("K3", a)), 2)

    def test_segment_and_coreg_contexts_retained(self):
        for field in ["segment_hash", "coreg_hash"]:
            a = [fact(), fact("F2", **{field: "a" * 64})]
            self.assertEqual(grouped("K3", a)[0]["mixed_segment_coreg"], 1)
            self.assertEqual(len(grouped("K4", a)), 2)

    def test_accession_is_part_of_full_source_identity(self):
        a = [fact(), fact("F2", adsh="0000320193-26-000021", value="110")]
        self.assertEqual(grouped("K4", a)[0]["mixed_accession"], 1)
        self.assertEqual(len(grouped("K5", a)), 2)

    def test_equal_numeric_tokens_are_equal(self):
        a = [fact(value="1.0"), fact("F2", segment_hash="a" * 64, value="1.0000")]
        self.assertEqual(grouped("K0", a)[0]["distinct_known_values"], 1)
        self.assertEqual(grouped("K0", a)[0]["numeric_conflict"], 0)

    def test_zero_is_known_and_missing_is_not_zero(self):
        a = [
            fact(value="0"),
            fact("F2", value="", value_state="MISSING", segment_hash="a" * 64),
        ]
        r = grouped("K0", a)[0]
        self.assertEqual(r["known_records"], 1)
        self.assertEqual(r["missing_records"], 1)
        self.assertEqual(r["distinct_known_values"], 1)

    def test_missing_winner_does_not_imply_numeric_agreement(self):
        a = [
            fact(),
            fact("F2", adsh="0000320193-26-000021", value="", value_state="MISSING"),
        ]
        r = grouped("K0", a)[0]
        self.assertEqual(r["numeric_disagreements"], 0)
        self.assertEqual(r["compared_known_records"], 0)
        self.assertEqual(r["unknown_comparison_records"], 2)

    def test_signed_values_retained(self):
        r = grouped(
            "K0", [fact(value="-10"), fact("F2", segment_hash="a" * 64, value="10")]
        )[0]
        self.assertEqual(r["distinct_known_values"], 2)
        self.assertEqual(r["numeric_disagreements"], 1)

    def test_latest_accession_multiple_contexts_abstain(self):
        r = grouped("K0", [fact(), fact("F2", qtrs="1")])[0]
        self.assertEqual(r["latest_accession_contexts"], 2)
        self.assertEqual(r["conservative_abstain"], 1)

    def test_same_timestamp_tie_break_is_deterministic(self):
        a = [fact(), fact("F2", adsh="0000320193-26-000021", value="9")]
        self.assertEqual(grouped("K0", a)[0]["winner_fact"], "F2")
        self.assertEqual(grouped("K0", list(reversed(a)))[0]["winner_fact"], "F2")

    def test_complete_context_tie_break_is_authored(self):
        a = [fact(), fact("F2", segment_hash="a" * 64, value="9")]
        self.assertEqual(grouped("K0", a)[0]["winner_fact"], "F2")

    def test_rows_beyond_one_decrease_with_context(self):
        a = [fact(), fact("F2", qtrs="1"), fact("F3", qtrs="1", uom="shares")]
        counts = [
            sum(r["rows_beyond_one"] for r in grouped(level, a)) for level in KEYS
        ]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(counts[-1], 0)

    def test_conflicting_group_count_need_not_decrease(self):
        a = [
            fact(qtrs="1", value="1"),
            fact("F2", qtrs="1", adsh="0000320193-26-000021", value="2"),
            fact("F3", qtrs="2", value="3"),
            fact("F4", qtrs="2", adsh="0000320193-26-000021", value="4"),
        ]
        self.assertEqual(sum(r["numeric_conflict"] for r in grouped("K0", a)), 1)
        self.assertEqual(sum(r["numeric_conflict"] for r in grouped("K1", a)), 2)


class SourceTests(unittest.TestCase):
    def base(self):
        num = dict(
            adsh="0000320193-26-000020",
            tag="Assets",
            version="us-gaap/2026",
            ddate="20260630",
            qtrs="0",
            uom="USD",
            segments="",
            coreg="",
            value="100",
        )
        sub = {
            num["adsh"]: dict(
                cik="320193",
                form="10-Q",
                filed="20260731",
                accepted="2026-07-31 06:01:00.0",
                period="20260630",
                fy="2026",
                fp="Q3",
                fye="0930",
                prevrpt="0",
            )
        }
        return num, sub

    def test_portable_fractional_timestamp(self):
        for suffix in ["", ".0", ".000", ".123456"]:
            value = accepted("2026-07-31 06:01:00" + suffix)
            self.assertEqual(
                value,
                "2026-07-31 06:01:00."
                + ("123456" if suffix == ".123456" else "000000"),
            )

    def test_invalid_timestamp_and_unverified_timezone_rejected(self):
        for token in [
            "2026-02-30 00:00:00",
            "2026-07-31T06:01:00",
            "2026-07-31 06:01:00Z",
            "2026-07-31 06:01:00.1234567",
        ]:
            self.assertIsNone(accepted(token))

    def test_strict_date_and_leap_boundary(self):
        self.assertEqual(date("20240229"), "20240229")
        self.assertIsNone(date("20250229"))
        self.assertIsNone(date("2026-06-30"))

    def test_numeric_missing_invalid_signed_and_zero(self):
        self.assertEqual(numeric(""), ("MISSING", ""))
        self.assertEqual(numeric("NaN"), ("INVALID", ""))
        self.assertEqual(numeric("0"), ("KNOWN", "0"))
        self.assertEqual(numeric("-1.25"), ("KNOWN", "-1.25"))

    def test_full_key_uses_numeric_quarter_identity(self):
        r, s = self.base()
        r["qtrs"] = "1"
        a = full_identity(r)
        r["qtrs"] = "1.0"
        self.assertEqual(a, full_identity(r))

    def test_whole_duplicate_group_quarantined(self):
        r, s = self.base()
        key = full_identity(r)
        for value in ["100", "200"]:
            r["value"] = value
            actual = project(
                r,
                s,
                set(),
                {(r["tag"], r["version"])},
                Counter({(r["adsh"], r["tag"], r["version"]): 1}),
                {key},
            )
            self.assertEqual(actual["state"], "DUPLICATE_FULL_IDENTITY")

    def test_presentation_repetition_is_not_fact_duplicate(self):
        r, s = self.base()
        actual = project(
            r,
            s,
            set(),
            {(r["tag"], r["version"])},
            Counter({(r["adsh"], r["tag"], r["version"]): 3}),
            set(),
        )
        self.assertEqual(actual["state"], "ELIGIBLE")
        self.assertEqual(actual["pre_rows"], "3")

    def test_missing_presentation_is_explicit(self):
        r, s = self.base()
        actual = project(r, s, set(), {(r["tag"], r["version"])}, Counter(), set())
        self.assertEqual(actual["state"], "MISSING_PRE_PRESENCE")

    def test_missing_tag_identity_is_explicit(self):
        r, s = self.base()
        actual = project(r, s, set(), set(), Counter(), set())
        self.assertEqual(actual["state"], "MISSING_TAG_IDENTITY")

    def test_sub_duplicate_is_unavailable(self):
        r, s = self.base()
        actual = project(r, s, {r["adsh"]}, set(), Counter(), set())
        self.assertEqual(actual["state"], "SUB_IDENTITY_OR_DATE_UNAVAILABLE")

    def test_standard_quoted_tsv_preserves_tabs_and_newlines(self):
        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr(
                "num.txt",
                "adsh\\tvalue\\tfootnote\\n".replace("\\t", "\t").replace("\\n", "\n")
                + 'a\t1\t"quoted\tfield\nwith newline"\n',
            )
        with ZipFile(io.BytesIO(buffer.getvalue())) as archive:
            actual = list(rows(archive, "num.txt"))
            self.assertEqual(len(actual), 1)
            self.assertEqual(actual[0]["footnote"], "quoted\tfield\nwith newline")


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.r = dict(
            purpose="current_fact",
            **{
                k: v
                for k, v in fact().items()
                if k
                in [
                    "cik",
                    "adsh",
                    "tag",
                    "version",
                    "ddate",
                    "qtrs",
                    "uom",
                    "segment_hash",
                    "coreg_hash",
                ]
            }
        )
        self.f = [fact()]

    def test_unique_current_context_qualified(self):
        a = answer(self.r, self.f)
        self.assertEqual(a["status"], "ACCEPTED_QUALIFIED")
        self.assertEqual(a["source_truth"], "UNESTABLISHED")
        self.assertEqual(a["value"], "100")

    def test_incomplete_context_abstains(self):
        for field in ["adsh", "qtrs", "uom", "version", "segment_hash", "coreg_hash"]:
            r = dict(self.r)
            r.pop(field)
            self.assertEqual(answer(r, self.f)["status"], "ABSTAIN")

    def test_missing_not_zero(self):
        self.f[0].update(value="", value_state="MISSING")
        self.assertEqual(answer(self.r, self.f)["status"], "UNAVAILABLE")

    def test_duplicate_or_absent_source_abstains(self):
        self.assertEqual(answer(self.r, self.f * 2)["status"], "ABSTAIN")
        self.assertEqual(answer(self.r, [])["status"], "ABSTAIN")

    def test_boolean_quarter_field_abstains(self):
        self.assertEqual(answer(dict(self.r, qtrs=True), self.f)["status"], "ABSTAIN")

    def test_unsupported_financial_or_historical_inferences_rejected(self):
        for purpose in [
            "formal_restatement",
            "historical_features",
            "exact_fiscal_dates",
            "forecast_accuracy",
            "investment_advice",
        ]:
            self.assertEqual(
                answer(dict(self.r, purpose=purpose), self.f)["status"], "REJECTED"
            )


if __name__ == "__main__":
    unittest.main()
