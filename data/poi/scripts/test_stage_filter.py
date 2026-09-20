#!/usr/bin/env python3
"""高中采集/清洗阶段回归：已确认的初中专属校区不得回流高中。"""
import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch = load("fetch_high_schools")
clean = load("build_high_levels_js")


class StageFilterTest(unittest.TestCase):
    def test_middle_only_campuses_are_rejected_by_both_stages(self):
        for name in fetch.MIDDLE_ONLY_CAMPUSES:
            self.assertFalse(fetch.is_high_candidate(name))
            self.assertFalse(clean.is_high_campus(name))

    def test_real_high_school_campus_is_retained(self):
        self.assertTrue(fetch.is_high_candidate("广州市真光中学(广钢校区)"))
        self.assertTrue(clean.is_high_campus("广州市真光中学(广钢校区)"))


if __name__ == "__main__":
    unittest.main()
