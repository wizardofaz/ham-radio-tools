# Test Data

This directory contains sample input data and a simple smoke-test runner for the contest summary tool.

## Contents

- 'input/' -- version-controlled sample ADIF input files
- 'output/' -- generated output files from test runs
- 'test.cmd' -- Windows command script for a repeatable local test

## Notes

- Files in 'output/' are generated and ignored by git.
- The sample data is intended for development smoke testing, not for strict output regression testing.
- The committed 'qrz_cache.json' in 'input/' is a starting fixture, not a runtime cache file. The 'test.cmd'  
- copies it into 'output/' before running the tool, to test qrz lookups (only a few are missing) and cache
- updates. 