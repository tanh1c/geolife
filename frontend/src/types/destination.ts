export interface EntrancePoint {
  id: string;
  name: string;
  isPopular?: boolean;
  popularText?: string;
  isFavorite?: boolean;
}

export interface PlaceResult {
  id: string;
  name: string;
  type: 'mall' | 'station' | 'location';
  distance: string;
  address: string;
  entrances: EntrancePoint[];
}

export interface PlaceSelection {
  name: string;
  address: string;
  distance: string;
  entrance?: string;
}
