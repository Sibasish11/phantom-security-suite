interface LoadingScreenProps { message?: string }
export function LoadingScreen({message = 'Loading your workspace…'}: LoadingScreenProps) {
  return <div className="loading-screen" role="status" aria-live="polite" aria-busy="true"><div className="loading-content"><span className="eyebrow">PHANTOMLAYER WORKSPACE</span><p>{message}</p><div className="loading-skeleton" aria-hidden="true"><i/><i/><i/></div></div></div>;
}
