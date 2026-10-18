import { PlaceResult } from '../types/destination';

export const HANOI_PLACES: PlaceResult[] = [
  {
    id: 'vincom-ba-trieu',
    name: 'Vincom Center Bà Triệu',
    type: 'mall',
    distance: '8,2km',
    address: '191 Phố Bà Triệu, Phường Hai Bà Trưng, Thành Phố Hà Nội, Việt Nam',
    entrances: [
      { id: 'bt-1', name: 'Cổng Thái Phiên - Vincom Bà Triệu' },
      { id: 'bt-2', name: 'Cổng Bà Triệu - Vincom Center Bà Triệu' },
      { id: 'bt-3', name: 'Cổng Đoàn Trần Nghiệp - Vincom Bà Triệu' },
      { id: 'bt-4', name: 'Sảnh Tháp A - Phố Bà Triệu' },
    ],
  },
  {
    id: 'vincom-tran-duy-hung',
    name: 'Vincom Center Trần Duy Hưng',
    type: 'mall',
    distance: '13,5...',
    address: '119 Đường Trần Duy Hưng, Phường Thanh Xuân, Thành Phố Hà Nội, Việt Nam',
    entrances: [
      { id: 'tdh-1', name: 'Toà C7 - Vincom Center Trần Duy Hưng' },
      {
        id: 'tdh-2',
        name: 'Sảnh chính - Vincom Center Trần Duy Hưng',
        isPopular: true,
        popularText: '63% khách chọn điểm này',
      },
      { id: 'tdh-3', name: 'Cổng hầm gửi xe B1 - Đường Hoàng Minh Giám' },
      { id: 'tdh-4', name: 'Cổng đón trả khách đường Trần Duy Hưng' },
    ],
  },
  {
    id: 'vincom-ocean-park',
    name: 'Vincom Mega Mall Ocean Park',
    type: 'location',
    distance: '7,5km',
    address: 'Sao Biển, Xã Gia Lâm, Thành phố Hà Nội, Việt Nam',
    entrances: [
      { id: 'op-1', name: 'VinFast - Vincom Mega Mall Ocean Park' },
      { id: 'op-2', name: 'Cổng Sao Biển 22 - Vincom Mega Mall Ocean Park' },
      { id: 'op-3', name: 'Sảnh Hải Âu - Mega Mall Ocean Park' },
    ],
  },
  {
    id: 'vincom-pham-ngoc-thach',
    name: 'Vincom Center Phạm Ngọc Thạch',
    type: 'mall',
    distance: '10km',
    address: '2 Đường Phạm Ngọc Thạch, Phường Kim Liên, Thành Phố Hà Nội, Việt Nam',
    entrances: [
      { id: 'pnt-1', name: 'Cổng Phạm Ngọc Thạch - Vincom Center' },
      { id: 'pnt-2', name: 'Cổng phố Chùa Bộc - Vincom Center' },
      { id: 'pnt-3', name: 'Sảnh tầng 1 TTTM Phạm Ngọc Thạch' },
    ],
  },
  {
    id: 'vincom-royal-city',
    name: 'Vincom Mega Mall Royal City',
    type: 'mall',
    distance: '9,8km',
    address: '72A Đường Nguyễn Trãi, Phường Thượng Đình, Quận Thanh Xuân, Hà Nội',
    entrances: [
      { id: 'rc-1', name: 'Quảng trường Hoàng Gia - Vincom Mega Mall Royal City' },
      { id: 'rc-2', name: 'Sảnh R1 - Khu Căn Hộ Royal City' },
      { id: 'rc-3', name: 'Cổng hầm B2 - Khu Đỗ Xe Xanh SM' },
    ],
  },
  {
    id: 'vincom-smart-city',
    name: 'Vincom Mega Mall Smart City',
    type: 'location',
    distance: '16,2km',
    address: 'Khu đô thị Vinhomes Smart City, Tây Mỗ, Nam Từ Liêm, Hà Nội',
    entrances: [
      { id: 'sc-1', name: 'Sảnh chính thác nước ánh sáng - Vincom Smart City' },
      { id: 'sc-2', name: 'Trạm sạc VinFast Vincom Smart City' },
    ],
  },
];
