from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestEmployeePublicAccess(TransactionCase):
    """Некадровий користувач читає hr.employee лише через hr.employee.public.

    Збережені поля міксина без `groups` потрапляли в prefetch будь-якого
    звертання до працівника, і Odoo падав з «The fields geodata_address_id,
    area, hromada ... are not available for employee public profiles»
    (напр. при плануванні зустрічі з ліда). Поля адреси бачить лише кадровик.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plain_user = cls.env["res.users"].create({
            "name": "Geo Plain Employee",
            "login": "geo_hr_plain_user",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.hr_user = cls.env["res.users"].create({
            "name": "Geo HR Officer",
            "login": "geo_hr_officer",
            "group_ids": [(6, 0, [cls.env.ref("hr.group_hr_user").id])],
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Geo Employee",
            "user_id": cls.plain_user.id,
            "area": "Бучанський район",
            "hromada": "Бучанська громада",
        })

    def _as_plain(self):
        # Як у новому HTTP-запиті: кеш порожній, тож спрацьовує prefetch.
        self.env.invalidate_all()
        return self.env["hr.employee"].with_user(self.plain_user).browse(self.employee.id)

    def test_plain_user_reads_public_fields(self):
        self.assertEqual(self._as_plain().name, "Geo Employee")
        self.assertTrue(self._as_plain().resource_id)
        self.assertTrue(self._as_plain().work_contact_id)

    def test_plain_user_search_fetch_and_read(self):
        employees = self.env["hr.employee"].with_user(self.plain_user).search_fetch(
            [("id", "=", self.employee.id)])
        self.assertEqual(employees.ids, self.employee.ids)
        values = self._as_plain().read([])[0]
        self.assertNotIn("area", values)
        self.assertNotIn("geodata_address_id", values)

    def test_hr_user_sees_address_fields(self):
        employee = self.employee.with_user(self.hr_user)
        employee.write({"private_city": "Буча"})
        self.env.invalidate_all()
        values = employee.read(["area", "hromada", "geodata_address_id"])[0]
        self.assertEqual(values["area"], "Бучанський район")
        self.assertEqual(values["hromada"], "Бучанська громада")
