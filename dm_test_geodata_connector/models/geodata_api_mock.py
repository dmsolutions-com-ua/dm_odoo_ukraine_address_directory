from odoo import models

# Готові payload-и API (дзеркалять doc/API_*_Example_Response.json), що
# використовуються при увімкненому mock-прапорці, щоб тести/тури йшли без мережі.
_MOCK_CITY_KYIV = {
    "st_moniker": "mock-city-moniker-kyiv",
    "Id": 1, "City": "Київ", "SettlementType": "місто",
    "Region": "Київ", "Area": False, "Suburb": "Печерськ",
    "KOATUU": "8000000000", "KATO": "UA80000000000093317",
    "PhoneCode": "044", "IsOCentre": True, "IsRCentre": False,
    "Lat": "50.450412", "Long": "30.523487",
    "HromadaOld": "Стара громада", "SettlementTypeOld": "містечко",
    "CityString": "місто Київ, Київська обл.",
}
_MOCK_STREET = {
    "house_moniker": "mock-street-moniker",
    "StreetId": 137212, "Street": "Хрещатик", "StreetType": "вул.",
    "StreetTypeOld": None, "StreetOld": None,
    "StreetString": "вул. Хрещатик",
}
_MOCK_HOUSE = {
    "HouseId": 326381, "HouseNum": "1", "HouseNumAdd": None,
    "Index_": "01001", "Lat": "50.4501", "Long": "30.5234",
    "CityDistrict": "Шевченківський",
    "MetroName": "Золоті ворота", "MetroLine": "Сирецько-Печерська",
    "MetroDistance": "443.2", "HouseString": "1",
}
_MOCK_FULL = {
    "Id": 999001, "AddressString": "місто Київ, вул. Хрещатик, 1Б",
    "City": "Київ", "SettlementType": "місто",
    "Street": "Хрещатик", "StrType": "вул.", "HouseNum": "1", "HouseNumAdd": "Б",
    "CityDistrict": "Шевченківський",
    "Index_": "01001", "Region": "Київ", "KOATUU": "8000000000",
    "Lat_": "50.4501", "Long_": "30.5234",
}
# Транслітерований (lang=en_US) варіант _MOCK_FULL — API повертає EN-значення в
# тих самих ключах; літерний суфікс будинку повертається малими ("b").
_MOCK_FULL_EN = {
    "Id": 999001, "AddressString": "misto Kyiv, vul. Khreshchatyk, 1b",
    "City": "Kyiv", "SettlementType": "misto",
    "Street": "Khreshchatyk", "StrType": "vul.", "HouseNum": "1", "HouseNumAdd": "b",
    "CityDistrict": "Shevchenkivskyi",
    "Index_": "01001", "Region": "Kyiv", "KOATUU": "8000000000",
}
_MOCK_USER_INFO = {"Email": "mock@test.com", "Balans": 100.0}


class GeodataApiCredentialMock(models.Model):
    _inherit = "dm.geodata.api.credential"

    def _mock_enabled(self):
        return self.env["ir.config_parameter"].sudo().get_param("geodata.test.mock_api")

    def _api_request(self, endpoint, params=None, method="GET", _retried=False, silent=True):
        if not self._mock_enabled():
            return super()._api_request(
                endpoint, params=params, method=method, _retried=_retried, silent=silent
            )
        params = params or {}
        query = (params.get("sRequest") or "").lower()
        if endpoint == "api/Account/UserInfo":
            return dict(_MOCK_USER_INFO)
        if endpoint == "api/Cities":
            # Шлях переотримання: пошук за КАТОТТГ/КОАТУУ (sPostCode).
            if params.get("sPostCode"):
                return [dict(_MOCK_CITY_KYIV)]
            return [dict(_MOCK_CITY_KYIV)] if "ки" in query else []
        if endpoint == "api/Streets":
            return [dict(_MOCK_STREET)] if "хрещ" in query else []
        if endpoint == "api/Houses":
            return [dict(_MOCK_HOUSE)] if query and query[0].isdigit() else []
        if endpoint in ("api/FullAddress", "api/Address"):
            if not query:
                return []
            lang = (params.get("sLang") or "").lower()
            return dict(_MOCK_FULL_EN) if lang.startswith("en") else dict(_MOCK_FULL)
        return []

    def _refresh_token(self):
        if self._mock_enabled():
            self._set_token("mock-token")
            return True
        return super()._refresh_token()
