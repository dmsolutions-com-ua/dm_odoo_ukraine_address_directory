from odoo.tests.common import TransactionCase


class TestOldNamesReset(TransactionCase):
    """Regressions of the LEVEL RESETS on a REUSED dm.geodata.address.

    `_api_data_to_vals` deliberately drops absent (None) keys so that merging the
    city -> street -> house chain never wipes the levels a payload does not carry.
    The counterweight is the level resets in `update_from_api`: when a payload
    DEFINES a level, a missing key means "there is none", so the field is cleared.
    Whenever that pairing is incomplete, data of the previously selected address
    silently sticks — historical names, post index, coordinates, metro, …"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Geo = cls.env["dm.geodata.address"]

    # Місто з історичними назвами (район/громада/нас. пункт/тип).
    _CITY_WITH_OLD = {
        "Id": 1, "City": "Підлісне", "SettlementType": "село",
        "Region": "Харківська обл.", "Area": "Берестинський р-н",
        "Hromada": "Берестинська",
        "CityOld": "Червоне", "AreaOld": "Красноградський р-н",
        "HromadaOld": "Красноградська", "RegionOld": "Стара обл.",
        "SettlementTypeOld": "смт",
    }
    # Інше місто (Харків) БЕЗ історичних назв (ключі *Old відсутні).
    _CITY_NO_OLD = {
        "Id": 2, "City": "Харків", "SettlementType": "місто",
        "Region": "Харківська обл.", "Area": "Харківський р-н",
        "Hromada": "Харківська",
    }

    def _assert_no_old(self, addr):
        for f in ("city_old", "area_old", "hromada_old",
                  "region_old", "settlement_type_old"):
            self.assertFalse(
                addr[f], "%s must be cleared for a settlement without old names" % f)

    def test_reselect_city_clears_stale_old_names(self):
        addr = self.Geo.create_from_api(dict(self._CITY_WITH_OLD))
        self.assertEqual(addr.city_old, "Червоне")
        self.assertEqual(addr.area_old, "Красноградський р-н")
        # Перевибір ІНШОГО міста без історичних назв на ТОМУ Ж записі.
        addr.update_from_api(dict(self._CITY_NO_OLD))
        self.assertEqual(addr.city, "Харків")
        self._assert_no_old(addr)

    def test_full_address_clears_stale_old_names(self):
        # Шлях повної адреси: payload несе City+Street+House одразу (level=house),
        # де раніше clear-below не чистив settlement-old.
        full_a = dict(self._CITY_WITH_OLD,
                      Street="Центральна", StrType="вул.", HouseNum="5")
        addr = self.Geo.create_from_api(full_a)
        self.assertEqual(addr.hromada_old, "Красноградська")
        full_b = dict(self._CITY_NO_OLD,
                      Street="Сумська", StrType="вул.", HouseNum="1")
        addr.update_from_api(full_b)
        self.assertEqual(addr.city, "Харків")
        self.assertEqual(addr.street, "Сумська")
        self._assert_no_old(addr)

    def test_street_step_keeps_settlement(self):
        # Ланцюг: вибір вулиці (payload БЕЗ City) не скидає поселенські поля.
        addr = self.Geo.create_from_api(dict(self._CITY_WITH_OLD))
        addr.update_from_api({"StreetId": 50, "Street": "Центральна",
                              "StreetType": "вул."})
        self.assertEqual(addr.street, "Центральна")
        # Поселення (і його стара назва) збережені.
        self.assertEqual(addr.city, "Підлісне")
        self.assertEqual(addr.city_old, "Червоне")
        self.assertEqual(addr.area_old, "Красноградський р-н")

    def test_reselect_city_clears_stale_post_index(self):
        # Повна адреса з індексом, потім перевибір ІНШОГО міста (city-рівень без
        # Index_) на тому ж записі: старий поштовий індекс не має «прилипати».
        full_a = dict(self._CITY_WITH_OLD, Street="Центральна", StrType="вул.",
                      HouseNum="5", Index_="63322")
        addr = self.Geo.create_from_api(full_a)
        self.assertEqual(addr.post_index, "63322")
        addr.update_from_api(dict(self._CITY_NO_OLD))
        self.assertEqual(addr.city, "Харків")
        self.assertFalse(
            addr.post_index, "stale post index must be cleared on a new city")

    def test_reselect_city_clears_stale_terr_status(self):
        # Місто зі статусом ТОТ, потім інше місто без статусу на тому ж записі:
        # старий terr_status не має «прилипати».
        addr = self.Geo.create_from_api(dict(
            self._CITY_WITH_OLD, TerrStatus="Деокупована", KATO="UA1"))
        self.assertEqual(addr.terr_status, "Деокупована")
        addr.update_from_api(dict(self._CITY_NO_OLD))
        self.assertEqual(addr.city, "Харків")
        self.assertFalse(
            addr.terr_status, "stale territory status must be cleared on a new city")

    def test_reselect_city_clears_stale_metro_and_district(self):
        # Перевибір міста має чистити метро та район міста (нижчий рівень).
        addr = self.Geo.create_from_api(dict(
            self._CITY_WITH_OLD, CityDistrict="Шевченківський",
            MetroStation="Золоті ворота", MetroLine="Лінія 1"))
        self.assertEqual(addr.city_district, "Шевченківський")
        self.assertEqual(addr.metro_station, "Золоті ворота")
        addr.update_from_api(dict(self._CITY_NO_OLD))
        self.assertEqual(addr.city, "Харків")
        self.assertFalse(addr.city_district, "stale city district must be cleared")
        self.assertFalse(addr.metro_station, "stale metro must be cleared")
        self.assertFalse(addr.metro_line)

    def test_full_address_keeps_own_post_index(self):
        # Повна адреса несе власний Index_ — він має зберігатись (не скидатись
        # settlement-ресетом), бо vals.setdefault не перетирає наявне значення.
        full = dict(self._CITY_NO_OLD, Street="Сумська", StrType="вул.",
                    HouseNum="1", Index_="61000")
        addr = self.Geo.create_from_api(dict(self._CITY_WITH_OLD))
        addr.update_from_api(full)
        self.assertEqual(addr.post_index, "61000")

    def test_reselect_house_clears_stale_suffix(self):
        # Перевибір будинку без літери не лишає стару літеру.
        addr = self.Geo.create_from_api(dict(
            self._CITY_WITH_OLD, Street="Центральна", StrType="вул.",
            HouseNum="5", HouseNumAdd="А"))
        self.assertEqual(addr.house_num_add, "А")
        addr.update_from_api({"HouseId": 9, "HouseNum": "7"})
        self.assertEqual(addr.house_num, "7")
        self.assertFalse(addr.house_num_add, "stale house letter must be cleared")

    # ------------------------------------------------------------------
    # Рівень будинку володіє координатами, індексом і рядком будинку: payload
    # без них означає «їх немає», а не «лиши попередні».
    # ------------------------------------------------------------------
    def _addr_with_house_coords(self):
        """Адреса, де і населений пункт, і будинок мають координати."""
        addr = self.Geo.create_from_api(dict(
            self._CITY_NO_OLD, Lat_S="49.9935", Long_S="36.2304"))
        addr.update_from_api({"StreetId": 20, "Street": "Сумська", "StrType": "вул."})
        addr.update_from_api({
            "HouseId": 30, "HouseNum": "5", "Index_": "61000",
            "Lat": "49.995000", "Long": "36.231000",
            "MetroName": "Історичний музей", "MetroLine": "Холодногірсько-Заводська",
        })
        return addr

    def test_reselect_house_without_coords_clears_stale_ones(self):
        # Головний кейс зі звіту: новий будинок без координат лишав кнопки карт
        # із координатами попереднього.
        addr = self._addr_with_house_coords()
        self.assertEqual(addr.latitude, 49.995)

        addr.update_from_api({"HouseId": 31, "HouseNum": "7", "Index_": "61001"})
        self.assertEqual(addr.house_num, "7")
        self.assertFalse(addr.latitude, "координати попереднього будинку лишились")
        self.assertFalse(addr.longitude)
        # Наскрізно: рядок із кнопками карт у колонці деталей зникає.
        values = addr._api_template_values("ua")
        self.assertEqual(values["gd_lat"], "")
        self.assertEqual(values["gd_long"], "")

    def test_reselect_house_with_coords_applies_them(self):
        addr = self._addr_with_house_coords()
        addr.update_from_api({
            "HouseId": 31, "HouseNum": "7", "Lat": "50.000000", "Long": "36.240000"})
        self.assertEqual(addr.latitude, 50.0)
        self.assertEqual(addr.longitude, 36.24)

    def test_reselect_house_keeps_settlement_coords(self):
        # Координати населеного пункту — рівня міста, їх скидає лише вибір міста.
        addr = self._addr_with_house_coords()
        addr.update_from_api({"HouseId": 31, "HouseNum": "7"})
        self.assertEqual(addr.latitude_settlement, 49.9935)
        self.assertEqual(addr.longitude_settlement, 36.2304)

    def test_reselect_house_clears_stale_post_index(self):
        addr = self._addr_with_house_coords()
        self.assertEqual(addr.post_index, "61000")
        addr.update_from_api({"HouseId": 31, "HouseNum": "7"})
        self.assertFalse(addr.post_index, "індекс попереднього будинку лишився")

    def test_street_step_clears_stale_post_index_and_coords(self):
        # Вибір нової вулиці скидає і координати, і індекс попереднього будинку.
        addr = self._addr_with_house_coords()
        addr.update_from_api({"StreetId": 21, "Street": "Полтавський Шлях",
                              "StrType": "вул."})
        self.assertFalse(addr.post_index)
        self.assertFalse(addr.latitude)
        self.assertFalse(addr.house_num)
        # Населений пункт лишається тим самим.
        self.assertEqual(addr.city, "Харків")
        self.assertEqual(addr.latitude_settlement, 49.9935)
