import type { ReactNode } from 'react';
import { ConsoleLayout } from '../components/ConsoleLayout';
export function CustomerLayout({ children }: {children?: ReactNode}) {
  return <ConsoleLayout>{children}</ConsoleLayout>;
}
