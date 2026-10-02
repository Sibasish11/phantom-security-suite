import type { SVGProps } from 'react';

const paths = {
  shield: 'M12 3 3.5 6.5v5c0 5 3.5 8 8.5 10 5-2 8.5-5 8.5-10v-5L12 3Z M8 12l3 3 5-6',
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  activity: 'M2 12h5l3-8 4 16 3-8h5',
  alert: 'M12 3 2 20h20L12 3Z M12 9v4 M12 16v.5',
  globe: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M3 12h18 M12 3c5 5 5 13 0 18-5-5-5-13 0-18',
  server: 'M4 3h16v7H4z M4 14h16v7H4z M7 6.5h.1 M7 17.5h.1 M11 6.5h6 M11 17.5h6',
  settings: 'm10 3-1 3-3 1-3-1-1 4 3 2v3l-2 2 3 3 3-2 3 1 1 3 4-1v-3l2-2h3l1-4-3-1-1-3 1-3-4-1-2 2Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  arrow: 'M4 12h16 M14 6l6 6-6 6',
  check: 'm5 12 4 4L19 6',
  lock: 'M5 10h14v11H5z M8 10V7a4 4 0 0 1 8 0v3 M12 14v3',
  eye: 'M2 12c5-9 15-9 20 0-5 9-15 9-20 0Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  eyeOff: 'm3 3 18 18 M10 5c5-1 9 2 12 7l-3 4 M6 6c-2 1-3 3-4 6 4 7 10 9 16 6 M10 10a3 3 0 0 0 4 4',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  close: 'm6 6 12 12 M6 18 18 6',
  logOut: 'M9 4H4v16h5 M10 12h11 M17 8l4 4-4 4',
  layers: 'm12 3 10 5-10 5L2 8l10-5Z M2 12l10 5 10-5 M2 16l10 5 10-5',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 7v5l3 2',
  search: 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0 m-2 5 6 6',
  refresh: 'M20 8a9 9 0 0 0-15-3L2 8 M2 3v5h5 M4 16a9 9 0 0 0 15 3l3-3 M22 21v-5h-5',
  terminal: 'm5 7 4 5-4 5 M12 17h7',
  building: 'M5 21V3h14v18 M2 21h20 M9 7h1 M14 7h1 M9 11h1 M14 11h1 M10 21v-6h4v6',
} as const;
export type IconName = keyof typeof paths;
export function Icon({ name, ...props }: SVGProps<SVGSVGElement> & { name: IconName }) {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[name]} /></svg>;
}
