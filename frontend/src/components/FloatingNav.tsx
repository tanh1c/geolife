import React from 'react';
import { Clock, Bell, User, Home } from 'lucide-react';
import { TOKENS } from '../styles/tokens';

export type TabType = 'home' | 'history' | 'notifications' | 'profile';

interface FloatingNavProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export const FloatingNav: React.FC<FloatingNavProps> = ({ activeTab, onTabChange }) => {
  return (
    <nav
      aria-label="Thanh điều hướng chính"
      className="absolute bottom-5 sm:bottom-6 pb-[env(safe-area-inset-bottom)] left-1/2 -translate-x-1/2 z-40 select-none pointer-events-auto"
    >
      {/* Translucent Frosted Glass Dock with Liquid Glass V3 Material */}
      <div className={`w-[290px] h-[60px] rounded-full ${TOKENS.materials.dock} px-3 flex items-center justify-between`}>
        
        {/* Tab 1: Home (Active indicator with soft translucent frosted cyan glass) */}
        <button
          onClick={() => onTabChange('home')}
          aria-label="Trang chủ"
          className="relative group transition-transform duration-150 active:scale-95 flex items-center justify-center cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4] rounded-full"
        >
          {activeTab === 'home' ? (
            <div className={`w-11 h-11 rounded-full ${TOKENS.materials.dockActive} flex items-center justify-center transition-all duration-200`}>
              <Home className="w-[21px] h-[21px] text-white fill-white drop-shadow-xs" strokeWidth={1.5} />
            </div>
          ) : (
            <div className="w-10 h-10 flex items-center justify-center text-[#737C7F] hover:text-[#2DCCD4] transition-colors">
              <Home className="w-5 h-5" strokeWidth={1.8} />
            </div>
          )}
        </button>

        {/* Tab 2: History / Trips */}
        <button
          onClick={() => onTabChange('history')}
          aria-label="Lịch sử hoạt động"
          className="relative group transition-transform duration-150 active:scale-95 flex items-center justify-center cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4] rounded-full"
        >
          {activeTab === 'history' ? (
            <div className={`w-11 h-11 rounded-full ${TOKENS.materials.dockActive} flex items-center justify-center transition-all duration-200`}>
              <Clock className="w-[21px] h-[21px] text-white drop-shadow-xs" strokeWidth={2.2} />
            </div>
          ) : (
            <div className="w-10 h-10 flex items-center justify-center text-[#737C7F] hover:text-[#2DCCD4] transition-colors">
              <Clock className="w-5 h-5" strokeWidth={2} />
            </div>
          )}
        </button>

        {/* Tab 3: Notifications */}
        <button
          onClick={() => onTabChange('notifications')}
          aria-label="Thông báo"
          className="relative group transition-transform duration-150 active:scale-95 flex items-center justify-center cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4] rounded-full"
        >
          {activeTab === 'notifications' ? (
            <div className={`w-11 h-11 rounded-full ${TOKENS.materials.dockActive} flex items-center justify-center transition-all duration-200`}>
              <Bell className="w-[21px] h-[21px] text-white fill-white drop-shadow-xs" strokeWidth={1.5} />
            </div>
          ) : (
            <div className="w-10 h-10 flex items-center justify-center text-[#737C7F] hover:text-[#2DCCD4] transition-colors relative">
              <Bell className="w-5 h-5" strokeWidth={2} />
              {/* Subtle unread dot */}
              <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-[#EF4444] rounded-full ring-2 ring-white/90" />
            </div>
          )}
        </button>

        {/* Tab 4: Profile */}
        <button
          onClick={() => onTabChange('profile')}
          aria-label="Tài khoản cá nhân"
          className="relative group transition-transform duration-150 active:scale-95 flex items-center justify-center cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2DCCD4] rounded-full"
        >
          {activeTab === 'profile' ? (
            <div className={`w-11 h-11 rounded-full ${TOKENS.materials.dockActive} flex items-center justify-center transition-all duration-200`}>
              <User className="w-[21px] h-[21px] text-white fill-white drop-shadow-xs" strokeWidth={1.5} />
            </div>
          ) : (
            <div className="w-10 h-10 flex items-center justify-center text-[#737C7F] hover:text-[#2DCCD4] transition-colors">
              <User className="w-5 h-5" strokeWidth={2} />
            </div>
          )}
        </button>

      </div>
    </nav>
  );
};
