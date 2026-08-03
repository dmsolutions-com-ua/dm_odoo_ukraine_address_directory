from odoo.tests.common import Form, TransactionCase


class TestCountryAsAddressLevel(TransactionCase):
    """The country is a full address level: switching it to an explicitly
    foreign one detaches the validated Geodata link and clears the address
    block - live in the form (onchange) AND on save / import (write).

    Two narrowings are deliberate and pinned here: an EMPTY country is not a
    trigger (usually transient), and without a directory link nothing is
    touched, so a manually typed foreign address survives."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ua = cls.env.ref("base.ua")
        cls.pl = cls.env.ref("base.pl")
        # Області України синхронізуються при встановленні (post_init_hook).
        cls.ua_state = cls.env["res.country.state"].search(
            [("country_id", "=", cls.ua.id)], limit=1)

    def _linked_partner(self):
        """Партнер з українською адресою, обраною з довідника."""
        address = self.env["dm.geodata.address"].create({
            "geodata_id": 700001,
            "region": "Київ", "city": "Київ", "settlement_type": "місто",
            "str_type": "вул.", "street": "Хрещатик", "house_num": "1",
        })
        return self.env["res.partner"].create({
            "name": "Country Level Test",
            "country_id": self.ua.id,
            "state_id": self.ua_state.id,
            "city": "місто Київ",
            "street": "вул. Хрещатик, 1",
            "zip": "01001",
            "area": "Печерський р-н",
            "hromada": "Київська гр.",
            "geodata_address_id": address.id,
        }), address

    # ------------------------------------------------------------------
    # Наживо у формі (onchange) — головна відмінність цієї зміни
    # ------------------------------------------------------------------
    def test_foreign_country_clears_block_live(self):
        partner, _addr = self._linked_partner()
        form = Form(partner)
        form.country_id = self.pl
        # onchange уже відпрацював усередині Form -> усе зникло ДО збереження.
        self.assertFalse(form.geodata_address_id,
                         "іноземна країна має знімати прив'язку наживо")
        self.assertFalse(form.city)
        self.assertFalse(form.street)
        self.assertFalse(form.zip)
        self.assertFalse(form.area)
        self.assertFalse(form.hromada)
        self.assertFalse(form.state_id)

    def test_empty_country_keeps_everything(self):
        # Порожня країна — часто транзитний стан, а не «адреса більше не UA».
        partner, _addr = self._linked_partner()
        form = Form(partner)
        form.country_id = self.env["res.country"]
        self.assertTrue(form.geodata_address_id,
                        "порожня країна не має знімати прив'язку")
        self.assertEqual(form.city, "місто Київ")

    def test_manual_foreign_address_survives(self):
        # Без прив'язки чистити нема чого: ручний ввід не наш, не чіпаємо.
        partner = self.env["res.partner"].create({
            "name": "Manual Foreign",
            "country_id": self.ua.id,
            "city": "Warszawa",
            "street": "Marszalkowska 1",
        })
        form = Form(partner)
        form.country_id = self.pl
        self.assertEqual(form.city, "Warszawa",
                         "вручну введена адреса не має стиратись")
        self.assertEqual(form.street, "Marszalkowska 1")

    # ------------------------------------------------------------------
    # Шлях write: імпорт / RPC / код — onchange там не виконується
    # ------------------------------------------------------------------
    def test_foreign_country_clears_on_write_without_state(self):
        """Саме та дірка, якої не закривав побічний каскад через область.

        Ядро Odoo обнуляє `state_id` лише в onchange, тож при прямому записі
        країни у `vals` немає жодного іншого рівня — і до цієї зміни адреса
        лишалась українською під іноземною країною.
        """
        partner, _addr = self._linked_partner()
        partner.write({"country_id": self.pl.id})
        self.assertFalse(partner.geodata_address_id)
        self.assertFalse(partner.city)
        self.assertFalse(partner.street)
        self.assertFalse(partner.zip)
        self.assertFalse(partner.area)
        self.assertFalse(partner.hromada)

    def test_write_same_country_keeps_everything(self):
        partner, _addr = self._linked_partner()
        partner.write({"country_id": self.ua.id})
        self.assertTrue(partner.geodata_address_id)
        self.assertEqual(partner.city, "місто Київ")

    def test_write_empty_country_keeps_everything(self):
        partner, _addr = self._linked_partner()
        partner.write({"country_id": False})
        self.assertTrue(partner.geodata_address_id)
        self.assertEqual(partner.city, "місто Київ")

    def test_write_without_link_keeps_manual_address(self):
        partner = self.env["res.partner"].create({
            "name": "Manual Foreign Write",
            "country_id": self.ua.id,
            "city": "Warszawa",
        })
        partner.write({"country_id": self.pl.id})
        self.assertEqual(partner.city, "Warszawa")

    # ------------------------------------------------------------------
    # Нестандартні імена полів у власників (мапа _geodata_fields)
    # ------------------------------------------------------------------
    def test_other_owner_model_uses_its_own_field_names(self):
        """res.bank зве поле країни `country`, а не `country_id`."""
        Bank = self.env["res.bank"]
        if "geodata_address_id" not in Bank._fields:
            self.skipTest("dm_geodata_bank не встановлено в цій БД")
        address = self.env["dm.geodata.address"].create({
            "geodata_id": 700002,
            "region": "Київ", "city": "Київ", "settlement_type": "місто",
        })
        bank = Bank.create({
            "name": "Country Level Bank",
            "country": self.ua.id,
            "city": "місто Київ",
            "geodata_address_id": address.id,
        })
        bank.write({"country": self.pl.id})
        self.assertFalse(bank.geodata_address_id)
        self.assertFalse(bank.city)

    # ------------------------------------------------------------------
    # Предикат окремо: єдина відмінність від not _geodata_is_ua()
    # ------------------------------------------------------------------
    def test_left_ua_predicate_ignores_empty_country(self):
        partner, _addr = self._linked_partner()
        self.assertFalse(partner._geodata_country_left_ua())
        self.assertTrue(partner._geodata_country_left_ua(self.pl))
        self.assertFalse(partner._geodata_country_left_ua(
            self.env["res.country"]))
        self.assertFalse(partner._geodata_country_left_ua(self.ua))
