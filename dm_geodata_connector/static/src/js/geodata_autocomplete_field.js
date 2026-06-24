/** @odoo-module **/

import { Component, useState, useRef, onWillUnmount, onMounted, onPatched, useExternalListener } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Self-contained address autocomplete field widget (replaces kw_widget_autocomplete).
 * Client-side debounce, min_chars and skip-on-space/unchanged dedup so a space
 * keystroke never fires an extra (billed) API request (AUDIT #17). Searches only
 * when the country is Ukraine (test #1).
 */
export class GeodataAutocompleteField extends Component {
    static template = "dm_geodata_connector.GeodataAutocompleteField";
    static props = {
        ...standardFieldProps,
        options: { type: Object, optional: true },
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ suggestions: [], open: false, activeIndex: -1 });
        this.listRef = useRef("list");
        this.inputRef = useRef("input");
        this.rootRef = useRef("root");
        // Закриваємо список, коли користувач клікає будь-де поза віджетом, навіть
        // на нефокусованій ділянці, що не зняла б фокус з input (виправляє
        // залишання списку відкритим при втраті фокуса).
        useExternalListener(window, "pointerdown", this.onOutsidePointerDown.bind(this));
        // Унікальний id, щоб aria-activedescendant вказував на потрібну опцію навіть
        // за кількох полів автопідказки (місто/вулиця/пошук) на одній формі.
        GeodataAutocompleteField._seq = (GeodataAutocompleteField._seq || 0) + 1;
        this.listId = `o_geodata_list_${GeodataAutocompleteField._seq}`;
        this._lastQuery = null;
        this._timer = null;
        // DOM-input НЕКОНТРОЛЬОВАНИЙ: ми ніколи не біндимо t-att-value (це
        // перезаписувало б у польоті натиснуті клавіші застарілим значенням запису
        // під час async onchange і губило б символи при швидкому наборі). Натомість
        // ми пушимо значення запису в DOM лише коли користувач у нього активно не
        // друкує. Застосування підказки виставляє значення DOM явно наприкінці
        // onSelect (без гонок таймінгу patch).
        onMounted(() => this._syncInputValue());
        onPatched(() => {
            this._syncInputValue();
            this._positionSuggestions();
        });
        onWillUnmount(() => {
            if (this._timer) {
                clearTimeout(this._timer);
            }
        });
    }

    // Випадний список шириною за вмістом (див. SCSS) може бути ширшим за поле.
    // Вимірюємо натуральну ширину, тоді обираємо сторону якоря (ліворуч/праворуч
    // від поля) і viewport-залежний max-width так, щоб список ніколи не вилазив за
    // жоден край екрана. За замовчуванням — ліворуч (як рідні списки Odoo);
    // праворуч перемикаємось лише коли там більше місця.
    _positionSuggestions() {
        const list = this.listRef.el;
        const anchor = this.rootRef.el;
        if (!list || !anchor) {
            return;
        }
        const MARGIN = 4; // зазор від краю вьюпорта
        const field = anchor.getBoundingClientRect();
        const vw = document.documentElement.clientWidth;
        const spaceRight = vw - field.left - MARGIN; // якір ліворуч -> росте праворуч
        const spaceLeft = field.right - MARGIN; // якір праворуч -> росте ліворуч

        // Натуральна ширина вмісту без обмежень (width:max-content + нерозірваний
        // text-truncate дають реальну ширину найдовшого пункту).
        list.style.maxWidth = "none";
        list.style.left = "0";
        list.style.right = "auto";
        const natural = list.getBoundingClientRect().width;

        // Без сталого ліміту: ширина за вмістом (min-width:100% тримає ≥ поле),
        // інлайн max-width = лише доступний простір, щоб не вилізти за екран.
        // За замовчуванням якір ліворуч; праворуч — лише коли вміст не вміщується
        // праворуч, а ліворуч місця більше.
        if (natural <= spaceRight || spaceRight >= spaceLeft) {
            list.style.left = "0";
            list.style.right = "auto";
            list.style.maxWidth = `${spaceRight}px`;
        } else {
            list.style.left = "auto";
            list.style.right = "0";
            list.style.maxWidth = `${spaceLeft}px`;
        }
    }

    _syncInputValue() {
        const el = this.inputRef.el;
        if (!el || this.value === el.value) {
            return;
        }
        // Не затираємо те, що користувач активно друкує; синхронізуємо зі запису
        // лише при монтуванні, перезавантаженні запису, або коли поле очищене
        // onchange іншого поля (у всіх цих випадках воно не у фокусі).
        if (document.activeElement === el) {
            return;
        }
        el.value = this.value;
    }

    get options() {
        return this.props.options || {};
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    get minChars() {
        return this.options.min_chars || 3;
    }

    // Амбер-індикатор: поле має непорожнє значення, введене вручну (його рівень не
    // підтверджений за довідником), підказку увімкнено, і країна — Україна (модуль
    // обробляє лише українські адреси).
    get isManual() {
        const data = this.props.record.data;
        const hintField = this.options.hint_field;
        const verifiedField = this.options.verified_field;
        if (!verifiedField) {
            return false;
        }
        const hintOn = !hintField || data[hintField];
        // Підказка ручного введення показується строго для України (форма має
        // вказати це через country_code); ніколи на не-UA / невідомій країні.
        const strictUa = data.country_code === "UA";
        return Boolean(strictUa && hintOn && this.value && !data[verifiedField]);
    }

    // Підказка індикатора «введено вручну» — перекладається за мовою користувача.
    get manualHintTitle() {
        return _t("Entered manually (not found in the directory)");
    }

    get countryOk() {
        const data = this.props.record.data;
        // Дозволяємо пошук, коли форма не несе придатного country_code тут;
        // остаточне рішення про Україну сервер ухвалює за country_id (надійно на
        // моделях, де related country_code не завантажений у запис форми).
        if (!("country_code" in data) || !data.country_code) {
            return true;
        }
        return data.country_code === "UA";
    }

    onInput(ev) {
        this.state.activeIndex = -1;
        // НЕ комітимо в запис на кожну літеру (це тригерило серверний onchange-RPC
        // під час набору). Значення в запис іде лише на blur (_commitNow) або при
        // виборі підказки (onSelect). Живий пошук читає сире значення DOM напряму.
        this._scheduleSearch(ev.target.value);
    }

    _commitNow() {
        const el = this.inputRef.el;
        if (el && el.value !== this.value) {
            this.props.record.update({ [this.props.name]: el.value });
        }
    }

    onBlur() {
        // Скидаємо останнє введене значення, щоб воно не губилось при швидкому blur/збереженні.
        this._commitNow();
        setTimeout(() => (this.state.open = false), 200);
    }

    onOutsidePointerDown(ev) {
        if (this.state.open && this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
            this.state.open = false;
        }
    }

    onKeydown(ev) {
        if (!this.state.open || !this.state.suggestions.length) {
            return;
        }
        const n = this.state.suggestions.length;
        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                this.state.activeIndex = (this.state.activeIndex + 1) % n;
                this._scrollActive();
                break;
            case "ArrowUp":
                ev.preventDefault();
                this.state.activeIndex = (this.state.activeIndex - 1 + n) % n;
                this._scrollActive();
                break;
            case "Enter": {
                ev.preventDefault();
                const idx = this.state.activeIndex >= 0 ? this.state.activeIndex : 0;
                this.onSelect(this.state.suggestions[idx]);
                break;
            }
            case "Escape":
                this.state.open = false;
                break;
        }
    }

    onItemHover(index) {
        this.state.activeIndex = index;
    }

    _scrollActive() {
        try {
            const el = this.listRef.el && this.listRef.el.children[this.state.activeIndex];
            if (el) {
                el.scrollIntoView({ block: "nearest" });
            }
        } catch {
            // нефатально
        }
    }

    _normalize(raw) {
        return (raw || "").trim().replace(/\s+/g, " ");
    }

    _scheduleSearch(raw) {
        const trimmed = this._normalize(raw);
        if (!this.countryOk || trimmed.length < this.minChars) {
            this.state.suggestions = [];
            this.state.open = false;
            return;
        }
        if (trimmed === this._lastQuery) {
            return; // незмінений обрізаний запит (напр. лише пробіл) -> без запиту
        }
        if (this._timer) {
            clearTimeout(this._timer);
        }
        this._timer = setTimeout(() => this._search(trimmed), this.options.debounce_ms || 250);
    }

    _m2oId(value) {
        if (!value) {
            return false;
        }
        if (typeof value === "number") {
            return value;
        }
        return value.id || (Array.isArray(value) ? value[0] : false);
    }

    _depValues() {
        const data = this.props.record.data;
        const dep = {};
        if ("country_code" in data) {
            dep.country_code = data.country_code || "";
        }
        for (const key of ["geodata_city_moniker", "geodata_street_moniker", "city", "street"]) {
            if (key in data && data[key]) {
                dep[key] = data[key];
            }
        }
        if ("geodata_address_id" in data && data.geodata_address_id) {
            dep.geodata_address_id = this._m2oId(data.geodata_address_id);
        }
        if (data.state_id) {
            dep.state_id = this._m2oId(data.state_id);
        }
        // country_id завжди присутній в адресному блоці; це робить серверний гейт
        // країни надійним на моделях, де related country_code не завжди завантажений
        // у запис форми (напр. crm.lead / res.company).
        if (data.country_id) {
            dep.country_id = this._m2oId(data.country_id);
        }
        return dep;
    }

    async _search(trimmed) {
        this._lastQuery = trimmed;
        const method = this.options.source_method;
        if (!method) {
            return;
        }
        const res = await this.orm.call(this.props.record.resModel, method, [
            trimmed,
            this._depValues(),
        ]);
        this.state.suggestions = res || [];
        this.state.open = Boolean(res && res.length);
        this.state.activeIndex = -1;
    }

    async onSelect(suggestion) {
        this.state.open = false;
        this._lastQuery = null;
        const data = this.props.record.data;
        const applyMethod = this.options.on_select_method || "apply_address";
        const recordId = this.props.record.resId || false;
        const currentAddressId = this._m2oId(data.geodata_address_id);
        const result = await this.orm.call(this.props.record.resModel, applyMethod, [
            recordId,
            suggestion.data,
            currentAddressId,
        ]);

        const vals = {};
        if ("geodata_autocomplete_active" in data) {
            vals.geodata_autocomplete_active = true;
        }
        // Прогресивний однорядковий пошук: тримаємо вибране значення в цьому полі,
        // щоб користувач міг продовжувати набір (місто -> вулиця -> будинок) — test #1.
        if (this.options.progressive) {
            vals[this.props.name] = suggestion.value;
        }
        for (const [key, val] of Object.entries(result || {})) {
            if (!(key in data)) {
                continue;
            }
            // Визначаємо many2one узагальнено з метаданих поля запису (а не зі
            // зашитого списку імен), щоб ремапнуті поля власника працювали на кожній
            // моделі: country_id/state_id (partner/crm/company), private_country_id/
            // private_state_id (hr.employee), country/state (res.bank) тощо.
            const fieldDef = this.props.record.fields[key];
            if (fieldDef && fieldDef.type === "many2one") {
                // У пам'яті значення many2one в Odoo 19 — це { id, display_name }.
                if (!val) {
                    vals[key] = false;
                } else if (typeof val === "object") {
                    vals[key] = val;
                } else {
                    vals[key] = { id: val };
                }
            } else {
                vals[key] = val;
            }
        }
        if (Object.keys(vals).length) {
            await this.props.record.update(vals);
        }
        if ("geodata_autocomplete_active" in data) {
            await this.props.record.update({ geodata_autocomplete_active: false });
        }
        // Пушимо застосоване значення в DOM явно тепер, коли запис його містить.
        // Робимо це тут (а не через patch-кероване _syncInputValue), щоб працювало
        // незалежно від таймінгу фокуса/patch: вибір через Enter лишає input у
        // фокусі, і наступний blur не має повторно записати застаріле значення.
        // Повертаємо фокус на поле й ставимо каретку в кінець, щоб користувач міг
        // продовжувати набір (місто -> вулиця -> будинок) саме там, де зупинився.
        const el = this.inputRef.el;
        if (el) {
            el.value = this.value;
            el.focus();
            const end = el.value.length;
            el.setSelectionRange(end, end);
        }
    }
}

export const geodataAutocompleteField = {
    component: GeodataAutocompleteField,
    supportedTypes: ["char"],
    extractProps: ({ options, attrs }) => ({
        options: options || {},
        placeholder: (attrs && attrs.placeholder) || "",
    }),
};

registry.category("fields").add("geodata_autocomplete", geodataAutocompleteField);
