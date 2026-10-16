# Xanh SM — Mobile UI/UX Reconstruction Design Spec (V3 — Liquid Glass Material Architecture)

> **Document type:** screenshot-derived design system & implementation handoff  
> **Version:** 3.0 — 2026-10-16  
> **Language:** Vietnamese (`vi-VN`)  
> **Primary target:** mobile web/PWA, portrait, 360–430 CSS px; base reference viewport **375 × 812 CSS px** / **390 × 844 CSS px**  
> **Source of truth:** this `design.md` **plus the supplied screenshots**; screenshots take precedence for visual differences.  
> **Typography Baseline:** **Montserrat** (weights 400, 500, 600, 700) matching confirmed Xanh SM brand baseline.

---

## 1. Design System V3: Liquid Glass & Material Architecture

### 1.1 Color Tokens
```css
:root {
  /* Brand Primary */
  --color-primary: #2DCCD4;         /* sampled prominent booking CTA */
  --color-primary-hover: #20BDC8;
  --color-primary-soft: #E8FAFB;
  --color-primary-stroke: #55D8DC;
  --color-primary-text: #158E9A;

  /* Neutrals & Surfaces */
  --color-bg: #FFFFFF;
  --color-surface: #FFFFFF;
  --color-surface-muted: #F8FAFB;
  --color-text: #202425;
  --color-text-secondary: #737C7F;
  --color-text-tertiary: #8E989D;
  --color-border: #EDF0F2;
  --color-divider: #F2F4F4;

  /* Semantics */
  --color-map-route: #2DCCD4;
  --color-map-destination: #F6C600;
  --color-positive: #16A34A;
  --color-cash: #7C3AED;
}
```

### 1.2 Liquid Glass V3 Material Matrix

| Material Token | White Opacity | Blur | Saturation | Primary Role |
|---|---|---|---|---|
| `glass-dock` | 0.64 | 26px | 175% | Home floating dock capsule |
| `glass-dock-active`| 0.44 (cyan) | 12px | — | Floating dock active tab pill |
| `glass-button` | 0.76 | 16px | 160% | Interactive circular/rounded actions |
| `glass-pill` | 0.78 | 18px | 160% | Map location chips & contextual chips |
| `glass-card` | 0.82 | 16px | 150% | General soft translucent cards |
| `glass-card-car` | 0.82–0.88 | 18px | 150% | "Đặt ô tô" primary action card |
| `glass-card-food`| 0.82–0.88 | 18px | 150% | "Đặt món ăn" primary action card |
| `glass-card-service` | 0.82 | 14px | 140% | 4×2 service shortcut cards |
| `glass-input` | 0.92 | 14px | — | Elevated search bars |
| `glass-route-badge` | 0.85 (cyan) | 14px | 160% | Route summary badge (21 phút · 10.8 km) |
| `solid-primary` | 1.0 (opaque) | — | — | High-intent primary CTAs ("Đặt xe", "+") |

### 1.3 Surface Classification: Glass vs. Solid

#### Surfaces Using Liquid Glass Materials:
1. **Home Screen**:
   - Top search input trigger (`glass-input`)
   - "Đặt ô tô" core card (`glass-card-car`)
   - "Đặt món ăn" core card (`glass-card-food`)
   - 8 Additional service cards (`glass-card-service`)
   - Floating navigation dock (`glass-dock`) & active indicator (`glass-dock-active`)
2. **Destination Search**:
   - Back arrow button (`glass-button`)
   - Search query input container (`glass-input`)
3. **Ride Booking**:
   - Floating back button on map (`glass-button`)
   - "Đặt hộ" button on map (`glass-pill`)
   - Pickup location chip on map (`glass-pill`)
   - Direction swap button (`glass-button`)
   - Destination chip on map (`glass-pill`)
   - Add stop "+" button on map (`glass-button`)
   - Route summary indicator (`glass-route-badge`)
4. **Modals & Overlays**:
   - Dismiss / close buttons (`glass-button`)

#### Surfaces Intentionally Kept Solid Opaque:
1. **Destination Search Results**:
   - Location list items, addresses, nested entrances, and favorites are rendered on opaque white surfaces to guarantee maximum legibility and prevent distracting optical interference.
2. **Booking Bottom Sheet Body**:
   - The main white bottom container remains solid (`bg-white`) to maintain clean text contrast for pricing and details.
3. **Vehicle Option Rows**:
   - Clean white rows with delicate hairline borders and turquoise accent state.
4. **Primary CTAs**:
   - The primary "Đặt xe" button uses solid `#2DCCD4` (`solid-primary`) with white text for decisive affordance and high visual hierarchy.
   - The add-stop "+" square button in Destination Search uses solid `#2DCCD4` (`solid-primary`).
5. **Marketing & Imagery Rails**:
   - Promotional carousel banner and restaurant cards use photographic / illustrated artwork.

---

## 2. Screen Specifications

### 2.1 Screen A — Home (`REF-01`)
- **Top Search**: `glass-input` container, search icon, `"Bạn muốn đi đâu?"`.
- **Core Cards**: Equal-width cards (*Đặt ô tô* with `glass-card-car` cyan specular gradient & electric car illustration; *Đặt món ăn* with `glass-card-food` warm cream gradient & food illustration).
- **Services (4 × 2)**: 8 service shortcuts with `glass-card-service` (*Xe máy*, *Đi sân bay*, *Gói hội viên*, *Thẻ quà tặng*, *VinBus*, *Giao hàng*, *Hẹn giờ*, *Đi Liên tỉnh*).
- **Promo Carousel**: Full-width marketing banner (*Bạn trao hàng hóa - Xanh gửi niềm tin*, *Giảm ngay 40K*, VinFast electric delivery van, driver, 4 pagination dots with active cyan capsule).
- **Recommendations**: Horizontal rail with authentic food cards (*Lim Dimsum*, *Al Fresco's*, *Cơm Ngon SIE*, *Phở Thìn*).
- **Floating Dock**: `glass-dock` capsule with soft glowing cyan `glass-dock-active` Home indicator, positioned fixed above the frame bottom.

### 2.2 Screen B — Destination Search (`REF-02`)
- **Header**: `glass-button` back arrow, dark circular pickup donut icon (`◎`), truncated address (`Điểm Đón Xanh Taxi - Tòa Nhà Văn Phò…`), Vietnam flag + `Hà Nội` vertical stack.
- **Query Row**: Yellow destination marker, `glass-input` query container, standalone cyan `solid-primary` `+` multi-stop button.
- **Section Heading**: `"Thành phố Hà Nội"` in muted gray `#737C7F`.
- **Results List**:
   - Left column: Building/mall icon + distance (`8,2km`, `13,5...`, `7,5km`, `10km`) stacked vertically.
   - Parent name with query tokens highlighted in brand cyan (`#2DCCD4`), remaining in dark charcoal.
   - Nested entrances with matching icons, favorite heart toggle, three-dot menu.
   - Recommendation star: `★ 63% khách chọn điểm này` in green without background pills.
   - Expand/collapse: `"Xem thêm ⌵"` / `"Thu gọn ︿"` per group.

### 2.3 Screen C — Ride Booking (`REF-03` & `REF-04`)
- **Map Background**: Pastel Hà Nội city map with Sông Hồng (Red River), Cầu Vĩnh Tuy, QL5, green parks, turquoise route line, yellow destination pin, pickup pin with fanned electric cars.
- **Map Overlays**: Floating `glass-button` back button, `glass-pill` `"Đặt hộ"` button, `glass-pill` pickup chip with `"77% khách chọn điểm này"`, `glass-route-badge` route summary (`21 phút · 10.8 km`), `glass-pill` destination chip (`"Vincom Center Bà Tr... >"`), and `glass-button` `+` stop button.
- **Bottom Sheet**:
   - **Vehicle Selection**:
     - *Xanh Car* (Selected): thin 1px turquoise border, white/faint cyan background, green price indicator, 101.000đ.
     - *Xanh Premium*: 129.000đ, 4 seats, 2 phút, VF 8 with sparkles.
     - *Green Mini*: 105.000đ, 3 seats, 2 phút, VF 3 compact.
   - **Inline Payment & Promo**: Purple cash icon with `"Tiền mặt"` and voucher outline with `"Ưu đãi"` on clean white surface.
   - **Invoice Row**: 4-dots grid icon with `"Xuất hóa đơn & dịch vụ bổ sung tại đây."`.
   - **Action Bar**:
     - Left: Cyan clock icon + `"Hẹn giờ"`.
     - Middle: Turquoise lightning icon + `"XanhNow"`.
     - Right: Primary CTA button **`"Đặt xe"`** in `solid-primary` turquoise (~60% width, ~48px height, white semibold text, no yellow outline).
