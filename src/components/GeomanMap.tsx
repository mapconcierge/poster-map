'use client';

import { useEffect, useRef } from 'react';

interface GeomanMapProps {
  onMapReady?: (map: any) => void;
  className?: string;
}

export default function GeomanMap({ onMapReady, className }: GeomanMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  useEffect(() => {
    if (!mapRef.current) return;
    
    // Prevent double initialization
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const initializeMap = async () => {
      const L = (await import('leaflet')).default;
      
      // Import Geoman before creating the map
      await import('@geoman-io/leaflet-geoman-free');
      
      // Fix Leaflet default markers in Next.js
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet/dist/images/marker-shadow.png',
      });

      // Create map
      const map = L.map(mapRef.current!).setView([35.6762, 139.6503], 10);
      mapInstanceRef.current = map;

      console.log('Map created, pm available:', !!map.pm);

      if (onMapReady) {
        onMapReady(map);
      }

      // Fix map sizing issues by forcing a resize after initial render
      setTimeout(() => {
        map.invalidateSize();
      }, 100);
    };

    initializeMap();

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  return (
    <div 
      ref={mapRef} 
      id="map" 
      className={className}
      style={{
        width: '100%',
        height: '100vh',
        margin: 0,
        padding: 0
      }}
    />
  );
}