import { Children, cloneElement, isValidElement, useLayoutEffect, useRef, type ReactElement, type ReactNode, type TableHTMLAttributes, type KeyboardEventHandler } from 'react';

// Keep native table semantics. On narrow screens CSS exposes the column names
// beside each cell, and existing selectable rows also work from the keyboard.
function keyboardRows(children: ReactNode): ReactNode {
  return Children.map(children, child => {
    if (!isValidElement(child)) return child;
    const element = child as ReactElement<{children?:ReactNode; onClick?:unknown; onKeyDown?:KeyboardEventHandler<HTMLTableRowElement>; tabIndex?:number}>;
    const props = element.props;
    const extra = element.type === 'tr' && props.onClick ? {
      tabIndex: props.tabIndex ?? 0,
      onKeyDown: ((event) => {
        props.onKeyDown?.(event);
        if (event.target === event.currentTarget && (event.key === 'Enter' || event.key === ' ')) {
          event.preventDefault(); event.currentTarget.click();
        }
      }) as KeyboardEventHandler<HTMLTableRowElement>,
    } : {};
    return cloneElement(element, extra, props.children ? keyboardRows(props.children) : props.children);
  });
}
export function ResponsiveTable({children,className='',...props}:TableHTMLAttributes<HTMLTableElement>) {
  const table=useRef<HTMLTableElement>(null);
  useLayoutEffect(()=>{
    const headings=Array.from(table.current?.querySelectorAll('thead th') || []).map(cell=>cell.textContent?.trim() || '');
    table.current?.querySelectorAll('tbody tr').forEach(row=>Array.from(row.children).forEach((cell,index)=>{
      if (cell.tagName==='TD' && cell.getAttribute('colspan')!=='99') cell.setAttribute('data-label',headings[index] || '');
    }));
  },[children]);
  return <table ref={table} className={`responsive-table ${className}`} {...props}>{keyboardRows(children)}</table>;
}
