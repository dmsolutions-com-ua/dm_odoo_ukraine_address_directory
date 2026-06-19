from odoo.tests.common import Form, TransactionCase


class TestClearingUx(TransactionCase):
    """Model v1.5: a manual settlement-level edit (clear or change) detaches the
    validated Geodata link live in-form; a non-divergent edit keeps it; an
    explicit reset always detaches."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ua = cls.env.ref("base.ua", raise_if_not_found=False)
        cls.address = cls.env["dm.geodata.address"].create({
            "geodata_id": 600001,
            "city": "Київ", "settlement_type": "місто",
            "str_type": "вул.", "street": "Хрещатик", "house_num": "1",
            "kato": "UA80000000000093317",
        })
        # Місто, збережене на партнері, має збігатися з валідованим значенням, отриманим
        # з адреси (_city_part -> "місто Київ"), щоб no-op не відв'язував.
        cls.partner = cls.env["res.partner"].create({
            "name": "Clearing Test",
            "country_id": cls.ua.id if cls.ua else False,
            "city": "місто Київ",
            "zip": "01001",
            "geodata_address_id": cls.address.id,
        })

    def test_non_divergent_edit_keeps_link(self):
        """A sub-settlement edit (zip) must not detach the link or codes."""
        self.partner.write({"zip": "01002"})
        self.assertTrue(
            self.partner.geodata_address_id,
            "Non-divergent manual edit must not detach the Geodata address",
        )
        self.assertTrue(
            self.partner.geodata_kato,
            "Document codes must remain on a non-divergent edit",
        )

    def test_clearing_city_detaches_live(self):
        """The actual bug fix: clearing the settlement in-form (onchange, before
        save) must drop the link so the Address Information block clears."""
        form = Form(self.partner)
        form.city = ""
        # onchange уже відпрацював усередині Form -> зв'язок зник до збереження.
        self.assertFalse(
            form.geodata_address_id,
            "Clearing the settlement must detach the link live (onchange)",
        )

    def test_changing_city_detaches_live(self):
        """Changing the settlement to another value detaches just as clearing."""
        form = Form(self.partner)
        form.city = "Інше місто"
        self.assertFalse(
            form.geodata_address_id,
            "Changing the settlement must detach the link live (onchange)",
        )

    def test_norm_strips_old_paren(self):
        # Порівняння має ігнорувати суфікс "(стара назва)", щоб перемикання show_old_names
        # не сприймалось як ручна правка.
        self.assertEqual(
            self.partner._norm("вул. Хрещатик (вул. Стара)"),
            self.partner._norm("вул. Хрещатик"),
        )

    def test_explicit_reset_detaches_and_deletes(self):
        # Строге 1:1: скидання відв'язує І видаляє осиротілий приватний рядок.
        self.partner.action_geodata_reset()
        self.assertFalse(self.partner.geodata_address_id)
        self.assertFalse(self.address.exists(), "Private address row deleted on reset")
