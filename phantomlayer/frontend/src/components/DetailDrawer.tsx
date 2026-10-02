import { type ReactNode, useEffect, useRef } from 'react';
import { containDialogFocus } from '../lib/dialogFocus';

export function DetailDrawer({children,onClose,label}: {children:ReactNode;onClose:()=>void;label:string}) {
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{
    const element=dialog.current;
    const focused=document.activeElement as HTMLElement|null;
    const overflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    element?.showModal();
    return()=>{if(element?.open)element.close();document.body.style.overflow=overflow;if(focused?.isConnected)focused.focus({preventScroll:true});};
  },[]);
  return <dialog ref={dialog} className="detail-dialog" aria-label={label} onKeyDown={containDialogFocus} onCancel={event=>{event.preventDefault();onClose();}} onClick={event=>{if(event.target===event.currentTarget)onClose();}}>{children}</dialog>;
}
