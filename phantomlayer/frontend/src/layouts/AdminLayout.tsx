import type { ReactNode } from 'react';
import { ConsoleLayout } from '../components/ConsoleLayout';
export function AdminLayout({ children }: {children?: ReactNode}) {
  return <ConsoleLayout admin>{children}</ConsoleLayout>;
}
