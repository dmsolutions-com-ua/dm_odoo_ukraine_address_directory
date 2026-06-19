# Geodata Connector Testing (dm_test_geodata_connector)

Test-only module: a mock API layer plus unit tests for the Geodata modules.
Install only in test/CI databases.

- `dm.geodata.api.credential` mock (`geodata_api_mock.py`): when the
  `geodata.test.mock_api` config parameter is set, API calls return canned
  data — tests/tours run with **no network**.
- Tests cover: address formatting (UA/EN), ingestion dedup (#12), query
  normalization / space handling (#17), manual-edit UX (no silent clearing,
  #16), and security (plain internal user can apply via sudo service #1/#2,
  multi-company rules #4).
- Demo data (credential `active=False`, sample addresses) is declared under
  the `demo` manifest key (not `data`).
