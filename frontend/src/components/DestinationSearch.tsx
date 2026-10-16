import React, { useState, useMemo } from 'react';
import {
  ArrowLeft,
  Plus,
  Heart,
  ChevronDown,
  X,
  MoreVertical,
  MapPin,
  ChevronRight,
} from 'lucide-react';
import { HANOI_PLACES } from '../data/hanoiPlaces';
import { PlaceSelection } from '../types/destination';
import { placeName, getPlaceIcon, type Result } from '../GeoLife';

export type { PlaceSelection };

interface DestinationSearchProps {
  onBack: () => void;
  onSelectPlace: (place: PlaceSelection) => void;
  suggestions?: Result | null;
  demoHour?: string;
  query?: string;
  onQueryChange?: (query: string) => void;
  favorites?: string[];
  onToggleFavorite?: (id: string) => void;
  extraStops?: string[];
  onExtraStopsChange?: (stops: string[]) => void;
  expandedGroups?: Record<string, boolean>;
  onToggleExpand?: (id: string) => void;
}

// Remove Vietnamese diacritics for accent-insensitive search matching
function removeVietnameseTones(str: string): string {
  return str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D');
}

// Custom Building / Shopping Mall Icon matching image_2.png
const MallIcon: React.FC<{ className?: string }> = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    {/* Storefront roof awning */}
    <path
      d="M3 9L4.5 4H19.5L21 9M3 9V19C3 19.5523 3.44772 20 4 20H20C20.5523 20 21 19.5523 21 19V9M3 9C3 10.1046 3.89543 11 5 11C6.10457 11 7 10.1046 7 9C7 10.1046 7.89543 11 9 11C10.1046 11 11 10.1046 11 9C11 10.1046 11.8954 11 13 11C14.1046 11 15 10.1046 15 9C15 10.1046 15.8954 11 17 11C18.1046 11 19 10.1046 19 9C19 10.1046 19.8954 11 21 11"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    {/* Entrance Doorway */}
    <path
      d="M9 20V14H15V20"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// Location Pin Icon matching Ocean Park in image_2.png
const PinMarkerIcon: React.FC<{ className?: string }> = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path
      d="M12 21C16 17 20 13.4183 20 9.5C20 5.35786 16.4183 2 12 2C7.58172 2 4 5.35786 4 9.5C4 13.4183 8 17 12 21Z"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle cx="12" cy="9.5" r="2.8" stroke="currentColor" strokeWidth="1.7" />
  </svg>
);

// Pickup Donut / Target Icon matching top header
const PickupTargetIcon: React.FC<{ className?: string }> = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <circle cx="12" cy="12" r="8" stroke="#1E2528" strokeWidth="3" />
    <circle cx="12" cy="12" r="3" fill="#1E2528" />
  </svg>
);

// Vietnam Flag Icon
const VietnamFlag: React.FC<{ className?: string }> = ({ className = "w-5 h-3.5" }) => (
  <svg viewBox="0 0 30 20" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect width="30" height="20" rx="1.5" fill="#DA251D" />
    {/* Yellow 5-pointed star */}
    <polygon
      points="15,4 16.5,8.8 21.5,8.8 17.5,11.8 19,16.5 15,13.5 11,16.5 12.5,11.8 8.5,8.8 13.5,8.8"
      fill="#FFFF00"
    />
  </svg>
);

export const DestinationSearch: React.FC<DestinationSearchProps> = ({
  onBack,
  onSelectPlace,
  suggestions,
  demoHour,
  query: controlledQuery,
  onQueryChange,
  favorites: controlledFavorites,
  onToggleFavorite,
  extraStops: controlledExtraStops,
  onExtraStopsChange,
  expandedGroups: controlledExpandedGroups,
  onToggleExpand,
}) => {
  // Support both controlled state from parent and internal fallback state
  const [internalQuery, setInternalQuery] = useState('');
  const [internalExtraStops, setInternalExtraStops] = useState<string[]>([]);
  const [internalFavorites, setInternalFavorites] = useState<string[]>([]);
  const [internalExpandedGroups, setInternalExpandedGroups] = useState<Record<string, boolean>>({
    'vincom-ba-trieu': false,
    'vincom-tran-duy-hung': false,
    'vincom-ocean-park': false,
    'vincom-pham-ngoc-thach': false,
  });

  const query = controlledQuery !== undefined ? controlledQuery : internalQuery;
  const setQuery = onQueryChange || setInternalQuery;

  const extraStops = controlledExtraStops !== undefined ? controlledExtraStops : internalExtraStops;
  const setExtraStops = onExtraStopsChange || setInternalExtraStops;

  const favorites = controlledFavorites !== undefined ? controlledFavorites : internalFavorites;
  const expandedGroups = controlledExpandedGroups !== undefined ? controlledExpandedGroups : internalExpandedGroups;

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onToggleFavorite) {
      onToggleFavorite(id);
    } else {
      setInternalFavorites((prev) =>
        prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
      );
    }
  };

  const toggleExpand = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onToggleExpand) {
      onToggleExpand(id);
    } else {
      setInternalExpandedGroups((prev) => ({ ...prev, [id]: !prev[id] }));
    }
  };

  const addStopField = () => {
    if (extraStops.length < 2) {
      setExtraStops([...extraStops, '']);
    }
  };

  const removeStopField = (index: number) => {
    setExtraStops(extraStops.filter((_, i) => i !== index));
  };

  // Filter places based on search query (case-insensitive & accent-insensitive)
  const filteredPlaces = useMemo(() => {
    const cleanQuery = removeVietnameseTones(query.trim().toLowerCase());
    if (!cleanQuery) return HANOI_PLACES;

    return HANOI_PLACES.filter((place) => {
      const matchName = removeVietnameseTones(place.name.toLowerCase()).includes(cleanQuery);
      const matchAddress = removeVietnameseTones(place.address.toLowerCase()).includes(cleanQuery);
      const matchEntrances = place.entrances.some((e) =>
        removeVietnameseTones(e.name.toLowerCase()).includes(cleanQuery)
      );
      return matchName || matchAddress || matchEntrances;
    });
  }, [query]);

  // Helper to render text with matched query tokens highlighted in turquoise (#2DCCD4)
  // Uses non-global regex test to ensure deterministic highlighting without lastIndex state bugs
  const renderHighlightedText = (text: string, currentQuery: string) => {
    const trimmed = currentQuery.trim();
    if (!trimmed) {
      return <span>{text}</span>;
    }

    try {
      // Escape special characters to prevent regex crashes
      const escaped = trimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const splitRegex = new RegExp(`(${escaped})`, 'gi');
      const parts = text.split(splitRegex);
      const matchRegex = new RegExp(`^${escaped}$`, 'i');

      return (
        <>
          {parts.map((part, i) =>
            matchRegex.test(part) ? (
              <span key={i} className="text-[#2DCCD4] font-semibold">
                {part}
              </span>
            ) : (
              <span key={i}>{part}</span>
            )
          )}
        </>
      );
    } catch {
      return <span>{text}</span>;
    }
  };

  return (
    <div className="flex-1 bg-white flex flex-col h-full min-h-0 overflow-hidden select-none">
      
      {/* 1. TOP HEADER (Sticky, White, Matches image_2.png) */}
      <div className="px-3.5 pt-10 pb-2.5 bg-white border-b border-gray-100 flex items-center justify-between gap-2 shrink-0">
        {/* Back Button (Subtle Liquid Glass button) */}
        <button
          onClick={onBack}
          aria-label="Quay lại"
          className="w-9 h-9 rounded-full glass-button flex items-center justify-center -ml-0.5 text-[#202425] shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
        >
          <ArrowLeft className="w-5 h-5" strokeWidth={2.2} />
        </button>

        {/* Pickup Location Info */}
        <div className="flex-1 flex items-center gap-2 overflow-hidden px-0.5">
          {/* Circular Donut Pickup Icon */}
          <PickupTargetIcon className="w-4 h-4 shrink-0" />
          <span className="text-[14px] font-semibold text-[#202425] truncate">
            Điểm Đón Xanh Taxi - Tòa Nhà Văn Phò…
          </span>
        </div>

        {/* Vietnam Flag + Hà Nội (Stacked vertically, matching screenshot) */}
        <div className="flex flex-col items-center justify-center shrink-0 pl-1 pr-1">
          <VietnamFlag className="w-[18px] h-[13px] shadow-2xs rounded-[1px]" />
          <span className="text-[10.5px] font-medium text-[#737C7F] leading-tight text-center mt-0.5">
            Hà Nội
          </span>
        </div>
      </div>

      {/* 2. DESTINATION SEARCH INPUT ROW (Matches image_2.png) */}
      <div className="px-4 pt-3 pb-2.5 flex items-center gap-2 shrink-0 bg-white">
        {/* Main Search Input Container (Elevated Liquid Glass Input) */}
        <div className="flex-1 h-[48px] glass-input rounded-[16px] px-3.5 flex items-center gap-2.5">
          {/* Rounded Yellow Destination Pin Marker with inner white square */}
          <div className="w-[18px] h-[18px] rounded-[5px] bg-[#F6C600] flex items-center justify-center shrink-0 shadow-2xs">
            <div className="w-[6px] h-[6px] bg-white rounded-[1px]" />
          </div>

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm kiếm điểm đến"
            className="flex-1 bg-transparent text-[15px] font-medium text-[#202425] focus:outline-none placeholder:text-[#9CA3AF]"
            autoFocus
          />

          {query && (
            <button
              onClick={() => setQuery('')}
              aria-label="Xóa nội dung tìm kiếm"
              className="w-5 h-5 rounded-full bg-gray-200/90 flex items-center justify-center text-gray-500 hover:bg-gray-300 active:scale-90 transition shrink-0 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" strokeWidth={2.2} />
            </button>
          )}
        </div>

        {/* Turquoise Square "+" Button (Solid Primary CTA, matches image_2.png) */}
        <button
          onClick={addStopField}
          aria-label="Thêm điểm dừng"
          className="w-[46px] h-[48px] rounded-[16px] solid-primary text-white flex items-center justify-center shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4]"
        >
          <Plus className="w-5 h-5" strokeWidth={2.6} />
        </button>
      </div>

      {/* Optional Extra Stops Inputs (Multi-Stop Support) */}
      {extraStops.length > 0 && (
        <div className="px-4 pb-2 space-y-2 shrink-0 bg-white">
          {extraStops.map((stopVal, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <div className="flex-1 h-[44px] bg-gray-50 rounded-[14px] px-3.5 flex items-center gap-2.5 border border-gray-200">
                <div className="w-3.5 h-3.5 rounded-full bg-[#3B82F6] flex items-center justify-center text-white text-[9px] font-bold">
                  {idx + 1}
                </div>
                <input
                  type="text"
                  placeholder={`Điểm dừng ${idx + 1}...`}
                  value={stopVal}
                  onChange={(e) => {
                    const newStops = [...extraStops];
                    newStops[idx] = e.target.value;
                    setExtraStops(newStops);
                  }}
                  className="flex-1 bg-transparent text-[14px] font-medium text-[#202425] focus:outline-none"
                />
              </div>
              <button
                onClick={() => removeStopField(idx)}
                className="w-9 h-9 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400 hover:text-red-500 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 4. RESULTS LIST (Vertically Scrollable, Exactly matches image_2.png) */}
      <div className="flex-1 overflow-y-auto px-4 pb-16 no-scrollbar">
        {/* Smart AI Suggestions Card */}
        {suggestions?.status === 'suggested' && suggestions.suggestions.length > 0 && !query && (
          <div className="pt-2 pb-2">
            <div className="rounded-[22px] bg-gradient-to-br from-[#F0FDFE] via-[#F8FDFF] to-white p-3.5 border border-[#2DCCD4]/35 shadow-[0_4px_16px_rgba(45,204,212,0.08)]">
              {/* Header */}
              <div className="flex items-center justify-between pb-2.5 border-b border-[#2DCCD4]/15">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-bold text-[#0E4850] tracking-tight">
                    Gợi ý cho bạn
                  </span>
                  <span className="text-[11px] font-bold text-[#127F8B] bg-[#E0F8FA] px-2 py-0.5 rounded-full border border-[#2DCCD4]/30">
                    {demoHour ? `Lúc ${demoHour}` : 'Hiện tại'}
                  </span>
                </div>
                <span className="text-[10.5px] font-semibold text-[#158E9A] bg-[#2DCCD4]/10 px-2 py-0.5 rounded-full">
                  AI GeoLife
                </span>
              </div>

              {/* Suggestions items */}
              <div className="divide-y divide-gray-100/80">
                {suggestions.suggestions.map((item) => (
                  <div
                    key={item.place_ref}
                    onClick={() =>
                      onSelectPlace({
                        name: placeName(item.place_ref),
                        address: item.explanations.join(' • '),
                        distance: `Top ${item.rank}`,
                      })
                    }
                    className="py-2.5 flex items-center justify-between gap-3 cursor-pointer hover:bg-white/80 active:scale-[0.98] rounded-xl px-1.5 transition-all group"
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className="w-10 h-10 shrink-0 flex items-center justify-center group-hover:scale-105 transition-transform">
                        {getPlaceIcon(item.place_ref, "w-10 h-10 object-contain drop-shadow-2xs")}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="text-[14.5px] font-bold text-[#202425] truncate leading-snug group-hover:text-[#127F8B] transition-colors">
                            {placeName(item.place_ref)}
                          </h4>
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-[#E0F8FA] text-[#127F8B] shrink-0 border border-[#2DCCD4]/30">
                            Top {item.rank}
                          </span>
                        </div>
                        <p className="text-[11.5px] text-[#737C7F] truncate mt-0.5 leading-snug">
                          {item.explanations.join(' • ')}
                        </p>
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center gap-1 text-[12px] font-bold text-[#127F8B] bg-[#E0F8FA] group-hover:bg-[#D4F4F7] px-2.5 py-1 rounded-xl border border-[#2DCCD4]/40 transition">
                      <span>Chọn</span>
                      <ChevronRight className="w-3.5 h-3.5 text-[#127F8B]" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 3. SECTION LABEL: "Thành phố Hà Nội" */}
        <div className="pt-2 pb-1.5">
          <span className="text-[13px] font-medium text-[#737C7F]">
            Thành phố Hà Nội
          </span>
        </div>
        {filteredPlaces.length === 0 ? (
          <div className="py-20 text-center flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 mb-3">
              <MapPin className="w-6 h-6" />
            </div>
            <p className="text-[#202425] font-semibold text-[15px]">Không tìm thấy địa điểm</p>
            <p className="text-[#8E989D] text-[13px] mt-1 max-w-[240px]">
              Vui lòng thử tìm kiếm với từ khóa khác hoặc kiểm tra lại chính tả.
            </p>
            <button
              onClick={() => setQuery('Vincom')}
              className="mt-4 px-4 py-2 rounded-xl bg-[#2DCCD4] text-white text-[13px] font-bold hover:bg-[#20BDC8] active:scale-95 transition"
            >
              Tìm lại "Vincom"
            </button>
          </div>
        ) : (
          filteredPlaces.map((place) => {
            const isExpanded = expandedGroups[place.id];
            const visibleEntrances = isExpanded
              ? place.entrances
              : place.entrances.slice(0, 2);

            return (
              <div key={place.id} className="pt-3 pb-3">
                {/* Parent Location Row */}
                <div
                  onClick={() =>
                    onSelectPlace({
                      name: place.name,
                      address: place.address,
                      distance: place.distance,
                    })
                  }
                  className="flex items-start gap-3 cursor-pointer group"
                >
                  {/* Left Column: Icon + Distance stacked vertically */}
                  <div className="w-10 shrink-0 flex flex-col items-center pt-0.5">
                    {place.type === 'location' ? (
                      <PinMarkerIcon className="w-5 h-5 text-[#737C7F] group-hover:text-[#2DCCD4] transition-colors" />
                    ) : (
                      <MallIcon className="w-5 h-5 text-[#737C7F] group-hover:text-[#2DCCD4] transition-colors" />
                    )}
                    <span className="text-[11px] font-medium text-[#737C7F] mt-0.5 text-center leading-tight truncate max-w-full">
                      {place.distance}
                    </span>
                  </div>

                  {/* Right Content: Location Title with highlight + Address */}
                  <div className="flex-1 pr-1 overflow-hidden">
                    <h3 className="text-[15px] font-semibold text-[#202425] leading-snug">
                      {renderHighlightedText(place.name, query)}
                    </h3>
                    <p className="text-[12px] text-[#8E989D] mt-0.5 leading-snug">
                      {place.address}
                    </p>
                  </div>
                </div>

                {/* Nested Pickup Locations / Entrances */}
                <div className="pl-13 pr-1 mt-2.5 space-y-2">
                  {visibleEntrances.map((entrance) => {
                    const isFav = favorites.includes(entrance.id);

                    return (
                      <div key={entrance.id} className="flex flex-col">
                        <div
                          onClick={() =>
                            onSelectPlace({
                              name: place.name,
                              address: place.address,
                              distance: place.distance,
                              entrance: entrance.name,
                            })
                          }
                          className="flex items-center justify-between py-1 cursor-pointer active:bg-gray-50 rounded-lg transition-colors group/ent"
                        >
                          {/* Left: Nested Icon + Name */}
                          <div className="flex items-center gap-2.5 flex-1 pr-2 overflow-hidden">
                            {place.type === 'location' ? (
                              <PinMarkerIcon className="w-4 h-4 text-[#8E989D] group-hover/ent:text-[#2DCCD4] shrink-0" />
                            ) : (
                              <MallIcon className="w-4 h-4 text-[#8E989D] group-hover/ent:text-[#2DCCD4] shrink-0" />
                            )}
                            <span className="text-[13.5px] font-medium text-[#202425] leading-snug truncate">
                              {renderHighlightedText(entrance.name, query)}
                            </span>
                          </div>

                          {/* Right: Heart Icon + Three Dot Menu */}
                          <div className="flex items-center gap-2.5 shrink-0 text-[#8E989D]">
                            <button
                              onClick={(e) => toggleFavorite(entrance.id, e)}
                              aria-label="Thêm vào yêu thích"
                              className="p-1 hover:text-red-500 active:scale-85 transition"
                            >
                              <Heart
                                className={`w-4 h-4 ${
                                  isFav
                                    ? 'text-[#EF4444] fill-[#EF4444]'
                                    : 'text-[#8E989D]'
                                }`}
                                strokeWidth={1.7}
                              />
                            </button>

                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                              }}
                              aria-label="Tùy chọn khác"
                              className="p-1 hover:text-gray-900 active:scale-85 transition"
                            >
                              <MoreVertical className="w-4 h-4 text-[#8E989D]" strokeWidth={1.8} />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  {/* "Xem thêm" Expand / Collapse control */}
                  {place.entrances.length > 2 && (
                    <button
                      onClick={(e) => toggleExpand(place.id, e)}
                      className="flex items-center gap-1 pt-1 text-[12px] font-semibold text-[#202425] hover:text-[#2DCCD4] active:scale-95 transition cursor-pointer"
                    >
                      <span>{isExpanded ? 'Thu gọn' : 'Xem thêm'}</span>
                      <ChevronDown
                        className={`w-3.5 h-3.5 text-[#202425] transition-transform duration-200 ${
                          isExpanded ? 'rotate-180' : ''
                        }`}
                      />
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

    </div>
  );
};
