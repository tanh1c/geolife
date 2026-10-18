/**
 * Xanh SM 3D AI-Generated Asset Registry
 * Provides typed semantic asset discovery with automatic Vite glob loading
 * and deterministic fallback resolution: PNG > WebP > SVG > hand-crafted SVG fallback
 */

export type ServiceAssetId =
  | 'car'
  | 'bike'
  | 'food'
  | 'airport'
  | 'subscription'
  | 'gift-card'
  | 'giftcard'
  | 'vinbus'
  | 'express'
  | 'schedule'
  | 'intercity'
  | 'tour'
  | 'car-rental'
  | 'car-rent'
  | 'buyvinfast'
  | 'buy-vinfast';

export type BookingAssetId =
  | 'xanh-car'
  | 'xanh-premium'
  | 'green-mini';

export type MediaAssetId =
  | 'banner-express'
  | 'banner-xanhsm-6trieu'
  | 'banner-phuclong'
  | 'banner-highlands'
  | 'banner-kfc'
  | 'banner-lotteria'
  | 'restaurant-lim-dimsum'
  | 'restaurant-al-frescos'
  | 'restaurant-com-ngon-sie'
  | 'restaurant-pho-thin';

export type AssetId = ServiceAssetId | BookingAssetId | MediaAssetId | (string & {});

export interface AssetMeta {
  id: string;
  name: string;
  category: 'services' | 'booking' | 'banners' | 'restaurants';
  recommendedFileName: string;
  expectedDimensions: string;
  format: 'webp' | 'png';
  hasAlpha: boolean;
  description: string;
}

/**
 * Complete metadata catalog of all registered semantic assets
 */
export const ASSET_CATALOG: Record<string, AssetMeta> = {
  // Services
  car: {
    id: 'car',
    name: 'Đặt ô tô (VF e34 / VF 5)',
    category: 'services',
    recommendedFileName: 'car.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D isometric cyan electric car matching Xanh Car branding with soft rim lighting.',
  },
  bike: {
    id: 'bike',
    name: 'Xe máy điện (Xanh SM Bike)',
    category: 'services',
    recommendedFileName: 'bike.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D turquoise electric scooter with dual mirrors and dark cyan accents.',
  },
  food: {
    id: 'food',
    name: 'Đặt món ăn (Xanh Food)',
    category: 'services',
    recommendedFileName: 'food.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D golden kraft food delivery bag with warm drink cup and bread baguette.',
  },
  intercity: {
    id: 'intercity',
    name: 'Đi Liên tỉnh',
    category: 'services',
    recommendedFileName: 'intercity.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D scenic highway waypoint map with route pins.',
  },
  express: {
    id: 'express',
    name: 'Giao hàng siêu tốc',
    category: 'services',
    recommendedFileName: 'express.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D shipping parcel held in hands with glowing delivery stars.',
  },
  subscription: {
    id: 'subscription',
    name: 'Gói hội viên',
    category: 'services',
    recommendedFileName: 'subscription.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D glowing cyan diamond privilege club insignia.',
  },
  giftcard: {
    id: 'giftcard',
    name: 'Thẻ quà tặng',
    category: 'services',
    recommendedFileName: 'giftcard.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D pastel gift box with voucher discount tags.',
  },
  'gift-card': {
    id: 'gift-card',
    name: 'Thẻ quà tặng',
    category: 'services',
    recommendedFileName: 'gift-card.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D pastel gift box with voucher discount tags.',
  },
  vinbus: {
    id: 'vinbus',
    name: 'VinBus xe buýt điện',
    category: 'services',
    recommendedFileName: 'vinbus.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D modern VinBus electric city bus in signature green/black livery.',
  },
  buyvinfast: {
    id: 'buyvinfast',
    name: 'Mua xe VinFast',
    category: 'services',
    recommendedFileName: 'buyvinfast.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D showroom trưng bày các dòng xe ô tô điện VinFast chính hãng.',
  },
  'buy-vinfast': {
    id: 'buy-vinfast',
    name: 'Mua xe VinFast',
    category: 'services',
    recommendedFileName: 'buy-vinfast.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D showroom trưng bày các dòng xe ô tô điện VinFast chính hãng.',
  },
  'car-rent': {
    id: 'car-rent',
    name: 'Thuê xe tự lái',
    category: 'services',
    recommendedFileName: 'car-rent.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D chìa khóa thông minh VinFast cho dịch vụ thuê xe tự lái.',
  },
  'car-rental': {
    id: 'car-rental',
    name: 'Thuê xe tự lái',
    category: 'services',
    recommendedFileName: 'car-rental.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D chìa khóa thông minh VinFast cho dịch vụ thuê xe tự lái.',
  },
  schedule: {
    id: 'schedule',
    name: 'Hẹn giờ đón',
    category: 'services',
    recommendedFileName: 'schedule.png',
    expectedDimensions: '512×512 px',
    format: 'png',
    hasAlpha: true,
    description: '3D modern minimalist desk clock calendar in frosted turquoise glass.',
  },
  airport: {
    id: 'airport',
    name: 'Đi sân bay',
    category: 'services',
    recommendedFileName: 'airport.webp',
    expectedDimensions: '512×512 px',
    format: 'webp',
    hasAlpha: true,
    description: '3D airliner ascending over cloud with turquoise travel suitcase.',
  },
  tour: {
    id: 'tour',
    name: 'Thuê xe du lịch',
    category: 'services',
    recommendedFileName: 'tour.webp',
    expectedDimensions: '512×512 px',
    format: 'webp',
    hasAlpha: true,
    description: '3D sightseeing luggage suitcase with sunglasses and camera.',
  },

  // Booking Vehicles (3D High-Fidelity Car Renders)
  'xanh-car': {
    id: 'xanh-car',
    name: 'Xanh Car (VinFast VF e34 3D)',
    category: 'booking',
    recommendedFileName: 'xanh-car.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: '3D studio rendering of VinFast VF e34 electric car in signature cyan blue.',
  },
  'suv-34-3d-1024': {
    id: 'suv-34-3d-1024',
    name: 'Xanh Car (VF e34 3D)',
    category: 'booking',
    recommendedFileName: 'suv-34-3d-1024.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: '3D studio rendering of VinFast VF e34 electric car in signature cyan blue.',
  },
  'xanh-premium': {
    id: 'xanh-premium',
    name: 'Xanh Premium (VinFast Luxury VF 8 3D)',
    category: 'booking',
    recommendedFileName: 'xanh-premium.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: '3D studio rendering of luxury electric SUV with VIP gold sparkle stars.',
  },
  'suv-sparkle-3d-1024': {
    id: 'suv-sparkle-3d-1024',
    name: 'Xanh Premium (Luxury 3D Sparkle)',
    category: 'booking',
    recommendedFileName: 'suv-sparkle-3d-1024.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: '3D studio rendering of luxury electric SUV with VIP gold sparkle stars.',
  },
  'green-mini': {
    id: 'green-mini',
    name: 'Green Mini (VinFast VF 3 Compact 3D)',
    category: 'booking',
    recommendedFileName: 'green-mini.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: '3D studio rendering of boxy compact electric car VinFast VF 3.',
  },
  'suv-mini-3d-1024': {
    id: 'suv-mini-3d-1024',
    name: 'Green Mini (VF 3 Compact 3D)',
    category: 'booking',
    recommendedFileName: 'suv-mini-3d-1024.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: '3D studio rendering of boxy compact electric car VinFast VF 3.',
  },

  // Banners & Promos
  'banner-xanhsm-6trieu': {
    id: 'banner-xanhsm-6trieu',
    name: 'Mừng khách hàng thứ 6 triệu',
    category: 'banners',
    recommendedFileName: 'banner-xanhsm-6trieu.png',
    expectedDimensions: '1920×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Banner chính thức kỷ niệm chào đón khách hàng thứ 6 triệu của Xanh SM.',
  },
  'banner-phuclong': {
    id: 'banner-phuclong',
    name: 'Phúc Long Giảm 30%',
    category: 'banners',
    recommendedFileName: 'banner-phuclong.png',
    expectedDimensions: '1920×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Banner khuyến mại Phúc Long giảm 30% thức uống tươi mát.',
  },
  'banner-highlands': {
    id: 'banner-highlands',
    name: 'Highlands Coffee Mua 1 Tặng 1',
    category: 'banners',
    recommendedFileName: 'banner-highlands.png',
    expectedDimensions: '1920×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Banner khuyến mại Highlands Coffee mua 1 tặng 1 cà phê đậm đà.',
  },
  'banner-kfc': {
    id: 'banner-kfc',
    name: 'KFC Combo 99K',
    category: 'banners',
    recommendedFileName: 'banner-kfc.png',
    expectedDimensions: '1920×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Banner khuyến mại KFC combo 99K xô gà rán giòn cay thơm ngon.',
  },
  'banner-lotteria': {
    id: 'banner-lotteria',
    name: 'Lotteria Giảm 50%',
    category: 'banners',
    recommendedFileName: 'banner-lotteria.png',
    expectedDimensions: '1920×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Banner khuyến mại Lotteria giảm giá 50% burger và khoai tây chiên.',
  },
  'greensm-login-bg': {
    id: 'greensm-login-bg',
    name: 'Xanh SM Login Background (Dọc 9:16)',
    category: 'banners',
    recommendedFileName: 'greensm-login-bg-1080x1920.png',
    expectedDimensions: '1080×1920 px',
    format: 'png',
    hasAlpha: false,
    description: 'Hình nền đăng nhập Xanh SM với bầu trời xanh, vệt cánh chim VinFast và xe ô tô điện trên đường phố.',
  },
  'greensm-profile-bg': {
    id: 'greensm-profile-bg',
    name: 'Xanh SM Profile Banner (Ngang 16:9)',
    category: 'banners',
    recommendedFileName: 'greensm-profile-bg-1920x1080.png',
    expectedDimensions: '1920×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Banner ngang trang hồ sơ người dùng Xanh SM với skyline thành phố và xe ô tô điện.',
  },
  'default-avatar': {
    id: 'default-avatar',
    name: 'Ảnh đại diện người dùng mặc định',
    category: 'banners',
    recommendedFileName: 'default-avatar-circle-1080x1080.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: true,
    description: 'Avatar hình tròn màu xanh cyan gradient với bóng người màu trắng đặc trưng Green SM.',
  },

  // GeoLife Place 3D Icons
  'place-cafe': {
    id: 'place-cafe',
    name: 'Địa điểm: Quán Cà Phê (3D)',
    category: 'services',
    recommendedFileName: 'place-cafe.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: 'Tách cà phê 3D màu cam ấm áp bốc khói nghi ngút cho địa điểm Cafe.',
  },
  'place-gym': {
    id: 'place-gym',
    name: 'Địa điểm: Phòng tập Gym (3D)',
    category: 'services',
    recommendedFileName: 'place-gym.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: 'Tạ tay thể hình 3D màu xanh dương cho địa điểm Phòng Gym.',
  },
  'place-library': {
    id: 'place-library',
    name: 'Địa điểm: Thư viện (3D)',
    category: 'services',
    recommendedFileName: 'place-library.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: 'Quyển sách mở 3D bìa xanh ngọc cho địa điểm Thư viện và học tập.',
  },
  'place-mall': {
    id: 'place-mall',
    name: 'Địa điểm: TTTM & Mua sắm (3D)',
    category: 'services',
    recommendedFileName: 'place-mall.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: 'Tòa nhà trung tâm thương mại 3D với mái hiên sọc màu sắc cho địa điểm Mall.',
  },
  'place-market': {
    id: 'place-market',
    name: 'Địa điểm: Khu chợ & Siêu thị (3D)',
    category: 'services',
    recommendedFileName: 'place-market.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: 'Túi xách đi chợ 3D màu cam đỏ cho địa điểm Chợ thực phẩm và mua sắm.',
  },
  'place-park': {
    id: 'place-park',
    name: 'Địa điểm: Công viên cây xanh (3D)',
    category: 'services',
    recommendedFileName: 'place-park.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: 'Cụm cây xanh 3D tươi mát trên thảm cỏ cho địa điểm Công viên.',
  },
  'place-station': {
    id: 'place-station',
    name: 'Địa điểm: Ga tàu & Bến xe (3D)',
    category: 'services',
    recommendedFileName: 'place-station.png',
    expectedDimensions: '1024×1024 px',
    format: 'png',
    hasAlpha: true,
    description: 'Ghim định vị 3D màu cyan với quả cầu trong suốt cho địa điểm Nhà ga và trạm trung chuyển.',
  },

  // Restaurants & Menu Posters
  'menu-banhmi': {
    id: 'menu-banhmi',
    name: 'Bánh Mì Thơm Ngon',
    category: 'restaurants',
    recommendedFileName: 'menu-banhmi.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Thực đơn Bánh mì thịt nướng, pate, trứng ốp la tươi ngon chuẩn vị.',
  },
  'menu-banhmi-1080x1080': {
    id: 'menu-banhmi-1080x1080',
    name: 'Bánh Mì Thơm Ngon (1080x1080)',
    category: 'restaurants',
    recommendedFileName: 'menu-banhmi-1080x1080.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Thực đơn Bánh mì thịt nướng, pate, trứng ốp la tươi ngon chuẩn vị.',
  },
  'menu-comtam': {
    id: 'menu-comtam',
    name: 'Cơm Tấm Sài Gòn',
    category: 'restaurants',
    recommendedFileName: 'menu-comtam.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Thực đơn Cơm tấm sườn nướng, bì chả, trứng ốp la đậm đà truyền thống.',
  },
  'menu-comtam-1080x1080': {
    id: 'menu-comtam-1080x1080',
    name: 'Cơm Tấm Sài Gòn (1080x1080)',
    category: 'restaurants',
    recommendedFileName: 'menu-comtam-1080x1080.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Thực đơn Cơm tấm sườn nướng, bì chả, trứng ốp la đậm đà truyền thống.',
  },
  'menu-pho': {
    id: 'menu-pho',
    name: 'Phở Ngon Truyền Thống',
    category: 'restaurants',
    recommendedFileName: 'menu-pho.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Thực đơn Phở bò tái, phở gà, phở bò viên nước dùng hầm 12h nóng hổi.',
  },
  'menu-pho-1080x1080': {
    id: 'menu-pho-1080x1080',
    name: 'Phở Ngon Truyền Thống (1080x1080)',
    category: 'restaurants',
    recommendedFileName: 'menu-pho-1080x1080.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Thực đơn Phở bò tái, phở gà, phở bò viên nước dùng hầm 12h nóng hổi.',
  },
  'menu-trasua': {
    id: 'menu-trasua',
    name: 'Trà Sữa Ngon',
    category: 'restaurants',
    recommendedFileName: 'menu-trasua.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Thực đơn Trà sữa truyền thống, khoai môn, trà đào, matcha mát lạnh.',
  },
  'menu-trasua-1080x1080': {
    id: 'menu-trasua-1080x1080',
    name: 'Trà Sữa Ngon (1080x1080)',
    category: 'restaurants',
    recommendedFileName: 'menu-trasua-1080x1080.png',
    expectedDimensions: '1080×1080 px',
    format: 'png',
    hasAlpha: false,
    description: 'Thực đơn Trà sữa truyền thống, khoai môn, trà đào, matcha mát lạnh.',
  },
  'restaurant-lim-dimsum': {
    id: 'restaurant-lim-dimsum',
    name: 'Nhà hàng Lim Dimsum',
    category: 'restaurants',
    recommendedFileName: 'restaurant-lim-dimsum.webp',
    expectedDimensions: '512×512 px',
    format: 'webp',
    hasAlpha: false,
    description: 'Bamboo steamer dimsum basket on rich crimson background with gold chopsticks.',
  },
  'restaurant-al-frescos': {
    id: 'restaurant-al-frescos',
    name: "Nhà hàng Al Fresco's",
    category: 'restaurants',
    recommendedFileName: 'restaurant-al-frescos.webp',
    expectedDimensions: '512×512 px',
    format: 'webp',
    hasAlpha: false,
    description: 'Woodfired Italian pizza and barbecue ribs on warm festive orange backdrop.',
  },
  'restaurant-com-ngon-sie': {
    id: 'restaurant-com-ngon-sie',
    name: 'Cơm Ngon SIE',
    category: 'restaurants',
    recommendedFileName: 'restaurant-com-ngon-sie.webp',
    expectedDimensions: '512×512 px',
    format: 'webp',
    hasAlpha: false,
    description: 'Steaming fragrant rice bowl with healthy vegetables and sesame garnish.',
  },
  'restaurant-pho-thin': {
    id: 'restaurant-pho-thin',
    name: 'Phở Thìn Lò Đúc',
    category: 'restaurants',
    recommendedFileName: 'restaurant-pho-thin.webp',
    expectedDimensions: '512×512 px',
    format: 'webp',
    hasAlpha: false,
    description: 'Traditional Hanoi stir-fried beef pho bowl with scallions and rich broth.',
  },
};

/**
 * Vite automatic asset discovery for files placed in src/assets/
 * Supports PNG, WebP, and SVG
 */
const discoveredAssets = import.meta.glob<string>(
  '/src/assets/**/*.{png,webp,svg}',
  {
    eager: true,
    import: 'default',
  }
);

/**
 * Deterministically resolve an asset ID to its file URL.
 * Preference: PNG > WebP > SVG
 * Returns null if no file has been placed in the folder yet.
 */
export function getAssetUrl(id: string): string | null {
  const meta = ASSET_CATALOG[id];

  const extensions = ['png', 'webp', 'svg'] as const;
  const categories = meta
    ? [meta.category, 'services', 'banners', 'booking', 'restaurants']
    : ['services', 'banners', 'booking', 'restaurants'];

  // 1. Direct path search by category and extensions
  for (const ext of extensions) {
    const rootPath = `/src/assets/${id}.${ext}`;
    if (discoveredAssets[rootPath]) {
      return discoveredAssets[rootPath];
    }
    if (meta?.recommendedFileName) {
      const recPath = `/src/assets/${meta.recommendedFileName}`;
      if (discoveredAssets[recPath]) {
        return discoveredAssets[recPath];
      }
    }
    for (const cat of categories) {
      const path = `/src/assets/${cat}/${id}.${ext}`;
      if (discoveredAssets[path]) {
        return discoveredAssets[path];
      }
    }
  }

  // 2. Name-match search inside discoveredAssets keys
  for (const ext of extensions) {
    for (const key of Object.keys(discoveredAssets)) {
      if (key.endsWith(`/${id}.${ext}`) || key.includes(`/${id}-`) || (meta?.recommendedFileName && key.endsWith(`/${meta.recommendedFileName}`))) {
        return discoveredAssets[key];
      }
    }
  }

  return null;
}

/**
 * Returns true if an image file is physically present in the repository
 */
export function hasAsset(id: string): boolean {
  return getAssetUrl(id) !== null;
}

/**
 * Returns all registered assets with their metadata and current discovery status
 */
export function getAllRegisteredAssets(): (AssetMeta & { isAvailable: boolean; url: string | null })[] {
  return Object.values(ASSET_CATALOG).map((meta) => {
    const url = getAssetUrl(meta.id);
    return {
      ...meta,
      isAvailable: url !== null,
      url,
    };
  });
}
