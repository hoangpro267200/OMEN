declare module 'react-simple-maps' {
  import type { ReactNode } from 'react';
  export interface ComposableMapProps {
    projection?: string;
    projectionConfig?: { scale?: number; center?: [number, number] };
    style?: React.CSSProperties;
    children?: ReactNode;
  }
  export interface GeographiesProps {
    geography: string | object;
    children: (props: { geographies: object[] }) => ReactNode;
  }
  export interface GeographyProps {
    geography: object;
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
    style?: object;
  }
  export interface LineProps {
    coordinates: [number, number][];
    stroke?: string;
    strokeWidth?: number;
    strokeLinecap?: string;
    strokeDasharray?: string;
  }
  export interface MarkerProps {
    coordinates: [number, number];
    children: ReactNode;
  }
  export interface ZoomableGroupProps {
    center?: [number, number];
    zoom?: number;
    children?: ReactNode;
  }
  export function ComposableMap(props: ComposableMapProps): JSX.Element;
  export function Geographies(props: GeographiesProps): JSX.Element;
  export function Geography(props: GeographyProps): JSX.Element;
  export function Line(props: LineProps): JSX.Element;
  export function Marker(props: MarkerProps): JSX.Element;
  export function ZoomableGroup(props: ZoomableGroupProps): JSX.Element;
}
